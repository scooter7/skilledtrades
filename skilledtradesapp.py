import streamlit as st
import requests
import json
import pandas as pd

# Google CSE credentials from .streamlit/secrets.toml
GOOGLE_CSE_ID = st.secrets["google_cse_id"]
GOOGLE_API_KEY = st.secrets["google_api_key"]
# College Scorecard API key
COLLEGE_SCORECARD_API_KEY = st.secrets["college_scorecard_api_key"]

# State Abbreviation Map
state_abbrev_map = {
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

# Trades & States
TRADES = [
    "Manufacturing", "Automotive", "Construction", 
    "Energy", "Healthcare", "Information Technology"
]
STATES = list(state_abbrev_map.keys())

def google_cse_search(query: str, num_results=5):
    """
    Performs a Google Custom Search and returns up to `num_results` items.
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
    else:
        return []

def fetch_bls_data(trade: str, state: str):
    """
    1) Search for BLS data or workforce outlook for the given trade & state.
    2) If no results are found, do a second search for national BLS data/outlook.
    3) Return the final list of search items.
    """
    query_state = f"BLS data or workforce outlook for {trade} in {state}"
    results_state = google_cse_search(query_state, num_results=5)
    if results_state:
        return results_state

    # Fallback to national data if state-level is empty
    query_national = f"National BLS data or outlook for {trade}"
    results_national = google_cse_search(query_national, num_results=5)
    return results_national

def fetch_job_listings(trade: str, state: str):
    """
    Uses Google CSE to find Indeed job listings for the trade & state.
    """
    query = f"Indeed job listings for {trade} in {state}"
    results = google_cse_search(query, num_results=5)
    return results

def fetch_cip_colleges(trade: str, state: str) -> list:
    """
    Uses the College Scorecard API to find up to 100 colleges in the given state
    whose CIP program titles contain the trade keyword (case-insensitive).
    """
    abbrev = state_abbrev_map.get(state)
    if not abbrev:
        return []

    trade_keyword = trade.lower()
    url = "https://api.data.gov/ed/collegescorecard/v1/schools"
    params = {
        "api_key": COLLEGE_SCORECARD_API_KEY,
        "school.state": abbrev,
        "latest.programs.cip_4_digit.title__icontains": trade_keyword,
        "per_page": 100,
        "fields": "school.name,latest.cost.tuition.in_state,latest.programs.cip_4_digit.title"
    }
    resp = requests.get(url, params=params)
    if resp.status_code != 200:
        return []

    data = resp.json()
    results = data.get("results", [])
    colleges = []
    for item in results:
        name = item.get("school.name", "N/A")
        tuition = item.get("latest.cost.tuition.in_state", "N/A")
        cip_entries = item.get("latest.programs.cip_4_digit", [])
        cip_titles = [x.get("title", "N/A") for x in cip_entries if x.get("title")]
        colleges.append({
            "name": name,
            "tuition_in_state": tuition,
            "cip_titles": cip_titles
        })
    return colleges

def build_college_dataframe(trade: str, state: str) -> pd.DataFrame:
    """
    Converts the CIP-based college lookup into a Pandas DataFrame.
    """
    raw_colleges = fetch_cip_colleges(trade, state)
    if not raw_colleges:
        return pd.DataFrame()

    table_rows = []
    for c in raw_colleges:
        row = {
            "College/University": c["name"],
            "Tuition Cost": c["tuition_in_state"],
            "CIP Titles": ", ".join(c["cip_titles"]) if c["cip_titles"] else "N/A"
        }
        table_rows.append(row)

    return pd.DataFrame(table_rows)

def main():
    st.title("Industry & Career Insights (Google CSE + College Scorecard)")
    st.markdown("""
        **This app retrieves**:
        1. **BLS Projections** or Workforce Outlook (via Google CSE)
        2. **Colleges** offering CIP-based programs (via College Scorecard)
        3. **Indeed Job Listings** (via Google CSE)

        *No Jina or Firecrawl used—lighter resource usage.*
    """)

    selected_trade = st.selectbox("Select a Trade", TRADES)
    selected_state = st.selectbox("Select a State", STATES)

    if st.button("Fetch Data"):
        with st.spinner("Searching BLS data..."):
            bls_results = fetch_bls_data(selected_trade, selected_state)
            st.subheader("BLS Data / Workforce Outlook")
            if not bls_results:
                st.write("No results found.")
            else:
                for item in bls_results:
                    st.write(f"**{item.get('title')}**")
                    st.write(item.get("snippet"))
                    st.write(item.get("link"))
                    st.write("---")

        with st.spinner("Fetching Colleges..."):
            df_colleges = build_college_dataframe(selected_trade, selected_state)
            st.subheader("Colleges & Universities")
            if df_colleges.empty:
                st.write("No colleges found for this state & trade.")
            else:
                st.dataframe(df_colleges)

        with st.spinner("Searching Indeed Job Listings..."):
            job_results = fetch_job_listings(selected_trade, selected_state)
            st.subheader("Job Listings (Indeed)")
            if not job_results:
                st.write("No job listings found.")
            else:
                for item in job_results:
                    st.write(f"**{item.get('title')}**")
                    st.write(item.get("snippet"))
                    st.write(item.get("link"))
                    st.write("---")

if __name__ == "__main__":
    main()
