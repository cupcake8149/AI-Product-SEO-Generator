# AI Product Description & SEO Generator

A Streamlit web app that uses the Google Gemini API to create product descriptions and SEO content from product details and/or an image.

## Files
- `app.py` — Streamlit application
- `requirements.txt` — Python dependencies
- `.gitignore` — excludes local secrets and generated files
- `.env` — local API key placeholder (never commit this file)

## Run locally (Windows PowerShell)

1. Install Python if it is not already installed.
2. Open PowerShell in this project folder.
3. Create and activate a virtual environment:

   ```powershell
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   ```

4. Install dependencies:

   ```powershell
   pip install -r requirements.txt
   ```

5. Open `.env` and replace `paste_your_actual_api_key_here` with your Gemini API key.
6. Start the app:

   ```powershell
   streamlit run app.py
   ```

7. Open the local URL Streamlit prints (normally http://localhost:8501).

## Deploy to Streamlit Community Cloud

1. Push `app.py`, `requirements.txt`, `.gitignore`, and `README.md` to a GitHub repository.
2. Do **not** commit `.env`.
3. Create a Streamlit Community Cloud app using `app.py` as the main file.
4. In Advanced settings / Secrets, add:

   ```toml
   GEMINI_API_KEY = "your_actual_api_key_here"
   ```

5. Deploy.

## Important
Keep your Gemini API key private. The `.env` file in this starter ZIP contains only a placeholder; it is not a working API key.
