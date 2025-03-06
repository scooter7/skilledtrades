import streamlit as st
import requests
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
    - **LinkedIn Job Listings**
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

# --- Educational Programs Functions ---

def fetch_education_programs_google(state: str, industry: str):
    """
    Uses Google Custom Search Engine to look for college/university pages
    that list programs related to the specified industry in the given state.
    """
    # Refine the query to target manufacturing or relevant programs
    query = f"{industry} manufacturing programs colleges {state} site:edu"
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

def fetch_education_programs_scorecard(state: str, industry: str):
    """
    Alternative: Uses the College Scorecard API to retrieve structured data about
    colleges in the given state. This function is simplified; you might need to refine
    the query and process the response to match your requirements.
    """
    url = "https://api.data.gov/ed/collegescorecard/v1/schools"
    params = {
         "api_key": COLLEGE_SCORECARD_API_KEY,
         "school.state": state,
         "per_page": 10,
         # Example fields; adjust as needed
         "fields": "id,school.name,school.city,school.state,latest.cost.tuition.in_state"
    }
    response = requests.get(url, params=params)
    if response.status_code == 200:
         return response.json()
    else:
         return {"error": response.status_code, "message": response.text}

# --- Main Agents for BLS and LinkedIn (using Firecrawl) ---

# Create a shared OpenAIChat model instance with the API key
model = OpenAIChat(
    id="gpt-4o",
    max_tokens=1024,
    temperature=0.5,
    api_key=OPENAI_API_KEY
)

# Create agents for BLS and LinkedIn queries
bls_agent = Agent(
    name="BLS Projections Agent",
    role="Retrieves BLS projections for a given industry and state.",
    tools=[FirecrawlTools(api_key=FIRECRAWL_API_KEY, scrape=False, crawl=True)],
    model=model
)

linkedin_agent = Agent(
    name="LinkedIn Jobs Agent",
    role="Retrieves LinkedIn job listings for a given industry and state.",
    tools=[FirecrawlTools(api_key=FIRECRAWL_API_KEY, scrape=False, crawl=True)],
    model=model
)

# Define queries for BLS and LinkedIn
bls_query = f"Retrieve Bureau of Labor Statistics projections for the {selected_trade} industry in {selected_state}."
linkedin_query = (
    f"Get current LinkedIn job listings for the {selected_trade} industry in {selected_state}. "
    "Include job title, company name, location, and a brief job description."
)

if st.button("Fetch Data"):
    with st.spinner("Fetching BLS projections..."):
         bls_response = bls_agent.run(bls_query)
         st.subheader("Bureau of Labor Statistics Projections")
         st.write(bls_response.content)
    
    # --- Educational Programs Display ---
    # Option 1: Using Google Custom Search Engine
    with st.spinner("Fetching Educational Programs via Google Custom Search..."):
         edu_results = fetch_education_programs_google(selected_state, selected_trade)
         st.subheader("Educational Programs (Google Custom Search)")
         if edu_results and "error" not in edu_results[0]:
             for item in edu_results:
                 st.write(f"**{item.get('title')}**")
                 st.write(item.get("snippet"))
                 st.write(item.get("link"))
                 st.markdown("---")
         else:
             st.write("No results or error:", edu_results)
    
    # Option 2: Using College Scorecard API (uncomment to use)
    # with st.spinner("Fetching Educational Programs via College Scorecard API..."):
    #      scorecard_results = fetch_education_programs_scorecard(selected_state, selected_trade)
    #      st.subheader("Educational Programs (College Scorecard)")
    #      st.write(scorecard_results)
    
    with st.spinner("Fetching LinkedIn Job Listings..."):
         linkedin_response = linkedin_agent.run(linkedin_query)
         st.subheader("LinkedIn Job Listings")
         st.write(linkedin_response.content)
