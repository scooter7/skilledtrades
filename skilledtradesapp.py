import streamlit as st
import requests
import pandas as pd
import json

# Agno imports for Firecrawl
from agno.agent import Agent
from agno.tools.firecrawl import FirecrawlTools
from agno.models.openai import OpenAIChat

# Retrieve secrets
OPENAI_API_KEY = st.secrets["openai_api_key"]
FIRECRAWL_API_KEY = st.secrets["firecrawl_api_key"]
GOOGLE_CSE_ID = st.secrets["google_cse_id"]
GOOGLE_API_KEY = st.secrets["google_api_key"]

# Create an Agent with FirecrawlTools for BLS and Indeed
agent = Agent(
    name="FirecrawlAgent",
    tools=[FirecrawlTools(api_key=FIRECRAWL_API_KEY, scrape=False, crawl=True)],
    model=OpenAIChat(api_key=OPENAI_API_KEY),
    show_tool_calls=True,
    markdown=True
)

# For BLS & Indeed
TRADES = [
    "Manufacturing",
    "Automotive",
    "Construction",
    "Energy",
    "Healthcare",
    "Information Technology"
]

STATE_ABBREV_MAP = {
    "Alabama": "AL", "Alaska": "AK", "Arizona": "AZ", "Arkansas": "AR",
    "California": "CA", "Colorado": "CO", "Connecticut": "CT", "Delaware": "DE",
    "Florida": "FL", "Georgia": "GA", "Hawaii": "HI", "Idaho": "ID",
    "Illinois": "IL", "Indiana": "IN", "Iowa": "IA", "Kansas": "KS",
    "Kentucky": "KY", "Louisiana": "LA", "Maine": "ME", "Maryland": "MD",
    "Massachusetts": "MA", "Michigan": "MI", "Minnesota": "MN", "Mississippi": "MS",
    "Missouri": "MO", "Montana": "MT", "Nebraska": "NE", "Nevada": "NV",
    "New Hampshire": "NH", "New Jersey": "NJ", "New Mexico": "NM",
    "New York": "NY", "North Carolina": "NC", "North Dakota": "ND", "Ohio": "OH",
    "Oklahoma": "OK", "Oregon": "OR", "Pennsylvania": "PA", "Rhode Island": "RI",
    "South Carolina": "SC", "South Dakota": "SD", "Tennessee": "TN", "Texas": "TX",
    "Utah": "UT", "Vermont": "VT", "Virginia": "VA", "Washington": "WA",
    "West Virginia": "WV", "Wisconsin": "WI", "Wyoming": "WY"
}
STATES = list(STATE_ABBREV_MAP.keys())

def fetch_bls_data(trade: str, state: str) -> str:
    """
    Uses the Firecrawl-based agent to retrieve BLS or workforce data for the trade & state.
    If no state-level data is found, fallback to national data.
    """
    query = (
        f"Retrieve BLS or workforce outlook data for '{trade}' in '{state}'. "
        "If no valuable state-level info is found, provide national-level data. "
        "Try to include numeric projections if possible."
    )
    response = agent.run(query)
    return response.content

def fetch_job_listings(trade: str, state: str) -> str:
    """
    Uses Firecrawl to find Indeed job listings for the trade & state.
    """
    query = (
        f"Retrieve Indeed job listings for '{trade}' in '{state}'. "
        "List job titles, companies, and any direct links or short descriptions."
    )
    response = agent.run(query)
    return response.content

def google_cse_search(query: str, num_results=8):
    """
    Performs a Google Custom Search with the given query, returning up to `num_results` items.
    """
    url = "https://www.googleapis.com/customsearch/v1"
    params = {
        "key": GOOGLE_API_KEY,
        "cx": GOOGLE_CSE_ID,
        "q": query,
        "num": num_results
    }
    resp = requests.get(url, params=params)
    if resp.status_code == 200:
        data = resp.json()
        return data.get("items", [])
    return []

def fetch_colleges_google(trade: str, state: str) -> list:
    """
    Use Google CSE to find colleges in `state` that offer programs in `trade`.
    We'll do a simple query with site:.edu, which often yields .edu pages for colleges.
    """
    # Example: "colleges in California that offer manufacturing programs site:.edu"
    query = f"colleges in {state} that offer {trade} programs site:.edu"
    results = google_cse_search(query, num_results=8)
    return results

def build_college_dataframe_google(trade: str, state: str) -> pd.DataFrame:
    """
    Builds a simple DataFrame from Google CSE results (title, snippet, link).
    """
    raw_results = fetch_colleges_google(trade, state)
    if not raw_results:
        return pd.DataFrame()

    rows = []
    for item in raw_results:
        title = item.get("title", "N/A")
        snippet = item.get("snippet", "")
        link = item.get("link", "")
        rows.append({
            "Title": title,
            "Snippet": snippet,
            "Link": link
        })
    return pd.DataFrame(rows)

def main():
    st.title("Industry & Career Insights (Firecrawl + Google CSE for Colleges)")
    st.markdown("""
        **This app** uses:
        1. **Firecrawl** (Agno Agent + FirecrawlTools) for BLS and Indeed job listings.
        2. **Google Custom Search** to find colleges in the selected state that offer
           programs for the selected trade (via site:.edu queries).
        
        This approach avoids the College Scorecard CIP codes, so we get a simple list
        of search results from Google. 
    """)

    selected_trade = st.selectbox("Select a Trade", TRADES)
    selected_state = st.selectbox("Select a State", STATES)

    if st.button("Fetch Data"):
        with st.spinner("Retrieving BLS data..."):
            bls_info = fetch_bls_data(selected_trade, selected_state)
            st.subheader("BLS / Workforce Outlook")
            st.write(bls_info)

        with st.spinner("Retrieving Colleges..."):
            df_colleges = build_college_dataframe_google(selected_trade, selected_state)
            st.subheader("Colleges & Universities")
            if df_colleges.empty:
                st.write("No colleges found from Google search.")
            else:
                st.dataframe(df_colleges)

        with st.spinner("Retrieving Job Listings..."):
            jobs_info = fetch_job_listings(selected_trade, selected_state)
            st.subheader("Indeed Job Listings")
            st.write(jobs_info)

if __name__ == "__main__":
    main()
