import os
import re
from urllib.parse import urlparse

import streamlit as st
from dotenv import load_dotenv
from PIL import Image, ImageOps
import requests
from google import genai
from google.genai import types
from google.genai.errors import APIError

load_dotenv()

st.set_page_config(
    page_title="AI Product Description & SEO Generator",
    page_icon="🛍️",
    layout="wide",
)

st.title("🛍️ AI Product Description & SEO Generator")
st.write(
    "Create product copy, SEO assets, buying advice, competitor comparisons, "
    "and web-grounded customer-review research."
)

# Read credentials from local .env or Streamlit Community Cloud secrets.
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    try:
        api_key = st.secrets.get("GEMINI_API_KEY")
    except Exception:
        api_key = None

if not api_key:
    st.error(
        "Missing Gemini API key. Add GEMINI_API_KEY to your local .env file "
        "or to Streamlit Cloud → Manage app → Settings → Secrets."
    )
    st.stop()

model_name = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
client = genai.Client(api_key=api_key)

tavily_api_key = os.getenv("TAVILY_API_KEY")
if not tavily_api_key:
    try:
        tavily_api_key = st.secrets.get("TAVILY_API_KEY")
    except Exception:
        tavily_api_key = None

def tavily_search(query: str, key: str, max_results: int = 5) -> list[dict]:
    """Run a Tavily search and preserve only fields needed for evidence review."""
    response = requests.post(
        "https://api.tavily.com/search",
        json={
            "api_key": key,
            "query": query,
            "search_depth": "basic",
            "topic": "general",
            "max_results": max_results,
            "include_answer": False,
            "include_raw_content": True,
        },
        timeout=25,
    )
    response.raise_for_status()
    payload = response.json()
    return [
        {
            "title": item.get("title", "Untitled source"),
            "url": item.get("url", ""),
            "content": item.get("content", ""),
            "raw_content": (item.get("raw_content") or "")[:3500],
        }
        for item in payload.get("results", [])
        if item.get("url")
    ]


STOPWORDS = {
    "the", "and", "for", "with", "from", "this", "that", "your", "product",
    "official", "current", "price", "prices", "market", "country", "model",
    "specification", "specifications", "features", "best", "top", "buy", "shop",
    "review", "reviews", "rating", "ratings", "customer", "customers", "user",
    "users", "similar", "alternative", "alternatives", "available", "women", "woman",
    "men", "man", "new", "online", "in", "on", "at", "of", "to", "a", "an",
    "is", "are", "by", "it", "as", "or", "be", "all", "from", "about",
}


def tokens(value: str) -> set[str]:
    """Normalize words for conservative, explainable relevance scoring."""
    return {
        word for word in re.findall(r"[a-z0-9]+", (value or "").lower())
        if len(word) > 2 and word not in STOPWORDS
    }


def source_relevance(item: dict, subject: str, task: str) -> tuple[int, str]:
    """Score whether a search result is actually useful for this research task."""
    title = item.get("title", "")
    snippet = item.get("content", "")
    raw = item.get("raw_content", "")
    url = item.get("url", "")
    title_tokens = tokens(title)
    body_tokens = tokens(f"{snippet} {raw[:1800]}")
    subject_tokens = tokens(subject)
    host = urlparse(url).netloc.lower().removeprefix("www.")

    # Generic lead-generation/company directories are not reliable product evidence.
    directory_hosts = ("rocketreach.co", "tracxn.com", "cbinsights.com")
    if any(host == domain or host.endswith("." + domain) for domain in directory_hosts):
        return -100, "generic company directory; not product-level evidence"

    # Words from the subject are more useful than generic words like "product" or "price".
    title_overlap = subject_tokens & title_tokens
    body_overlap = subject_tokens & body_tokens
    score = (len(title_overlap) * 3) + min(len(body_overlap), 5)

    # Penalize obviously unrelated results and generic company/directories pages.
    bad_signals = {
        "spa", "hair design", "dial tone resource", "recall", "auction", "million wristwatch",
        "portfolio investments", "company profile", "competitors companies like",
    }
    title_lower = title.lower()
    if any(signal in title_lower for signal in bad_signals):
        score -= 6
    # Product-category terms help assess alternatives without requiring the same brand.
    category_terms = {
        "watch": {"watch", "watches", "analog", "analogue", "wristwatch", "timepiece"},
        "cleanser": {"cleanser", "cleansing", "facewash", "face", "bodywash", "skincare"},
        "earphone": {"earphone", "earphones", "earbud", "earbuds", "headphone", "headphones"},
        "phone": {"phone", "smartphone", "mobile", "handset"},
        "laptop": {"laptop", "notebook", "computer"},
        "shoe": {"shoe", "shoes", "sneaker", "sneakers", "footwear"},
        "bag": {"bag", "handbag", "backpack", "purse"},
        "perfume": {"perfume", "fragrance", "eau", "cologne"},
    }
    subject_lower = subject.lower()
    category = next((terms for key, terms in category_terms.items() if key in subject_lower or any(t in subject_tokens for t in terms)), set())
    category_hits = (title_tokens | body_tokens) & category
    score += min(len(category_hits), 3) * 2

    if task == "reviews":
        review_signals = {"review", "reviews", "rating", "ratings", "verified", "customer", "customers", "stars", "testimonial"}
        if (title_tokens | body_tokens) & review_signals:
            score += 2
        else:
            score -= 2
    elif task == "alternatives":
        # Alternatives need clear category relevance, not necessarily a match to the target brand.
        if category and not category_hits:
            score -= 5

    # A direct official/retailer/product page can be useful, but authority alone is not relevance.
    if any(term in host for term in ("titan.co.in", "fossil.com", "citizenwatch.com", "timex.com", "amazon.in", "flipkart.com")):
        score += 1

    reason = f"title overlap: {len(title_overlap)}, category matches: {len(category_hits)}"
    return score, reason


