"""
ScrapeAgent Studio - Modern Web Application.
Interactive UI for universal web scraping, dynamic browser rendering,
and catalog data search & analytics.
"""
import io
import json
import os
import time
import pandas as pd
import streamlit as st

from agent import is_valid_url, normalize_url, check_bot_protection
from core.fetcher import fetch_page
from core.cleaner import clean_html
from core.extractor import UniversalExtractor
from config import DEFAULT_TIMEOUT, DEFAULT_USER_AGENT

# Page Configuration
st.set_page_config(
    page_title="ScrapeAgent Studio",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for modern, polished typography and cards
st.markdown(
    """
    <style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        margin-bottom: 0.2rem;
        color: #60a5fa;
    }
    .sub-header {
        font-size: 1.05rem;
        color: #94a3b8;
        margin-bottom: 1.5rem;
    }
    .metric-box {
        background-color: #1e293b;
        border: 1px solid #334155;
        border-radius: 8px;
        padding: 1rem;
        text-align: center;
    }
    .stButton>button {
        border-radius: 6px;
        font-weight: 600;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# --- Sidebar Configuration ---
st.sidebar.title("ScrapeAgent Studio")
st.sidebar.caption("Universal Web Scraping & Analytics Platform")

st.sidebar.markdown("---")
st.sidebar.subheader("Quick Presets")
preset_choice = st.sidebar.selectbox(
    "Select a pre-configured target:",
    [
        "None (Custom URL)",
        "Books Catalog (books.toscrape.com)",
        "Quotes to Scrape (quotes.toscrape.com)",
        "Hacker News (news.ycombinator.com)",
    ],
)

preset_urls = {
    "Books Catalog (books.toscrape.com)": "https://books.toscrape.com/",
    "Quotes to Scrape (quotes.toscrape.com)": "https://quotes.toscrape.com/",
    "Hacker News (news.ycombinator.com)": "https://news.ycombinator.com/",
}

default_url = preset_urls.get(preset_choice, "")

st.sidebar.markdown("---")
st.sidebar.subheader("Network Settings")
custom_timeout = st.sidebar.slider("Timeout (seconds)", min_value=5, max_value=60, value=DEFAULT_TIMEOUT)
engine_type = st.sidebar.radio(
    "Extraction Engine:",
    ["HTTP Engine (Fast & Lightweight)", "Headless Browser (Playwright / Dynamic JS)"],
    help="Use HTTP Engine for regular static websites. Choose Headless Browser for JavaScript-heavy Single Page Applications.",
)

st.sidebar.markdown("---")
st.sidebar.info(
    "**Notice**: Ensure compliance with target platforms' Terms of Service and `robots.txt` policies. "
    "Designed for research and testing purposes."
)

# --- Main Tabs ---
tab_scrape, tab_explore, tab_batch = st.tabs(
    ["Universal Web Scraper", "Dataset Explorer & Analytics", "Catalog Scraping Pipeline"]
)

# ==========================================
# TAB 1: UNIVERSAL WEB SCRAPER
# ==========================================
with tab_scrape:
    st.markdown('<div class="main-header">Universal Web Scraper</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="sub-header">Enter any public URL to automatically detect repeating data clusters and extract structured records.</div>',
        unsafe_allow_html=True,
    )

    col_url, col_btn = st.columns([5, 1])
    with col_url:
        input_url = st.text_input(
            "Target Web Address:",
            value=default_url,
            placeholder="e.g. https://books.toscrape.com/ or example.com",
            label_visibility="collapsed",
        )
    with col_btn:
        scrape_clicked = st.button("Scrape Data", type="primary", use_container_width=True)

    if scrape_clicked:
        if not input_url:
            st.warning("Please enter a target URL.")
        elif not is_valid_url(input_url):
            st.error(f"Invalid URL format: '{input_url}'. Please provide a valid address (e.g. 'https://example.com').")
        else:
            target_url = normalize_url(input_url)
            use_browser = "Headless Browser" in engine_type

            with st.status("Extracting structured data...", expanded=True) as status:
                start_time = time.time()
                try:
                    # 1. Fetching
                    st.write(f"Connecting to `{target_url}` using {'Playwright Chromium' if use_browser else 'HTTP client'}...")
                    if use_browser:
                        from core.browser_fetcher import fetch_page_browser
                        raw_html = fetch_page_browser(target_url, timeout_ms=custom_timeout * 1000)
                        status_code = 200
                        size_kb = len(raw_html.encode("utf-8")) // 1024
                    else:
                        resp = fetch_page(target_url, timeout=custom_timeout)
                        raw_html = resp.text
                        status_code = resp.status_code
                        size_kb = len(resp.content) // 1024

                    st.write(f"Response received: Status {status_code} ({size_kb} KB markup)")

                    # 2. Sanitizing
                    st.write("Sanitizing DOM (stripping script tags, styles, and noise)...")
                    soup = clean_html(raw_html)

                    # Bot protection check
                    block_reason = check_bot_protection(soup)
                    if block_reason:
                        st.warning(f"Anti-Bot Challenge Detected: {block_reason}. The target page blocked automated access.")
                        if not use_browser:
                            st.info("Tip: Try re-running with the 'Headless Browser' engine from the sidebar.")

                    # 3. Extracting
                    st.write("Universal Extractor analyzing DOM structure and repeating patterns...")
                    extractor = UniversalExtractor(base_url=target_url)
                    records = extractor.extract_all(soup)

                    elapsed = time.time() - start_time

                    if not records:
                        status.update(label="No structured data clusters found", state="error")
                        st.error("No repeating records or structured metadata could be automatically identified on this page.")
                    else:
                        status.update(label=f"Successfully extracted {len(records)} items in {elapsed:.2f}s", state="complete")
                        st.session_state["scraped_df"] = pd.DataFrame(records)
                        st.session_state["target_url"] = target_url

                except Exception as e:
                    status.update(label="Scraping Failed", state="error")
                    st.error(f"Extraction failed: {e}")

    # Display Scraped Results
    if "scraped_df" in st.session_state and not st.session_state["scraped_df"].empty:
        df = st.session_state["scraped_df"]
        st.markdown("### Extracted Records")

        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.metric("Total Items", len(df))
        with m2:
            price_col = next((c for c in df.columns if "price" in c.lower()), None)
            if price_col and pd.to_numeric(df[price_col], errors="coerce").notnull().any():
                avg_val = pd.to_numeric(df[price_col], errors="coerce").mean()
                st.metric("Average Price", f"£{avg_val:.2f}" if "£" in str(df[price_col].iloc[0]) or "currency" in df.columns else f"{avg_val:.2f}")
            else:
                st.metric("Columns", len(df.columns))
        with m3:
            link_col = next((c for c in df.columns if "url" in c.lower() or "link" in c.lower()), None)
            st.metric("Unique Links", df[link_col].nunique() if link_col else len(df))
        with m4:
            st.metric("Source", st.session_state.get("target_url", "").split("//")[-1].split("/")[0])

        # Interactive Table
        st.dataframe(df, use_container_width=True, hide_index=True)

        # Export Buttons
        col_exp1, col_exp2, _ = st.columns([1.5, 1.5, 3])
        with col_exp1:
            csv_buffer = io.StringIO()
            df.to_csv(csv_buffer, index=False, encoding="utf-8")
            st.download_button(
                label="Download as CSV",
                data=csv_buffer.getvalue(),
                file_name="scraped_data.csv",
                mime="text/csv",
                type="primary",
            )
        with col_exp2:
            json_str = df.to_json(orient="records", indent=2, force_ascii=False)
            st.download_button(
                label="Download as JSON",
                data=json_str,
                file_name="scraped_data.json",
                mime="application/json",
            )


# ==========================================
# TAB 2: DATASET EXPLORER & ANALYTICS
# ==========================================
with tab_explore:
    st.markdown('<div class="main-header">Dataset Explorer & Analytics</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="sub-header">Search, filter, analyze, and query catalog datasets using in-memory pandas operations.</div>',
        unsafe_allow_html=True,
    )

    # Dataset Loader (defaults to all_books.csv or books.csv, or allows upload)
    uploaded_file = st.file_uploader("Upload custom CSV dataset (optional):", type=["csv"])

    active_dataset = None
    if uploaded_file is not None:
        try:
            active_dataset = pd.read_csv(uploaded_file, encoding="utf-8")
            st.success(f"Loaded uploaded file: {uploaded_file.name} ({len(active_dataset)} rows)")
        except Exception as err:
            st.error(f"Failed to load file: {err}")
    elif os.path.exists("all_books.csv"):
        active_dataset = pd.read_csv("all_books.csv", encoding="utf-8")
        st.caption("Loaded default catalog dataset: `all_books.csv` (1,000 items from Day 2)")
    elif os.path.exists("books.csv"):
        active_dataset = pd.read_csv("books.csv", encoding="utf-8")
        st.caption("Loaded baseline catalog dataset: `books.csv` (20 items from Day 1)")

    if active_dataset is not None:
        # Preprocessing & Types
        eda_df = active_dataset.copy()
        if "price" in eda_df.columns:
            eda_df["price"] = pd.to_numeric(eda_df["price"], errors="coerce").fillna(0.0)
        if "rating" in eda_df.columns:
            eda_df["rating"] = pd.to_numeric(eda_df["rating"], errors="coerce").fillna(0).astype(int)
        if "stock_count" in eda_df.columns:
            eda_df["stock_count"] = pd.to_numeric(eda_df["stock_count"], errors="coerce").fillna(0).astype(int)

        # Query & Filter Controls
        f_col1, f_col2, f_col3 = st.columns([2, 2, 2])

        with f_col1:
            search_query = st.text_input("Search (title, description, category):", placeholder="e.g. python, mystery, art")

        with f_col2:
            if "category" in eda_df.columns:
                categories = ["All"] + sorted(eda_df["category"].dropna().unique().tolist())
                selected_cat = st.selectbox("Category Filter:", categories)
            else:
                selected_cat = "All"

        with f_col3:
            if "price" in eda_df.columns and eda_df["price"].max() > eda_df["price"].min():
                p_min = float(eda_df["price"].min())
                p_max = float(eda_df["price"].max())
                price_range = st.slider("Price Range (£):", min_value=p_min, max_value=p_max, value=(p_min, p_max))
            else:
                price_range = None

        # Apply Filters
        filtered = eda_df
        if search_query:
            query = search_query.lower()
            mask = pd.Series(False, index=filtered.index)
            for col in ["title", "description", "category"]:
                if col in filtered.columns:
                    mask |= filtered[col].astype(str).str.lower().str.contains(query, na=False)
            filtered = filtered[mask]

        if selected_cat != "All":
            filtered = filtered[filtered["category"] == selected_cat]

        if price_range:
            filtered = filtered[(filtered["price"] >= price_range[0]) & (filtered["price"] <= price_range[1])]

        # Stats Cards
        st.markdown("---")
        s1, s2, s3, s4 = st.columns(4)
        with s1:
            st.metric("Matching Books", len(filtered))
        with s2:
            if "price" in filtered.columns and not filtered.empty:
                st.metric("Avg Price", f"£{filtered['price'].mean():.2f}")
            else:
                st.metric("Avg Price", "-")
        with s3:
            if "rating" in filtered.columns and not filtered.empty:
                st.metric("Avg Rating", f"{filtered['rating'].mean():.2f} / 5")
            else:
                st.metric("Avg Rating", "-")
        with s4:
            if "stock_count" in filtered.columns and not filtered.empty:
                st.metric("Total Stock Units", int(filtered["stock_count"].sum()))
            else:
                st.metric("In Stock", len(filtered))

        # Filtered Table
        st.dataframe(filtered, use_container_width=True, hide_index=True)

        # Export filtered view
        buf = io.StringIO()
        filtered.to_csv(buf, index=False, encoding="utf-8")
        st.download_button(
            label=f"Download {len(filtered)} Filtered Records as CSV",
            data=buf.getvalue(),
            file_name="filtered_books.csv",
            mime="text/csv",
        )
    else:
        st.info("No catalog dataset found. Run Phase 1 or Phase 2 scraping to generate `books.csv` or `all_books.csv`.")


# ==========================================
# TAB 3: BATCH SCRAPING PIPELINE
# ==========================================
with tab_batch:
    st.markdown('<div class="main-header">Catalog Scraping Pipeline</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="sub-header">Run the multi-page pagination and detail enrichment scraper directly from the application.</div>',
        unsafe_allow_html=True,
    )

    st.write("This pipeline executes two-level catalog extraction (listing card + individual detail page for UPC, stock count, description, category).")

    p_col1, p_col2 = st.columns([2, 1])
    with p_col1:
        pages_to_scrape = st.number_input("Pages to Crawl (20 books/page):", min_value=1, max_value=50, value=2)
    with p_col2:
        st.write("")
        st.write("")
        start_batch = st.button("Launch Pipeline", type="primary")

    if start_batch:
        from scrape_all_books import run_full_catalog_scraper

        with st.spinner(f"Crawling {pages_to_scrape} pages and enriching detail pages..."):
            prog_bar = st.progress(0)
            status_text = st.empty()
            status_text.text("Connecting to books.toscrape.com...")

            batch_books = run_full_catalog_scraper(max_pages=pages_to_scrape, output_csv="all_books.csv")
            prog_bar.progress(100)
            status_text.text(f"Successfully scraped {len(batch_books)} books across {pages_to_scrape} pages!")

        st.success(f"Catalog saved to `all_books.csv`. Head over to the 'Dataset Explorer' tab to query your data!")
