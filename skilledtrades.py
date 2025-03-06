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

# --- Function to fetch job listings from Indeed using Google CSE ---
def fetch_job_listings_indeed(industry: str, state: str):
    """
    Uses Google Custom Search Engine to find job listings on Indeed.com.
    """
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

# Create a shared OpenAIChat model instance with the API key for the BLS query.
model = OpenAIChat(
    id="gpt-4o",
    max_tokens=1024,
    temperature=0.5,
    api_key=OPENAI_API_KEY
)

# Create an agent for the BLS projections using FirecrawlTools.
bls_agent = Agent(
    name="BLS Projections Agent",
    role="Retrieves BLS projections for a given industry and state.",
    tools=[FirecrawlTools(api_key=FIRECRAWL_API_KEY, scrape=False, crawl=True)],
    model=model
)

# Define query for BLS projections.
bls_query = f"Retrieve Bureau of Labor Statistics projections for the {selected_trade} industry in {selected_state}."

if st.button("Fetch Data"):
    with st.spinner("Fetching BLS projections..."):
         bls_response = bls_agent.run(bls_query)
         st.subheader("Bureau of Labor Statistics Projections")
         st.write(bls_response.content)
    
    # Educational Programs Section (using Google CSE as before)
    with st.spinner("Fetching Educational Programs via Google Custom Search..."):
         edu_query = f"{selected_trade} manufacturing programs colleges {selected_state} site:edu"
         edu_url = "https://www.googleapis.com/customsearch/v1"
         edu_params = {
             "key": GOOGLE_API_KEY,
             "cx": GOOGLE_CSE_ID,
             "q": edu_query,
             "num": 10
         }
         edu_response = requests.get(edu_url, params=edu_params)
         if edu_response.status_code == 200:
             edu_data = edu_response.json()
             edu_results = edu_data.get("items", [])
             st.subheader("Educational Programs (Google Custom Search)")
             for item in edu_results:
                 st.write(f"**{item.get('title')}**")
                 st.write(item.get("snippet"))
                 st.write(item.get("link"))
                 st.markdown("---")
         else:
             st.write("Error fetching educational programs:", edu_response.text)
    
    # Fetch job listings from Indeed
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
