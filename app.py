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
