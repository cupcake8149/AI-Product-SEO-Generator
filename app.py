import os
import streamlit as st
from dotenv import load_dotenv
from PIL import Image
from google import genai
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
    uploaded_file = st.file_uploader(
        "Upload Product Image", 
        type=["png", "jpg", "jpeg", "webp"]
    )

    pil_image = None
    if uploaded_file:
        pil_image = Image.open(uploaded_file)
        st.image(pil_image, caption="Product Preview", use_container_width=True)

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
        if not pil_image and not product_name.strip() and not features.strip():
            st.warning("Please upload a product image or provide product details.")
        else:
            prompt = f"""
You are an expert e-commerce copywriter and SEO strategist.
Analyze the product provided.

User Context:
- Product Name: {product_name.strip() if product_name.strip() else 'Infer from visual details'}
- Features / Notes: {features.strip() if features.strip() else 'Extract from visual appearance'}
- Tone: {tone}

Generate an e-commerce and SEO package structured in Markdown:
### 1. SEO-Optimized Title (Under 60 chars)
### 2. Short Description (1-2 sentences)
### 3. Key Feature Bullets (4-5 bullets)
### 4. SEO Keywords (5 Primary, 5 Long-tail)
### 5. Meta Description (150-160 chars with CTA)
### 6. Recommended Image Alt Text
"""
            contents = [prompt]
            if pil_image:
                if pil_image.mode in ("RGBA", "P"):
                    pil_image = pil_image.convert("RGB")
                contents.append(pil_image)

            # Models tried in order of priority; if one gives 503, the next is tried automatically
            candidate_models = [
                "gemini-3.5-flash-lite",
                "gemini-3.8-flash",
                "gemini-3.6-flash",
                "gemini-flash-latest"
            ]

            response_text = None
            successful_model = None

            with st.spinner("Analyzing product and creating SEO package..."):
                for model_name in candidate_models:
                    try:
                        response = client.models.generate_content(
                            model=model_name,
                            contents=contents
                        )
                        if response.text:
                            response_text = response.text
                            successful_model = model_name
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
                st.error("All models are currently experiencing high demand. Please retry in 30 seconds.")

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
        <span class="footer-badge">Solo Leveling</span>
        <div class="footer-title">Crafted with ❤️ by Team Solo Leveling</div>
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