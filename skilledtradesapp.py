import streamlit as st
import requests
import json
import pandas as pd

# Retrieve secrets from Streamlit
GOOGLE_CSE_ID = st.secrets["google_cse_id"]
GOOGLE_API_KEY = st.secrets["google_api_key"]
COLLEGE_SCORECARD_API_KEY = st.secrets["college_scorecard_api_key"]

# State Abbreviations
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

# Trades
TRADES = [
    "Manufacturing", 
    "Automotive", 
    "Construction", 
    "Energy", 
    "Healthcare", 
    "Information Technology"
]

# CIP Synonyms for each trade
CIP_SYNONYMS = {
    "Manufacturing": [
        "manufacturing", "industrial technology", "industrial production",
        "machining", "welding", "fabrication"
    ],
    "Automotive": [
        "automotive", "auto mechanics", "vehicle maintenance",
        "diesel technology", "collision repair"
    ],
    "Construction": [
        "construction", "carpentry", "plumbing", "HVAC",
        "electrician", "welding"
    ],
    "Energy": [
        "energy", "renewable energy", "power generation", 
        "utilities", "oil and gas", "wind technology"
    ],
    "Healthcare": [
        "healthcare", "nursing", "medical assisting", 
        "health sciences", "public health"
    ],
    "Information Technology": [
        "information technology", "IT", "computer science", 
        "software development", "networking", "cybersecurity"
    ]
}

def google_cse_search(query: str, num_results=5):
    """
    Perform a Google Custom Search with the given query, returning up to `num_results` items.
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

def fetch_bls_data(trade: str, state: str):
    """
    1) Search specifically for 2022-2032 occupational projections for (trade) in (state) site:bls.gov
    2) If empty, fallback to national query.
    """
    query_state = f"2022-2032 occupational projections for {trade} in {state} site:bls.gov"
    results_state = google_cse_search(query_state, num_results=5)
    if results_state:
        return results_state

    # Fallback to national
    query_national = f"2022-2032 occupational projections for {trade} site:bls.gov"
    return google_cse_search(query_national, num_results=5)

def fetch_job_listings(trade: str, state: str):
    """
    Google CSE for Indeed job listings for the trade & state.
    """
    query = f"Indeed job listings for {trade} in {state}"
    results = google_cse_search(query, num_results=5)
    return results

def fetch_cip_colleges_for_keyword(keyword: str, abbrev: str) -> list:
    """
    Fetches colleges from College Scorecard that match the given `keyword`
    in CIP titles, for the specified state abbreviation.
    """
    url = "https://api.data.gov/ed/collegescorecard/v1/schools"
    params = {
        "api_key": COLLEGE_SCORECARD_API_KEY,
        "school.state": abbrev,
        "latest.programs.cip_4_digit.title__icontains": keyword,
        "per_page": 100,
        "fields": "school.name,latest.cost.tuition.in_state,latest.programs.cip_4_digit.title"
    }
    resp = requests.get(url, params=params)
    if resp.status_code != 200:
        return []

    data = resp.json()
    return data.get("results", [])

def fetch_cip_colleges(trade: str, state: str) -> list:
    """
    Uses CIP_SYNONYMS to gather colleges for multiple synonyms,
    merging them into one combined list (deduplicating by name).
    """
    abbrev = state_abbrev_map.get(state)
    if not abbrev:
        return []

    synonyms = CIP_SYNONYMS.get(trade, [trade.lower()])
    all_colleges = {}
    for kw in synonyms:
        results = fetch_cip_colleges_for_keyword(kw, abbrev)
        for item in results:
            name = item.get("school.name", "N/A")
            if name not in all_colleges:
                all_colleges[name] = item
    return list(all_colleges.values())

def build_college_dataframe(trade: str, state: str) -> pd.DataFrame:
    """
    Builds a DataFrame from the CIP-based college lookups for multiple synonyms.
    """
    raw_colleges = fetch_cip_colleges(trade, state)
    if not raw_colleges:
        return pd.DataFrame()

    table_rows = []
    for item in raw_colleges:
        name = item.get("school.name", "N/A")
        tuition = item.get("latest.cost.tuition.in_state", "N/A")
        cip_entries = item.get("latest.programs.cip_4_digit", [])
        cip_titles = [x.get("title", "N/A") for x in cip_entries if x.get("title")]
        row = {
            "College/University": name,
            "Tuition Cost": tuition,
            "CIP Titles": ", ".join(cip_titles) if cip_titles else "N/A"
        }
        table_rows.append(row)

    return pd.DataFrame(table_rows)

def main():
    st.title("Industry & Career Insights (Google CSE + CIP Synonyms)")
    st.markdown("""
        **Features**:
        1. BLS 2022–2032 projections (site:bls.gov) with fallback to national if state-level is empty
        2. CIP-based college searches using synonyms (College Scorecard)
        3. Indeed job listings (Google CSE)
        
        This avoids Jina/Firecrawl and should be lighter on resources.
    """)

    trade = st.selectbox("Select a Trade", TRADES)
    state = st.selectbox("Select a State", list(state_abbrev_map.keys()))

    if st.button("Fetch Data"):
        with st.spinner("Retrieving BLS Data..."):
            bls_results = fetch_bls_data(trade, state)
            st.subheader("BLS Data / Workforce Outlook")
            if not bls_results:
                st.write("No results found.")
            else:
                for item in bls_results:
                    st.write(f"**{item.get('title')}**")
                    st.write(item.get("snippet"))
                    st.write(item.get("link"))
                    st.write("---")

        with st.spinner("Retrieving Colleges..."):
            df_colleges = build_college_dataframe(trade, state)
            st.subheader("Colleges & Universities")
            if df_colleges.empty:
                st.write("No colleges found for this state & trade.")
            else:
                st.dataframe(df_colleges)

        with st.spinner("Retrieving Job Listings..."):
            job_results = fetch_job_listings(trade, state)
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
