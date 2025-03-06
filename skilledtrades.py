import streamlit as st
import requests
import json
import pandas as pd

# Agno imports
from agno.agent import Agent
from agno.tools.firecrawl import FirecrawlTools
from agno.models.openai import OpenAIChat

# Retrieve API keys from Streamlit secrets
OPENAI_API_KEY = st.secrets["openai_api_key"]
FIRECRAWL_API_KEY = st.secrets["firecrawl_api_key"]
GOOGLE_CSE_ID = st.secrets["google_cse_id"]
GOOGLE_API_KEY = st.secrets["google_api_key"]
COLLEGE_SCORECARD_API_KEY = st.secrets["college_scorecard_api_key"]

# Mapping of full state names to two-letter abbreviations
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

# Define available trades
trades = [
    "Manufacturing", 
    "Automotive", 
    "Construction", 
    "Energy", 
    "Healthcare", 
    "Information Technology"
]

# Set up the Streamlit app
st.title("Industry & Career Insights Agent")
st.markdown(
    """
    This app retrieves data for your selected trade and state:
    - **Bureau of Labor Statistics (BLS) Projections** (with fallback if state-level data not found)
    - **Colleges & Universities Educational Programs** (via College Scorecard + OpenAI)
    - **Job Listings** (via Indeed + Google Custom Search)
    """
)

# User selections
selected_trade = st.selectbox("Select a Trade", trades)
states_list = list(state_abbrev_map.keys())  # all full state names
selected_state = st.selectbox("Select a State", states_list)

# Shared OpenAIChat model instance for the agents
model = OpenAIChat(
    id="gpt-4o",
    max_tokens=1024,
    temperature=0.5,
    api_key=OPENAI_API_KEY
)

# Agent for BLS data (via Firecrawl)
bls_agent = Agent(
    name="BLS Projections Agent",
    role="Retrieves BLS projections for a given industry and state (fallback to national if needed).",
    tools=[FirecrawlTools(api_key=FIRECRAWL_API_KEY, scrape=False, crawl=True)],
    model=model
)

# Agent for Education data (via Firecrawl + OpenAI)
education_agent = Agent(
    name="Education Programs Agent",
    role="Extracts program details from college web data.",
    tools=[FirecrawlTools(api_key=FIRECRAWL_API_KEY, scrape=False, crawl=True)],
    model=model
)

def fetch_bls_projections(trade: str, state: str) -> str:
    """
    Tries to retrieve state-level BLS projections for the chosen trade and state.
    If no valuable data is found, requests national-level data and 
    also attempts to gather info from the state's workforce development site.
    """
    query = (
        f"Retrieve BLS projections for the {trade} industry in {state}. "
        "If no valuable data is found at the state level, present national-level growth projections "
        f"and also gather data from the {state} workforce development site about job outlook "
        "for this industry. Provide a thorough answer."
    )
    response = bls_agent.run(query)
    return response.content

def fetch_education_programs_table(full_state_name: str, trade: str, agent: Agent) -> pd.DataFrame:
    """
    Uses the College Scorecard API to get up to 100 colleges in the given state 
    that have CIP program titles containing the trade (e.g., 'manufacturing').
    Then queries each college for details about the program (degree type, duration, 
    microcredentials, AI mention) via the agent.
    """
    # Convert full state name to abbreviation
    state_abbrev = state_abbrev_map.get(full_state_name)
    if not state_abbrev:
        st.error(f"Unable to map state '{full_state_name}' to an abbreviation.")
        return pd.DataFrame()

    # Convert trade to lowercase for CIP search
    trade_keyword = trade.lower()

    # Query College Scorecard, searching CIP titles for the trade keyword
    url = "https://api.data.gov/ed/collegescorecard/v1/schools"
    params = {
        "api_key": COLLEGE_SCORECARD_API_KEY,
        "school.state": state_abbrev,
        # CIP 4-digit title search for the trade keyword
        "latest.programs.cip_4_digit.title__icontains": trade_keyword,
        # Increase per_page to get more results
        "per_page": 100,
        "fields": "school.name,latest.cost.tuition.in_state,latest.programs.cip_4_digit.title"
    }
    response = requests.get(url, params=params)
    if response.status_code != 200:
        st.error("Error fetching college data: " + response.text)
        return pd.DataFrame()

    data = response.json()
    schools = data.get("results", [])
    if not schools:
        st.warning(f"No colleges found in {full_state_name} that match '{trade_keyword}' in CIP titles.")
        return pd.DataFrame()

    table_data = []
    for school in schools:
        college_name = school.get("school.name", "N/A")
        tuition_cost = school.get("latest.cost.tuition.in_state", "N/A")

        # We'll ask the agent for more program details
        # The agent will attempt to find or reason about them.
        query = (
            f"Provide details about the {trade} program at {college_name}. "
            "Return the following information in JSON format with keys: "
            "'degree type', 'program duration', 'offers microcredentials', "
            "'mentions AI in program description'. If data is unavailable, use 'N/A'."
        )
        try:
            details_response = agent.run(query)
            details_json = json.loads(details_response.content)
        except Exception:
            details_json = {
                "degree type": "N/A",
                "program duration": "N/A",
                "offers microcredentials": "N/A",
                "mentions AI in program description": "N/A"
            }

        table_data.append({
            "College/University": college_name,
            "Degree Type": details_json.get("degree type", "N/A"),
            "Tuition Cost": tuition_cost,
            "Program Duration": details_json.get("program duration", "N/A"),
            "Offers Microcredentials": details_json.get("offers microcredentials", "N/A"),
            "Mentions AI in Program Description": details_json.get("mentions AI in program description", "N/A")
        })

    return pd.DataFrame(table_data)

def fetch_job_listings_indeed(trade: str, state: str):
    """
    Uses Google Custom Search Engine to find job listings on Indeed.com
    for the given trade and state.
    """
    query = f"{trade} jobs {state} site:indeed.com"
    url = "https://www.googleapis.com/customsearch/v1"
    params = {
         "key": GOOGLE_API_KEY,
         "cx": GOOGLE_CSE_ID,
         "q": query,
         "num": 10
    }
    response = requests.get(url, params=params)
    if response.status_code == 200:
        data = response.json()
        return data.get("items", [])
    else:
        return [{"error": response.status_code, "message": response.text}]

if st.button("Fetch Data"):
    # 1. BLS Projections
    with st.spinner("Fetching BLS projections..."):
        bls_data = fetch_bls_projections(selected_trade, selected_state)
        st.subheader("Bureau of Labor Statistics Projections")
        st.write(bls_data)

    # 2. Educational Programs
    with st.spinner("Fetching Educational Programs..."):
        edu_df = fetch_education_programs_table(selected_state, selected_trade, education_agent)
        st.subheader("Educational Programs")
        if not edu_df.empty:
            st.dataframe(edu_df)
        else:
            st.write("No educational program data available for your selection.")

    # 3. Job Listings (Indeed via Google CSE)
    with st.spinner("Fetching Job Listings from Indeed..."):
        job_results = fetch_job_listings_indeed(selected_trade, selected_state)
        st.subheader("Job Listings (Indeed)")
        if job_results and "error" not in job_results[0]:
            for item in job_results:
                title = item.get("title", "N/A")
                snippet = item.get("snippet", "")
                link = item.get("link", "")
                st.write(f"**{title}**")
                st.write(snippet)
                st.write(link)
                st.markdown("---")
        else:
            st.write("Error fetching job listings:", job_results)
