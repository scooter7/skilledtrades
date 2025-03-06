import streamlit as st
import requests
import json
import pandas as pd
from agno.agent import Agent
from agno.tools.firecrawl import FirecrawlTools
from agno.models.openai import OpenAIChat

# Retrieve API keys from Streamlit secrets
OPENAI_API_KEY = st.secrets["openai_api_key"]
FIRECRAWL_API_KEY = st.secrets["firecrawl_api_key"]
GOOGLE_CSE_ID = st.secrets["google_cse_id"]
GOOGLE_API_KEY = st.secrets["google_api_key"]
COLLEGE_SCORECARD_API_KEY = st.secrets["college_scorecard_api_key"]

st.title("Industry & Career Insights Agent")
st.markdown(
    """
    This app retrieves data for your selected trade and state:
    - **Bureau of Labor Statistics (BLS) Projections**
    - **Colleges & Universities Educational Programs**
    - **Job Listings (via Indeed)**
    """
)

# Define available trades and states.
trades = [
    "Manufacturing", "Automotive", "Construction", "Energy", "Healthcare", "Information Technology"
]
states = [
    "Alabama", "Alaska", "Arizona", "Arkansas", "California", "Colorado", "Connecticut", "Delaware", 
    "Florida", "Georgia", "Hawaii", "Idaho", "Illinois", "Indiana", "Iowa", "Kansas", "Kentucky", 
    "Louisiana", "Maine", "Maryland", "Massachusetts", "Michigan", "Minnesota", "Mississippi", 
    "Missouri", "Montana", "Nebraska", "Nevada", "New Hampshire", "New Jersey", "New Mexico", 
    "New York", "North Carolina", "North Dakota", "Ohio", "Oklahoma", "Oregon", "Pennsylvania", 
    "Rhode Island", "South Carolina", "South Dakota", "Tennessee", "Texas", "Utah", "Vermont", 
    "Virginia", "Washington", "West Virginia", "Wisconsin", "Wyoming"
]

selected_trade = st.selectbox("Select a Trade", trades)
selected_state = st.selectbox("Select a State", states)

# Create a shared OpenAIChat model instance
model = OpenAIChat(
    id="gpt-4o",
    max_tokens=1024,
    temperature=0.5,
    api_key=OPENAI_API_KEY
)

# Create an agent for BLS queries (using FirecrawlTools)
bls_agent = Agent(
    name="BLS Projections Agent",
    role="Retrieves BLS projections for a given industry and state.",
    tools=[FirecrawlTools(api_key=FIRECRAWL_API_KEY, scrape=False, crawl=True)],
    model=model
)

# Create an agent for educational program details (for additional details via OpenAI)
education_agent = Agent(
    name="Education Programs Agent",
    role="Extracts manufacturing program details from college web data.",
    tools=[FirecrawlTools(api_key=FIRECRAWL_API_KEY, scrape=False, crawl=True)],
    model=model
)

# Create a function to fetch a table of educational program data using the College Scorecard API and agent queries.
def fetch_education_programs_table(state: str, industry: str, agent: Agent):
    """
    Retrieves a list of colleges from the College Scorecard API and queries each one
    for manufacturing program details. Returns a DataFrame with the columns:
    College/University, Degree Type, Tuition Cost, Program Duration,
    Offers Microcredentials, and Mentions AI in Program Description.
    """
    url = "https://api.data.gov/ed/collegescorecard/v1/schools"
    params = {
         "api_key": COLLEGE_SCORECARD_API_KEY,
         "school.state": state,
         "per_page": 5,  # limiting to 5 for demo purposes
         "fields": "school.name,latest.cost.tuition.in_state"
    }
    response = requests.get(url, params=params)
    if response.status_code != 200:
         st.error("Error fetching college data: " + response.text)
         return None
    data = response.json()
    schools = data.get("results", [])
    table_data = []
    for school in schools:
         college_name = school.get("school.name", "N/A")
         tuition_cost = school.get("latest.cost.tuition.in_state", "N/A")
         # Build a query to extract manufacturing program details
         query = (
             f"Provide details about the manufacturing program at {college_name}. "
             "Return the following information in JSON format with keys: "
             "'degree type', 'program duration', 'offers microcredentials', "
             "and 'mentions AI in program description'. If data is unavailable, use 'N/A'."
         )
         try:
             details_response = agent.run(query)
             # Attempt to parse the response as JSON
             details_json = json.loads(details_response.content)
         except Exception as e:
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
    df = pd.DataFrame(table_data)
    return df

# Function to fetch job listings from Indeed using Google CSE
def fetch_job_listings_indeed(industry: str, state: str):
    query = f"{industry} jobs {state} site:indeed.com"
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
         results = data.get("items", [])
         formatted_results = []
         for item in results:
             formatted_results.append({
                  "title": item.get("title"),
                  "snippet": item.get("snippet"),
                  "link": item.get("link")
             })
         return formatted_results
    else:
         return [{"error": response.status_code, "message": response.text}]

# Define query for BLS projections.
bls_query = f"Retrieve Bureau of Labor Statistics projections for the {selected_trade} industry in {selected_state}."

if st.button("Fetch Data"):
    with st.spinner("Fetching BLS projections..."):
         bls_response = bls_agent.run(bls_query)
         st.subheader("Bureau of Labor Statistics Projections")
         st.write(bls_response.content)
    
    # --- Educational Programs Section ---
    with st.spinner("Fetching Educational Programs..."):
         edu_df = fetch_education_programs_table(selected_state, selected_trade, education_agent)
         if edu_df is not None:
             st.subheader("Educational Programs")
             st.dataframe(edu_df)
         else:
             st.error("No educational program data available.")
    
    # --- Job Listings Section (using Indeed) ---
    with st.spinner("Fetching Job Listings from Indeed..."):
         indeed_results = fetch_job_listings_indeed(selected_trade, selected_state)
         st.subheader("Job Listings (Indeed)")
         if indeed_results and "error" not in indeed_results[0]:
             for item in indeed_results:
                 st.write(f"**{item.get('title')}**")
                 st.write(item.get("snippet"))
                 st.write(item.get("link"))
                 st.markdown("---")
         else:
             st.write("Error fetching job listings:", indeed_results)
