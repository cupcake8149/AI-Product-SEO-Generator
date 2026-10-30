# AI Product Description & SEO Generator

Streamlit app using Gemini for image analysis and SEO writing, and Tavily for live web search.

## Features
- Upload multiple product images.
- Generate SEO titles, descriptions, feature bullets, keywords, meta descriptions, and alt text.
- Produce buying advice and competitor research using live search results.
- Search separately for product details, customer reviews, and alternatives.
- Rank and filter candidate search results for product/category relevance before passing them to Gemini.
- Exclude generic company-directory pages from product-level evidence and show only the filtered source set.
- Avoids using Gemini Google Search grounding, which was returning quota errors for this project.
- Download the generated report as Markdown.

## Configure Streamlit Community Cloud
In your app, open **Manage app → Settings → Secrets** and add both keys:

```toml
GEMINI_API_KEY = "your_gemini_api_key_here"
TAVILY_API_KEY = "your_tavily_api_key_here"
```

Save the secrets and reboot/redeploy the app. Never commit API keys to GitHub or share them in screenshots/chats.

## Run locally
1. Install Python 3.10 or newer.
2. Install dependencies: `python -m pip install -r requirements.txt`
3. Copy `.env.example` to `.env` and fill in your own API keys.
4. Run: `streamlit run app.py`

## Research accuracy
Tavily returns live search results and may include extracted page text, but search snippets can be incomplete. The app instructs Gemini not to invent reviews, prices, ratings, or URLs and displays the returned source links for manual verification. A source being returned by search does not by itself prove every claim in the generated report.
