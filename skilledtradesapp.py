import streamlit as st
import requests
import json
import pandas as pd

# Agno imports for Jina + OpenAI
from agno.agent import Agent
from agno.tools.jina import JinaReaderTools
from agno.models.openai import OpenAIChat

###############################################################################
# Retrieve Secrets (for Streamlit Cloud)
###############################################################################
JINA_API_KEY = st.secrets["jina_api_key"]
OPENAI_API_KEY = st.secrets["openai_api_key"]
COLLEGE_SCORECARD_API_KEY = st.secrets["college_scorecard_api_key"]

###############################################################################
# State Abbreviation Map (Full Name -> Two-Letter Code)
###############################################################################
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

###############################################################################
# Configuration: Trades, States, etc.
###############################################################################
TRADES = [
    "Manufacturing",
    "Automotive",
    "Construction",
    "Energy",
    "Healthcare",
    "Information Technology"
]

STATES = list(state_abbrev_map.keys())

###############################################################################
# BLS Data Retrieval (Multi-step fallback with Jina)
###############################################################################
def fetch_bls_data(agent: Agent, trade: str, state: str) -> str:
    """
    1) Attempt to find BLS or workforce data specifically for (trade) in (state).
    2) If the agent indicates no relevant info, fallback to searching national data
       plus state workforce development info.
    3) Return the summarized text.
    """

    # STEP 1: Search for state-level data
    state_search_prompt = (
        f"Search for: BLS data or workforce outlook for '{trade}' in '{state}'. "
        "If no relevant info is found, respond with EXACTLY 'NO_DATA_FOUND'. Summarize clearly."
    )
    response1 = agent.run(state_search_prompt)
    content1 = response1.content.strip()

    # Check if agent gave us a "NO_DATA_FOUND" fallback trigger
    if "NO_DATA_FOUND" in content1:
        # STEP 2: Fallback to national data + any state workforce dev info
        fallback_prompt = (
            f"Search for: national BLS data or outlook for '{trade}', plus any workforce dev info for '{state}'. "
            "Summarize clearly."
        )
        response2 = agent.run(fallback_prompt)
        return response2.content
    else:
        return content1

###############################################################################
# College Scorecard CIP-based Lookups
###############################################################################
def fetch_cip_colleges(trade: str, state: str) -> list:
    """
    Uses College Scorecard to find up to 100 colleges in the given state
    that have CIP program titles containing the trade keyword (case-insensitive).
    Returns a list of dicts with keys:
      - name
      - tuition_in_state
      - cip_titles (list of matching CIP program titles)
    """
    # Convert full state name to abbreviation
    abbrev = state_abbrev_map.get(state)
    if not abbrev:
        return []

    # CIP-based search for the trade keyword
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

###############################################################################
# Use Jina to refine program details for each college
###############################################################################
def refine_college_details(agent: Agent, college_name: str, trade: str) -> dict:
    """
    Asks JinaReaderTools to search for program details about (college_name) + (trade),
    returning a dictionary with the keys:
      - degree_type
      - program_duration
      - offers_microcredentials
      - mentions_ai
    If no data is found, sets them to "N/A".
    """
    prompt = (
        f"Search for: program details about '{trade}' at '{college_name}'. "
        "Return the info in JSON with these keys: "
        "degree_type, program_duration, offers_microcredentials, mentions_ai. "
        "If not found, respond with 'N/A' for each key."
    )
    resp = agent.run(prompt)
    content = resp.content.strip()

    # Attempt to parse as JSON
    try:
        details = json.loads(content)
        return {
            "degree_type": details.get("degree_type", "N/A"),
            "program_duration": details.get("program_duration", "N/A"),
            "offers_microcredentials": details.get("offers_microcredentials", "N/A"),
            "mentions_ai": details.get("mentions_ai", "N/A")
        }
    except:
        return {
            "degree_type": "N/A",
            "program_duration": "N/A",
            "offers_microcredentials": "N/A",
            "mentions_ai": "N/A"
        }

###############################################################################
# Build a DataFrame of all colleges + refined details
###############################################################################
def build_college_dataframe(agent: Agent, trade: str, state: str) -> pd.DataFrame:
    """
    1) Fetch CIP-based colleges from College Scorecard.
    2) For each college, ask JinaReaderTools for more details.
    3) Return a DataFrame with columns:
        College/University, Tuition Cost, CIP Titles,
        Degree Type, Program Duration, Offers Microcredentials, Mentions AI
    """
    raw_colleges = fetch_cip_colleges(trade, state)
    if not raw_colleges:
        return pd.DataFrame()  # empty

    table_rows = []
    for c in raw_colleges:
        details = refine_college_details(agent, c["name"], trade)
        row = {
            "College/University": c["name"],
            "Tuition Cost": c["tuition_in_state"],
            "CIP Titles": ", ".join(c["cip_titles"]) if c["cip_titles"] else "N/A",
            "Degree Type": details["degree_type"],
            "Program Duration": details["program_duration"],
            "Offers Microcredentials": details["offers_microcredentials"],
            "Mentions AI": details["mentions_ai"]
        }
        table_rows.append(row)

    return pd.DataFrame(table_rows)

###############################################################################
# Job Listings from Jina
###############################################################################
def fetch_job_listings(agent: Agent, trade: str, state: str) -> str:
    """
    Uses JinaReaderTools to search for Indeed job listings for the trade & state,
    returning a summarized string.
    """
    prompt = (
        f"Search for: Indeed job listings for '{trade}' in '{state}'. "
        "List job title, company, location, and any direct links if available."
    )
    response = agent.run(prompt)
    return response.content

###############################################################################
# Streamlit App
###############################################################################
def main():
    st.title("Industry & Career Insights (Jina + College Scorecard)")
    st.markdown(
        """
        This app retrieves:
        1. **BLS Projections** for a chosen trade & state (with explicit fallback to national data).
        2. **Colleges** offering CIP-based programs in that state, plus refined details from Jina.
        3. **Job Listings** from Indeed (via Jina search).

        **Note:** Keys are read from `st.secrets`, suitable for Streamlit Cloud deployment.
        ---
        """
    )

    # Let the user pick a trade & state
    selected_trade = st.selectbox("Select a Trade", TRADES)
    selected_state = st.selectbox("Select a State", STATES)

    if st.button("Fetch Data"):
        # BLS Data with fallback
        with st.spinner("Retrieving BLS Data..."):
            bls_content = fetch_bls_data(agent, selected_trade, selected_state)
            st.subheader("BLS Projections")
            st.write(bls_content)

        # College Scorecard + Jina for details
        with st.spinner("Retrieving Colleges..."):
            df_colleges = build_college_dataframe(agent, selected_trade, selected_state)
            st.subheader("Colleges & Universities")
            if df_colleges.empty:
                st.write("No colleges found for this state & trade.")
            else:
                st.dataframe(df_colleges)

        # Indeed Jobs (via Jina)
        with st.spinner("Retrieving Job Listings..."):
            job_content = fetch_job_listings(agent, selected_trade, selected_state)
            st.subheader("Job Listings (Indeed)")
            st.write(job_content)

###############################################################################
# Create the Agent with JinaReaderTools
###############################################################################
agent = Agent(
    tools=[JinaReaderTools(api_key=JINA_API_KEY)],
    model=OpenAIChat(api_key=OPENAI_API_KEY)
)

if __name__ == "__main__":
    main()
