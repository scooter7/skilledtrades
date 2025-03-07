import streamlit as st
# Import the Firecrawl client (adjust the import based on how the package is installed)
from firecrawl import FireCrawl  

# Retrieve API keys from Streamlit secrets
OPENAI_API_KEY = st.secrets["openai_api_key"]
FIRECRAWL_API_KEY = st.secrets["firecrawl_api_key"]

# Create an instance of the Firecrawl agent
firecrawl = FireCrawl(api_key=FIRECRAWL_API_KEY)

# Define functions that use Firecrawl to fetch data from various sources

def fetch_bls_projections(industry: str, state: str):
    # Create a query that describes exactly what you need.
    query = (
        f"Retrieve Bureau of Labor Statistics projections for the {industry} industry in {state}."
    )
    response = firecrawl.run(query, api_key=OPENAI_API_KEY)
    return response

def fetch_education_programs(state: str, industry: str):
    # Craft a query to extract data on relevant colleges and universities.
    query = (
        f"List the colleges and universities in {state} that offer programs to train "
        f"for a career in {industry}. For each institution, provide details including program offerings, "
        f"descriptions, tuition price, and program length. Compare these programs by institution."
    )
    response = firecrawl.run(query, api_key=OPENAI_API_KEY)
    return response

def fetch_linkedin_jobs(industry: str, state: str):
    # Build a query to pull job listings data from LinkedIn.
    query = (
        f"Get current LinkedIn job listings for the {industry} industry in {state}. "
        f"Provide job title, company name, location, and a brief job description."
    )
    response = firecrawl.run(query, api_key=OPENAI_API_KEY)
    return response

# Streamlit app layout

st.title("Industry & Career Insights Agent")
st.markdown("""
This agent uses Agno's Firecrawl tool to retrieve:
- **BLS Projections** for your selected industry and state.
- **Educational Programs** available at colleges/universities in your state for your industry.
- **LinkedIn Job Listings** for the industry in your state.
""")

# Define available trades and states.
trades = ["Manufacturing", "Automotive", "Construction", "Energy", "Healthcare", "Information Technology"]
states = [
    "Alabama", "Alaska", "Arizona", "Arkansas", "California", "Colorado", "Connecticut", "Delaware", 
    "Florida", "Georgia", "Hawaii", "Idaho", "Illinois", "Indiana", "Iowa", "Kansas", "Kentucky", 
    "Louisiana", "Maine", "Maryland", "Massachusetts", "Michigan", "Minnesota", "Mississippi", 
    "Missouri", "Montana", "Nebraska", "Nevada", "New Hampshire", "New Jersey", "New Mexico", 
    "New York", "North Carolina", "North Dakota", "Ohio", "Oklahoma", "Oregon", "Pennsylvania", 
    "Rhode Island", "South Carolina", "South Dakota", "Tennessee", "Texas", "Utah", "Vermont", 
    "Virginia", "Washington", "West Virginia", "Wisconsin", "Wyoming"
]

# User selections
selected_trade = st.selectbox("Select a Trade", trades)
selected_state = st.selectbox("Select a State", states)

if st.button("Fetch Data"):
    with st.spinner("Fetching BLS projections..."):
        bls_data = fetch_bls_projections(selected_trade, selected_state)
        st.subheader("Bureau of Labor Statistics Projections")
        st.write(bls_data)

    with st.spinner("Fetching educational program details..."):
        education_data = fetch_education_programs(selected_state, selected_trade)
        st.subheader("Colleges and Universities Educational Programs")
        st.write(education_data)

    with st.spinner("Fetching LinkedIn job listings..."):
        jobs_data = fetch_linkedin_jobs(selected_trade, selected_state)
        st.subheader("LinkedIn Job Listings")
        st.write(jobs_data)
