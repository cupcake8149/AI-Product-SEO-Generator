# AI Product Description & SEO Generator

A Streamlit application using Google's Gemini API to create SEO copy and research products.

## Features

- Upload multiple product images.
- Generate SEO titles, descriptions, feature bullets, keywords, meta descriptions, and alt text.
- Request a balanced buying verdict.
- Research competitor alternatives and estimated prices.
- Request 3–5 customer reviews with traceable source pages.
- Use Google Search grounding and display source links returned by Gemini.
- Download the generated report as Markdown.

## Important limitation

Search grounding does not guarantee that 3–5 genuine customer reviews will be found for every product. The prompt instructs the model not to invent reviews. Always open the original review pages and verify quotations, ratings, dates, prices, and model/region before presenting or publishing the results. Grounding links may support general claims without linking to the exact review itself.

## Setup locally

1. Install Python 3.10 or newer.
2. Open a terminal in this project folder.
3. Create and activate a virtual environment if desired.
4. Install dependencies:

   ```bash
   python -m pip install -r requirements.txt
   ```

5. Copy `.env.example` to `.env` and set `GEMINI_API_KEY` to your own key.
6. Run:

   ```bash
   streamlit run app.py
   ```

Get a Gemini API key from Google AI Studio. Never commit `.env` or publish your API key.

## Deploy on Streamlit Community Cloud

1. Push this project to a GitHub repository.
2. Create/select the app in Streamlit Community Cloud and set `app.py` as the entry point.
3. In app settings, open **Secrets** and add:

   ```toml
   GEMINI_API_KEY = "your_real_api_key"
   GEMINI_MODEL = "gemini-2.5-flash"
   ```

4. Deploy or reboot the app.

If your project does not have access to the configured model or Google Search grounding, check the current model availability and API error in **Manage app → Logs**. You can change `GEMINI_MODEL` to a model available to your API project.

## Project files

- `app.py` — Streamlit application
- `requirements.txt` — Python dependencies
- `.env.example` — environment variable template
- `.gitignore` — excludes secrets and Python cache
