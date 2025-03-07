import streamlit as st
import requests
import json
import pandas as pd

# Google CSE / College Scorecard credentials
GOOGLE_CSE_ID = st.secrets["google_cse_id"]
GOOGLE_API_KEY = st.secrets["google_api_key"]
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

# Trade List
TRADES = [
    "Manufacturing",
    "Automotive",
    "Construction",
    "Energy",
    "Healthcare",
    "Information Technology"
]

# CIP Codes for Each Trade
# These are partial examples; you may need more/other codes.
CIP_CODES = {
    "Manufacturing": [
        "15.0613",  # Manufacturing Technology/Technician
        "15.0805",  # Mechanical Engineering/Mechanical Technology/Technician
        "48.0000",  # Precision Production Trades, General
        "48.0501",  # Machine Tool Technology/Machinist
        "48.0508",  # Welding Technology/Welder
    ],
    "Automotive": [
        "47.0604",  # Automobile/Automotive Mechanics Technology/Technician
        "47.0613",  # Medium/Heavy Vehicle and Truck Technology/Technician
        "47.0603",  # Autobody/Collision and Repair Technology/Technician
    ],
    "Construction": [
        "46.0000",  # Construction Trades, General
        "46.0201",  # Carpentry/Carpenter
        "46.0302",  # Electrician
        "46.0503",  # Plumbing Technology/Plumber
        "46.0412",  # Building/Construction Site Management/Manager
    ],
    "Energy": [
        "15.0503",  # Energy Management and Systems Technology/Technician
        "03.0209",  # Renewable Energy
        "47.0501",  # Stationary Energy Sources Installer and Operator
        # You might add "Petroleum Technology" CIP codes, etc.
    ],
    "Healthcare": [
        "51.0000",  # Health Services/Allied Health/Health Sciences, General
        "51.3801",  # Registered Nursing/Registered Nurse
        "51.0801",  # Medical/Clinical Assistant
        "51.0707",  # Health Information/Medical Records Technology
    ],
    "Information Technology": [
        "11.0101",  # Computer and Information Sciences, General
        "11.0201",  # Computer Programming/Programmer, General
        "11.1003",  # Computer and Information Systems Security/Information Assurance
        "11.0901",  # Computer Systems Networking and Telecommunications
    ]
}

def google_cse_search(query: str, num_results=5):
    """
    Google Custom Search with `query`, returning up to `num_results` items.
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
    Multi-step approach:
      1) 2022-2032 occupational projections for {trade} in {state} site:bls.gov
      2) {state} workforce development {trade} job outlook
      3) 2022-2032 occupational projections for {trade} site:bls.gov (national fallback)
    """
    # Step 1: State-level BLS
    query_1 = f"2022-2032 occupational projections for {trade} in {state} site:bls.gov"
    results_1 = google_cse_search(query_1, num_results=5)
    if results_1:
        return results_1

    # Step 2: State workforce dev
    query_2 = f"{state} workforce development {trade} job outlook"
    results_2 = google_cse_search(query_2, num_results=5)
    if results_2:
        return results_2

    # Step 3: National BLS fallback
    query_3 = f"2022-2032 occupational projections for {trade} site:bls.gov"
    results_3 = google_cse_search(query_3, num_results=5)
    return results_3

def fetch_job_listings(trade: str, state: str):
    """
    Google CSE for Indeed job listings for the trade & state.
    """
    query = f"Indeed job listings for {trade} in {state}"
    return google_cse_search(query, num_results=5)

def fetch_cip_colleges_by_codes(cip_codes: list, abbrev: str) -> list:
    """
    Queries College Scorecard for all CIP codes in `cip_codes`, merges results into one list.
    """
    all_colleges = {}
    for code in cip_codes:
        url = "https://api.data.gov/ed/collegescorecard/v1/schools"
        params = {
            "api_key": COLLEGE_SCORECARD_API_KEY,
            "school.state": abbrev,
            "latest.programs.cip_4_digit.code": code,
            "per_page": 100,
            "fields": "school.name,latest.cost.tuition.in_state,latest.programs.cip_4_digit.title"
        }
        resp = requests.get(url, params=params)
        if resp.status_code != 200:
            continue

        data = resp.json()
        results = data.get("results", [])
        for item in results:
            name = item.get("school.name", "N/A")
            if name not in all_colleges:
                all_colleges[name] = item
    return list(all_colleges.values())

def build_college_dataframe(trade: str, state: str) -> pd.DataFrame:
    """
    For the given trade, gather CIP codes from CIP_CODES dict,
    query College Scorecard, and return a DataFrame.
    """
    abbrev = state_abbrev_map.get(state)
    if not abbrev:
        return pd.DataFrame()

    cip_list = CIP_CODES.get(trade, [])
    if not cip_list:
        return pd.DataFrame()

    raw_colleges = fetch_cip_colleges_by_codes(cip_list, abbrev)
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
    st.title("Industry & Career Insights (CIP Codes + Multi-step BLS)")
    st.markdown("""
        **Features**:
        1. **CIP-based** college lookups using official CIP codes for each trade
        2. **Multi-step BLS** approach for state-level data, workforce dev, then national fallback
        3. **Indeed** job listings via Google CSE
        
        This approach often yields better college matches than text synonyms.
    """)

    trade = st.selectbox("Select a Trade", TRADES)
    states = list(state_abbrev_map.keys())
    state = st.selectbox("Select a State", states)

    if st.button("Fetch Data"):
        with st.spinner("Retrieving BLS / Workforce Data..."):
            bls_results = fetch_bls_data(trade, state)
            st.subheader("BLS / Workforce Outlook")
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
