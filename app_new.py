import os
import streamlit as st
from dotenv import load_dotenv
from PIL import Image
from google import genai, types
from google.genai.errors import APIError

load_dotenv()

st.set_page_config(
    page_title="AI Product Description & SEO Generator",
    page_icon="🛍️",
    layout="wide"
)

# Fetch key from environment or Streamlit secrets
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    try:
        api_key = st.secrets.get("GEMINI_API_KEY")
    except Exception:
        pass

if not api_key:
    st.error("Missing GEMINI_API_KEY. Please verify your .env file or Streamlit secrets.")
    st.stop()

client = genai.Client(api_key=api_key)

st.title("🛍️ AI Product Description & SEO Generator")
st.write("Upload a product image or enter details to generate SEO copy.")

col1, col2 = st.columns([1, 1], gap="large")

with col1:
    st.subheader("Product Input")
    uploaded_files = st.file_uploader(
        "Upload Product Images",
        type=["png", "jpg", "jpeg", "webp"],
        accept_multiple_files=True,
        help="Upload one or more product images."
    )

    pil_images = []
    if uploaded_files:
        for uploaded_file in uploaded_files:
            try:
                pil_image = Image.open(uploaded_file)
                if pil_image.mode in ("RGBA", "P"):
                    pil_image = pil_image.convert("RGB")
                elif pil_image.mode != "RGB":
                    pil_image = pil_image.convert("RGB")
                pil_images.append(pil_image)
            except Exception as e:
                st.warning(f"Could not read {uploaded_file.name}: {e}")

        if pil_images:
            st.image(
                pil_images,
                caption=[f"Product Image {i + 1}" for i in range(len(pil_images))],
                use_container_width=True
            )

    product_name = st.text_input("Product Name (Optional)")
    features = st.text_area("Key Features / Notes (Optional)")
    tone = st.selectbox(
        "Tone of Voice", 
        ["Persuasive & Commercial", "Trendy & Casual", "Minimalist & Luxury", "Technical & Informative"]
    )
    generate_btn = st.button("Generate Descriptions & SEO", type="primary", use_container_width=True)

with col2:
    st.subheader("Generated Assets")
    if generate_btn:
        if not pil_images and not product_name.strip() and not features.strip():
            st.warning("Please upload at least one product image or provide product details.")
        else:
            prompt = f"""
You are an expert e-commerce copywriter, SEO strategist, objective market analyst,
and strict but fair product critic. Analyze the product using the supplied images
and user context. Do not claim visual details or specifications that cannot be
reasonably established from the inputs.

User Context:
- Product Name: {product_name.strip() if product_name.strip() else 'Infer from visual details; state uncertainty if needed'}
- Features / Notes: {features.strip() if features.strip() else 'Extract only supportable details from the images'}
- Tone: {tone}
- Number of supplied images: {len(pil_images)}

Generate an e-commerce and research package structured in Markdown:

### 1. SEO-Optimized Title (under 60 characters)
### 2. Short Description (1-2 sentences)
### 3. Key Feature Bullets (4-5 bullets)
### 4. SEO Keywords (5 primary and 5 long-tail)
### 5. Meta Description (150-160 characters, with a CTA)
### 6. Recommended Image Alt Text
### 7. AI Verdict & Buying Advice
- Give an honest, balanced assessment of whether this product appears worth buying.
- Explain who may benefit from it and who should avoid it.
- Separate facts supported by the input from assumptions or information that needs checking.
- Do not make unsupported claims about performance, safety, durability, or quality.

### 8. Competitor Comparison Table (2-4 alternatives, when appropriate)
- If the user entered a broad category (for example, "wireless earphones"), compare 2-4 relevant, popular alternatives.
- Use a Markdown table with: Product Name, Estimated Price Range, Key Pros, Key Cons, and Value-for-Money Verdict.
- If a specific product is named, compare it with 2-4 relevant alternatives when enough reliable information is available.
- Prices and product availability vary by country and date. State the market/region and that prices are estimates; do not invent precise current prices.
- Use web search to verify current product names, pricing context, and comparisons. Cite source URLs where available.
- If reliable information cannot be found, clearly say so rather than making up facts.

### 9. Customer Reviews & Testimonials (3-5 real reviews, if verifiable)
- Use web search to look for genuine customer reviews on identifiable platforms, such as retailer listings or official brand stores.
- Include 3-5 reviews only when the review text, rating, and source page can be verified.
- For each, provide a short excerpt or faithful paraphrase, the displayed rating (if available), the platform, and a direct source URL.
- Do NOT invent, simulate, or present AI-written text as a real customer testimonial.
- Do not imply a review is from a platform unless the source page supports that attribution.
- If no verifiable reviews are found, explicitly write: "No verifiable customer reviews were retrieved in this run." Do not fill the section with fabricated examples.
- Keep any quoted review excerpts brief and respect source/platform terms.

Important: Web search availability does not guarantee that every review page is accessible. Clearly distinguish retrieved evidence from your own analysis. Do not present generated marketing copy as a customer quote.
"""
            contents = [prompt]
            contents.extend(pil_images)

            # Google Search grounding is enabled to help retrieve current market information
            # and verifiable review sources. The prompt forbids inventing customer testimonials.
            research_config = types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())]
            )

            # Models tried in order of priority; if one gives 503, the next is tried automatically
            candidate_models = [
                "gemini-3.5-flash-lite",
                "gemini-3.8-flash",
                "gemini-3.6-flash",
                "gemini-flash-latest"
            ]

            response_text = None
            successful_model = None

            with st.spinner("Analyzing images, researching alternatives and review sources, and creating the SEO package..."):
                for model_name in candidate_models:
                    try:
                        response = client.models.generate_content(
                            model=model_name,
                            contents=contents,
                            config=research_config
                        )
                        if response.text:
                            response_text = response.text
                            successful_model = model_name

                            # Add URLs from Gemini's grounding metadata so users can
                            # inspect the web sources used for market/review research.
                            grounding_sources = []
                            try:
                                candidates = getattr(response, "candidates", None) or []
                                metadata = getattr(candidates[0], "grounding_metadata", None) if candidates else None
                                chunks = getattr(metadata, "grounding_chunks", None) or []
                                for chunk in chunks:
                                    web_source = getattr(chunk, "web", None)
                                    uri = getattr(web_source, "uri", None) if web_source else None
                                    title = getattr(web_source, "title", None) if web_source else None
                                    if uri and uri not in [item[1] for item in grounding_sources]:
                                        grounding_sources.append((title or uri, uri))
                            except Exception:
                                # Keep the generated package usable if metadata shape differs by SDK version.
                                grounding_sources = []

                            if grounding_sources:
                                response_text += "\n\n### Web Research Sources\n"
                                response_text += "\n".join(
                                    f"- [{title}]({uri})" for title, uri in grounding_sources
                                )
                            break
                    except APIError as e:
                        if e.code == 503:
                            # 503 high demand: continue to the next model in the candidate list
                            continue
                        else:
                            st.error(f"API Error ({model_name}): {e.message}")
                            break
                    except Exception as e:
                        st.error(f"Unexpected error with {model_name}: {e}")
                        break

            if response_text:
                st.caption(f"Generated using `{successful_model}`")
                st.markdown(response_text)
                st.download_button(
                    label="Download SEO Package (.txt)",
                    data=response_text,
                    file_name="product_seo_package.txt",
                    mime="text/plain",
                    use_container_width=True
                )
            elif not st.session_state.get("_error_shown"):
                st.error("The request could not be completed. This may be temporary, or the selected model may not support Google Search grounding. Check the API error above or try again shortly.")

