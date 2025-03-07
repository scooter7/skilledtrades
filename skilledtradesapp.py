import streamlit as st
import requests
import pandas as pd
import json

# Agno imports
from agno.agent import Agent
from agno.tools.firecrawl import FirecrawlTools
from agno.models.openai import OpenAIChat

# Retrieve secrets
OPENAI_API_KEY = st.secrets["openai_api_key"]
FIRECRAWL_API_KEY = st.secrets["firecrawl_api_key"]
COLLEGE_SCORECARD_API_KEY = st.secrets["college_scorecard_api_key"]

# Create an Agent with FirecrawlTools
agent = Agent(
    name="FirecrawlAgent",
    tools=[FirecrawlTools(api_key=FIRECRAWL_API_KEY, scrape=False, crawl=True)],
    model=OpenAIChat(api_key=OPENAI_API_KEY),  # If you want GPT-based summarization
    show_tool_calls=True,  # Optional: see debug info
    markdown=True
)

# Example CIP codes for each trade
CIP_CODES = {
    "Manufacturing": ["15.0613", "15.0805", "48.0000", "48.0501", "48.0508"],
    "Automotive": ["47.0604", "47.0613", "47.0603"],
    "Construction": ["46.0000", "46.0201", "46.0302", "46.0503", "46.0412"],
    "Energy": ["15.0503", "03.0209", "47.0501"],
    "Healthcare": ["51.0000", "51.3801", "51.0801", "51.0707"],
    "Information Technology": ["11.0101", "11.0201", "11.1003", "11.0901"]
}

# Trades & State abbreviations
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

def fetch_cip_colleges(trade: str, state: str) -> list:
    """
    For the given trade, gather CIP codes from CIP_CODES,
    query College Scorecard, and merge results by school name.
    """
    abbrev = STATE_ABBREV_MAP.get(state)
    if not abbrev:
        return []

    codes = CIP_CODES.get(trade, [])
    all_colleges = {}
    for code in codes:
        url = "https://api.data.gov/ed/collegescorecard/v1/schools"
        params = {
            "api_key": COLLEGE_SCORECARD_API_KEY,
            "school.state": abbrev,
            "latest.programs.cip_4_digit.code": code,
            "per_page": 100,
            "fields": "school.name,latest.cost.tuition.in_state,latest.programs.cip_4_digit.title"
        }
        resp = requests.get(url, params=params)
        if resp.status_code == 200:
            data = resp.json()
            results = data.get("results", [])
            for item in results:
                name = item.get("school.name", "N/A")
                if name not in all_colleges:
                    all_colleges[name] = item
    return list(all_colleges.values())

def build_college_dataframe(trade: str, state: str) -> pd.DataFrame:
    raw_data = fetch_cip_colleges(trade, state)
    if not raw_data:
        return pd.DataFrame()

    rows = []
    for item in raw_data:
        name = item.get("school.name", "N/A")
        tuition = item.get("latest.cost.tuition.in_state", "N/A")
        cip_entries = item.get("latest.programs.cip_4_digit", [])
        cip_titles = [x.get("title", "N/A") for x in cip_entries if x.get("title")]
        rows.append({
            "College/University": name,
            "Tuition Cost": tuition,
            "CIP Titles": ", ".join(cip_titles) if cip_titles else "N/A"
        })
    return pd.DataFrame(rows)

def main():
    st.title("Industry & Career Insights (Agno Agent + FirecrawlTools + CIP Codes)")
    st.markdown("""
        **This app** uses an Agno `Agent` with `FirecrawlTools` to:
        1. **Fetch BLS / workforce data** for a selected trade & state (fallback to national).
        2. **Retrieve Indeed job listings** for that trade & state.
        
        It also uses the **College Scorecard** API (via CIP codes) to list relevant colleges.
        
        **Note**: Firecrawl can be resource-intensive on free-tier Streamlit.
    """)

    selected_trade = st.selectbox("Select a Trade", TRADES)
    selected_state = st.selectbox("Select a State", STATES)

    if st.button("Fetch Data"):
        with st.spinner("Retrieving BLS data..."):
            bls_info = fetch_bls_data(selected_trade, selected_state)
            st.subheader("BLS / Workforce Outlook")
            st.write(bls_info)

        with st.spinner("Retrieving Colleges..."):
            df_colleges = build_college_dataframe(selected_trade, selected_state)
            st.subheader("Colleges & Universities")
            if df_colleges.empty:
                st.write("No colleges found for this state & trade.")
            else:
                st.dataframe(df_colleges)

        with st.spinner("Retrieving Job Listings..."):
            jobs_info = fetch_job_listings(selected_trade, selected_state)
            st.subheader("Indeed Job Listings")
            st.write(jobs_info)

if __name__ == "__main__":
    main()