def filter_relevant_sources(items: list[dict], subject: str, limit: int = 8) -> list[dict]:
    """Keep a small, ranked set of task-relevant sources; discard noisy search hits."""
    ranked = []
    for item in items:
        task = item.get("task", "product")
        score, reason = source_relevance(item, subject, task)
        item["relevance_score"] = score
        item["relevance_reason"] = reason
        # Use a slightly lower threshold for alternatives because brand names differ.
        threshold = 2 if task == "alternatives" else 3
        if score >= threshold:
            ranked.append(item)
    ranked.sort(key=lambda item: (item["relevance_score"], item.get("tavily_score", 0)), reverse=True)

    # Deduplicate by normalized URL and cap the evidence set passed to the language model.
    kept, seen = [], set()
    for item in ranked:
        normalized_url = item["url"].split("#", 1)[0].rstrip("/").lower()
        if normalized_url in seen:
            continue
        seen.add(normalized_url)
        kept.append(item)
        if len(kept) >= limit:
            break
    return kept

left, right = st.columns([1, 1], gap="large")

with left:
    st.subheader("Product Information")

    uploaded_files = st.file_uploader(
        "Upload Product Images (optional; select multiple)",
        type=["png", "jpg", "jpeg", "webp"],
        accept_multiple_files=True,
        help="Upload several views of the same product for better visual context.",
    )

    if uploaded_files:
        preview_cols = st.columns(min(3, len(uploaded_files)))
        for index, uploaded_file in enumerate(uploaded_files):
            try:
                with Image.open(uploaded_file) as source_image:
                    preview_image = ImageOps.exif_transpose(source_image).copy()
                with preview_cols[index % len(preview_cols)]:
                    st.image(
                        preview_image,
                        caption=uploaded_file.name,
                        use_container_width=True,
                    )
            except Exception:
                st.warning(f"Could not preview {uploaded_file.name}. Please use a valid image.")

    product_name = st.text_input(
        "Product Name or Category",
        placeholder="e.g., Lumière Silk Face Cleanser or wireless earphones",
        help="Enter a specific product for its SEO package, or a broad category to compare alternatives.",
    )
    features = st.text_area(
        "Product Features / Notes (optional)",
        placeholder="Ingredients, specifications, materials, benefits, price, or other known details",
        height=130,
    )
    seo_keywords = st.text_input(
        "SEO Keywords (optional)",
        placeholder="e.g., wireless earbuds, Bluetooth earphones",
    )
    market = st.text_input(
        "Target Market / Country (optional)",
        placeholder="e.g., India, United Kingdom, United States",
        help="Used to make competitor availability and estimated price comparisons more relevant.",
    )
    tone = st.selectbox(
        "Tone of Voice",
        [
            "Persuasive & Commercial",
            "Trendy & Casual",
            "Minimalist & Luxury",
            "Technical & Informative",
        ],
    )

    generate_btn = st.button(
        "Generate Product Research & SEO",
        type="primary",
        use_container_width=True,
    )

