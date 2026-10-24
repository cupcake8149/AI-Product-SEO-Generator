import os
from io import BytesIO

import streamlit as st
from dotenv import load_dotenv
from PIL import Image, ImageOps
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
attached images. Use web search to research current, externally verifiable information
where appropriate.

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
- Use web search for current competitor information and customer review research.
- If a fact, review, price, or source cannot be verified, say so clearly rather than guessing.
- Do not imply that a review is real unless it can be tied to an accessible source page.
- Review snippets, if used, must be brief and faithful to the source; do not fabricate or combine
  different reviews. Prefer paraphrases with direct links over invented quotation marks.
- Clearly label estimated prices and include currency and market.
- If the input names a specific product, focus the SEO package on that product. If the input is
  a broad category (for example, "wireless earphones"), also compare 2–4 relevant alternatives.
- Do not treat a broad category as if it were one specific product.

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
            with st.spinner(
                "Researching the product, checking available web sources, and generating your SEO package..."
            ):
                response = client.models.generate_content(
                    model=model_name,
                    contents=contents,
                    config=types.GenerateContentConfig(
                        temperature=0.4,
                        tools=[types.Tool(google_search=types.GoogleSearch())],
                    ),
                )

            response_text = response.text or ""
            if not response_text.strip():
                st.error(
                    "Gemini returned no text. Please retry, or check the app logs and model availability."
                )
                st.stop()

            st.caption(f"Generated using `{model_name}` · Images analyzed: {image_count}")
            st.markdown(response_text)

            # Show source links supplied by Gemini's Google Search grounding metadata.
            source_items = []
            seen_urls = set()
            try:
                for candidate in response.candidates or []:
                    grounding_metadata = getattr(candidate, "grounding_metadata", None)
                    for chunk in getattr(grounding_metadata, "grounding_chunks", None) or []:
                        web_source = getattr(chunk, "web", None)
                        uri = getattr(web_source, "uri", None) if web_source else None
                        title = getattr(web_source, "title", None) if web_source else None
                        if uri and uri not in seen_urls:
                            seen_urls.add(uri)
                            source_items.append((title or uri, uri))
            except Exception:
                # Grounding metadata may be absent for some responses.
                source_items = []

            if source_items:
                with st.expander(f"Web sources returned by Gemini ({len(source_items)})", expanded=True):
                    for title, uri in source_items:
                        st.markdown(f"- [{title}]({uri})")
            else:
                st.info(
                    "No web-source links were returned in grounding metadata for this response. "
                    "Do not treat any purported customer reviews as verified until their original pages are checked."
                )

            st.download_button(
                label="Download SEO & Research Package (.md)",
                data=response_text,
                file_name="product_seo_research_package.md",
                mime="text/markdown",
                use_container_width=True,
            )

        except APIError as exc:
            error_code = getattr(exc, "code", "unknown")
            error_detail = str(getattr(exc, "message", "") or "").strip()

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
                st.caption(f"Gemini's error detail: {error_detail[:500]}")
            st.caption("For technical details, open Manage app → Logs in Streamlit Cloud.")
        except Exception as exc:
            st.error("The request could not be completed. Check the app logs for details.")
            st.caption(f"Error type: {type(exc).__name__}. Sensitive details are hidden.")

st.divider()
st.caption(
    "AI-generated content can be inaccurate. Verify product claims, prices, review wording, "
    "ratings, and source pages before publishing or presenting results."
)