st.markdown(
    """
    <style>
    .footer-container {
        margin-top: 60px;
        padding: 30px 20px 20px 20px;
        border-radius: 18px;
        background: linear-gradient(145deg, rgba(17, 24, 39, 0.95), rgba(15, 23, 42, 0.98));
        border: 1px solid rgba(99, 102, 241, 0.3);
        box-shadow: 0 10px 30px -10px rgba(79, 70, 229, 0.25);
        color: #e2e8f0;
        text-align: center;
        font-family: inherit;
    }
    .footer-badge {
        display: inline-block;
        padding: 4px 14px;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 700;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        background: linear-gradient(90deg, #6366f1, #a855f7);
        color: #ffffff;
        margin-bottom: 12px;
        box-shadow: 0 0 12px rgba(168, 85, 247, 0.4);
    }
    .footer-title {
        font-size: 1.15rem;
        font-weight: 600;
        margin: 0 0 6px 0;
        color: #f8fafc;
    }
    .footer-sub {
        font-size: 0.88rem;
        color: #94a3b8;
        margin-bottom: 18px;
    }
    .members-grid {
        display: flex;
        flex-wrap: wrap;
        justify-content: center;
        gap: 10px;
        margin-bottom: 20px;
    }
    .member-pill {
        background: rgba(30, 41, 59, 0.85);
        border: 1px solid rgba(148, 163, 184, 0.2);
        padding: 6px 16px;
        border-radius: 12px;
        font-size: 0.85rem;
        color: #f1f5f9;
        font-weight: 500;
        transition: all 0.2s ease-in-out;
    }
    .member-pill:hover {
        border-color: #818cf8;
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(99, 102, 241, 0.25);
    }
    .footer-disclaimer {
        font-size: 0.78rem;
        color: #64748b;
        border-top: 1px solid rgba(148, 163, 184, 0.15);
        padding-top: 14px;
        margin-top: 8px;
    }
    </style>

    <div class="footer-container">
        <span class="footer-badge">AI Product SEO Generator</span>
        <div class="footer-title">Made with ❤️ by<br>Team Solo Leveling</div>
        <div class="footer-sub">Generative AI Project &bull; M.Sc. AI (Part 1)</div>
        <div class="members-grid">
            <div class="member-pill">⚡ Hadi Sheikh</div>
            <div class="member-pill">⚡ Rushikesh</div>
            <div class="member-pill">⚡ Sujal Singh</div>
            <div class="member-pill">⚡ Farhan</div>
        </div>
        <div class="footer-disclaimer">
            ⚠️ Gemini is an AI and can make mistakes. Please verify critical details and SEO output before publishing.
        </div>
    </div>
    """,
    unsafe_allow_html=True
)