with right:
    st.subheader("Generated Assets")

    if generate_btn:
        if not product_name.strip() and not features.strip() and not uploaded_files:
            st.warning("Enter a product name/category, add product notes, or upload at least one image.")
            st.stop()

        prompt = f"""
You are an evidence-conscious e-commerce copywriter, product critic, SEO strategist,
and objective market researcher. Analyze the user's product information and any
attached images. Use the LIVE WEB SEARCH RESULTS supplied later in this prompt to research current,
externally verifiable information. Do not claim to have visited or verified a page beyond
what its supplied title, snippet, and extracted text support.

USER CONTEXT
- Product name/category: {product_name.strip() or "Infer cautiously from the supplied images and notes"}
- Features/notes supplied by the user: {features.strip() or "No written features supplied; do not invent specifications"}
- SEO keywords: {seo_keywords.strip() or "Choose relevant keywords"}
- Target market: {market.strip() or "Not specified; state the market assumption used for prices"}
- Tone: {tone}

IMPORTANT EVIDENCE RULES
- Distinguish user-provided facts, visual observations, estimates, and externally verified claims.
- Never invent ingredients, certifications, specifications, prices, ratings, review quotations,
  customer identities, review dates, or source URLs.
- Product images alone do not prove ingredients, performance, safety, certifications, or exact model.
- Use only the live search results supplied in this prompt for external research.
- Cite only URLs included in those results. Never invent a URL or claim a source supports something it does not.
- If a fact, review, price, or source cannot be verified, say so clearly rather than guessing.
- Do not imply that a review is real unless it can be tied to an accessible source page.
- Review snippets, if used, must be brief and faithful to the source; do not fabricate or combine
  different reviews. Prefer paraphrases with direct links over invented quotation marks.
- Clearly label estimated prices and include currency and market.
- If the input names a specific product, focus the SEO package on that product. If the input is
  a broad category (for example, "wireless earphones"), also compare 2–4 relevant alternatives.
- Do not treat a broad category as if it were one specific product.
- Never infer a gender target, exact model, material, or product variant from appearance alone.
- Treat each supplied search result as a candidate, not automatically relevant. Ignore sources that
  merely mention the category or brand without supporting the specific claim being made.
- For each competitor row, use an exact model and a source that identifies that model. If the results
  only support broad brand-level comparisons, label them as brand-level examples and do not invent prices.
- The source list should contain only sources actually cited or materially used in the report; do not
  repeat every search result just because it was returned.

Write the output in clear Markdown with these sections:

### 1. SEO-Optimized Product Title
Keep the title under 60 characters where practical.

### 2. Short Product Description
Write 1–2 persuasive sentences without unsupported claims.

### 3. Key Feature Bullets
Provide 4–5 bullets. Mark uncertain features as unverified or omit them.

### 4. SEO Keywords
List 5 primary and 5 long-tail keywords. Use supplied keywords naturally where relevant.

### 5. Meta Description
Aim for 150–160 characters with a call to action, without keyword stuffing.

### 6. Recommended Image Alt Text
Describe only visible details. Do not infer invisible specifications.

### 7. Customer Reviews & Testimonials — 3–5 sourced reviews
Research 3–5 real customer reviews for the exact product where possible. For each one include:
- A short faithful quote (only if the exact wording is visible and verifiable) or a clearly labelled paraphrase
- Rating, reviewer/date only if visible on the source
- Source platform and a direct URL to the actual review/product-review page
- A brief note if the source is for a different region or a closely related model

Do not create sample reviews and present them as real. If fewer than 3 genuine, traceable reviews can be found, report how many were verified and explain what could not be found. Official product pages and general search results are not themselves customer reviews unless they display actual customer feedback. Clearly distinguish sponsored/brand-provided testimonials from independent customer reviews.

### 8. AI Buying Verdict & Advice
Give a balanced verdict based on available evidence: whether it appears worth considering, who may benefit, who should avoid it, key drawbacks, and what to check before buying. Do not state certainty beyond the evidence.

### 9. Competitor Comparison (2–4 alternatives when appropriate)
If the user entered a broad product category, use web research to compare 2–4 relevant, currently available market alternatives. Use a Markdown table with:
- Product/model
- Estimated price range (currency, market, and source/date where available)
- Key pros
- Key cons
- Value-for-money verdict
- Source link(s)

For a specific named product, include alternatives only when useful and clearly identify them as alternatives. Do not invent exact prices. If current prices cannot be verified, label them unavailable instead of guessing.

### 10. Research Sources
List the most relevant URLs actually used. Prioritize direct product-review pages and reliable retailer/manufacturer pages. Explain briefly which claims each source supports.

Remember: a search result snippet alone may not establish that a claim is true. If web research does not return adequate evidence, be transparent about the limitation.
"""

        contents = [prompt]
        image_count = 0
        for uploaded_file in uploaded_files or []:
            try:
                uploaded_file.seek(0)
                with Image.open(uploaded_file) as source_image:
                    pil_image = ImageOps.exif_transpose(source_image).copy()
                if pil_image.mode not in ("RGB", "L"):
                    pil_image = pil_image.convert("RGB")
                elif pil_image.mode == "L":
                    pil_image = pil_image.convert("RGB")
                contents.append(pil_image)
                image_count += 1
            except Exception:
                st.warning(f"Skipped unreadable image: {uploaded_file.name}")

        if uploaded_files and image_count == 0 and not product_name.strip() and not features.strip():
            st.warning("No readable images were found. Upload a valid image or enter product details.")
            st.stop()

        try:
            with st.spinner("Searching the live web with Tavily, then generating your SEO and research package..."):
                if not tavily_api_key:
                    st.error(
                        "Tavily API key is missing. Add TAVILY_API_KEY to Streamlit Cloud → "
                        "Manage app → Settings → Secrets, then reboot the app."
                    )
                    st.stop()

                market_text = market.strip() or "India"
                # Identify the uploaded product before searching; otherwise a generic
                # placeholder leads to unrelated pages (e.g. Getty Images reviews).
                if product_name.strip():
                    research_subject = product_name.strip()
                elif features.strip():
                    research_subject = features.strip()
                elif image_count:
                    identify_prompt = (
                        "Identify the product shown in the attached image(s) for web research. "
                        "Return a concise search identity: visible brand, product type, distinctive "
                        "features, and model/SKU only if readable. Do not guess an exact model."
                    )
                    identify_response = client.models.generate_content(
                        model=model_name,
                        contents=[identify_prompt, *contents[1:]],
                        config=types.GenerateContentConfig(temperature=0.1),
                    )
                    research_subject = (identify_response.text or "").strip() or "product identified from image"
                else:
                    research_subject = "product"

                # Search in separate stages so each result can be judged against its intended task.
                lower_subject = research_subject.lower()
                if "titan" in lower_subject and ("watch" in lower_subject or "analog" in lower_subject):
                    query_plan = [
                        ("product", f'"{research_subject}" Titan official product specifications price {market_text}'),
                        ("reviews", f'"{research_subject}" Titan watch customer reviews ratings {market_text}'),
                        ("reviews", f'Titan rose gold analog watch white dial day date reviews retailer {market_text}'),
                        ("alternatives", f'rose gold analog watch white dial day date alternatives price India Fossil Timex'),
                    ]
                else:
                    query_plan = [
                        ("product", f'"{research_subject}" official product specifications price {market_text}'),
                        ("reviews", f'"{research_subject}" customer reviews ratings retailer {market_text}'),
                        ("alternatives", f'{research_subject} similar products alternatives current prices {market_text}'),
                    ]

                candidate_results = []
                seen_urls = set()
                for task, query in query_plan:
                    for item in tavily_search(query, tavily_api_key, max_results=5):
                        url = item["url"].strip()
                        normalized_url = url.split("#", 1)[0].rstrip("/").lower()
                        if not url or normalized_url in seen_urls:
                            continue
                        seen_urls.add(normalized_url)
                        item["task"] = task
                        item["query"] = query
                        candidate_results.append(item)

                search_results = filter_relevant_sources(candidate_results, research_subject, limit=8)

                if not search_results:
                    st.warning(
                        "Tavily returned results, but none passed the relevance filter. "
                        "The report will avoid making externally sourced claims rather than use unrelated pages. "
                        "Try entering the exact product name/model or adding identifying details."
                    )
                    research_context = (
                        "No search result passed the app's relevance filter for this product. "
                        "Do not invent prices, reviews, ratings, availability, specifications, competitors, or sources. "
                        "Explain that relevant evidence could not be found in this search."
                    )
                else:
                    research_context = (
                        "LIVE TAVILY RESULTS THAT PASSED A LOCAL RELEVANCE FILTER. The filter is heuristic, "
                        "not proof that a page is accurate. Re-check each title/snippet/extracted text before using it. "
                        "Ignore a result if it does not directly support the specific claim.\n"
                    )
                    for i, item in enumerate(search_results, 1):
                        research_context += (
                            f"\nSOURCE {i} (research task: {item['task']}; relevance score: {item['relevance_score']})"
                            f"\nTitle: {item['title']}\nURL: {item['url']}\n"
                            f"Search snippet: {item['content']}\n"
                            f"Extracted page text (may be incomplete): {item['raw_content'] or '[not available]'}\n"
                        )
                    research_context += (
                        "\nEVIDENCE RULES: A result passing a relevance filter is not proof that its claims are true. "
                        "Only attribute claims to a source when its supplied text supports them. Do not invent customer quotes, "
                        "names, ratings, dates, prices, or specifications. For reviews, use only feedback clearly visible "
                        "in supplied source text and link to the actual review/product-review page. Official product pages "
                        "and general search results are not customer reviews unless actual feedback is visible. If the exact "
                        "product/model or review cannot be matched, say so. If current prices are not shown, mark them unavailable. "
                        "Do not claim pages were independently verified; extracted source text may be incomplete.\n"
                    )

                grounded_contents = [contents[0], "\n\n" + research_context, *contents[1:]]
                response = client.models.generate_content(
                    model=model_name,
                    contents=grounded_contents,
                    config=types.GenerateContentConfig(temperature=0.3),
                )

            response_text = response.text or ""
            if not response_text.strip():
                st.error("Gemini returned no text. Please retry, or check the app logs and model availability.")
                st.stop()

            st.caption(f"Generated using `{model_name}` · Images analyzed: {image_count} · Live search: Tavily")
            st.markdown(response_text)

            if search_results:
                with st.expander(f"Relevant candidate sources used for research ({len(search_results)})", expanded=True):
                    for item in search_results:
                        title = item["title"].replace("[", "(").replace("]", ")")
                        task_label = item.get("task", "product").title()
                        st.markdown(f"- **{task_label}** · [{title}]({item['url']})")
                    st.caption(
                        "These sources passed a basic relevance filter, not a fact-check. "
                        "Open the pages before relying on specific prices, ratings, or product claims."
                    )
            else:
                st.info("No live source links were returned. External claims, prices, and reviews are not verified in this report.")

            st.download_button(
                label="Download SEO & Research Package (.md)",
                data=response_text,
                file_name="product_seo_research_package.md",
                mime="text/markdown",
                use_container_width=True,
            )

        except APIError as exc:
            error_code = getattr(exc, "code", "unknown")
            # Include the full SDK error text: the short message alone can omit
            # structured quota details useful for diagnosing HTTP 429 responses.
            error_detail = str(exc).strip() or str(getattr(exc, "message", "") or "").strip()

            if error_code == 404:
                st.error(
                    f"Gemini returned HTTP 404 for model `{model_name}`. "
                    "This often means the model is unavailable to this API project. "
                    "The app's default has been updated to `gemini-3.5-flash-lite`."
                )
                st.info(
                    "In Streamlit Cloud → Manage app → Settings, check whether an environment "
                    "variable named GEMINI_MODEL overrides the default. If it does, change its "
                    "value to `gemini-3.5-flash-lite` or remove the override, then reboot the app."
                )
            else:
                st.error(
                    f"Gemini API request failed (HTTP {error_code}). "
                    "Check the API key, API project access, quota, and request settings."
                )

            if error_detail:
                st.caption(f"Gemini's error detail: {error_detail[:1200]}")
            st.caption("For technical details, open Manage app → Logs in Streamlit Cloud.")
        except requests.HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else "unknown"
            detail = ""
            try:
                detail = exc.response.text[:1000] if exc.response is not None else str(exc)
            except Exception:
                detail = str(exc)
            st.error(f"Tavily live search failed (HTTP {status}). Check that TAVILY_API_KEY is correct and that your Tavily account has available credits.")
            if detail:
                st.caption(f"Tavily error detail: {detail}")
        except requests.RequestException as exc:
            st.error("Could not reach Tavily live search. Check the connection and try again.")
            st.caption(f"Network error: {type(exc).__name__}")
        except Exception as exc:
            st.error("The request could not be completed. Check the app logs for details.")
            st.caption(f"Error type: {type(exc).__name__}. Sensitive details are hidden.")

st.divider()
st.caption(
    "AI-generated content can be inaccurate. Verify product claims, prices, review wording, "
    "ratings, and source pages before publishing or presenting results."
)
