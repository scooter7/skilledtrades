import streamlit as st
from agno.agent import Agent
from agno.tools.firecrawl import FirecrawlTools
from agno.models.openai import OpenAIChat

# Retrieve API keys from Streamlit secrets
OPENAI_API_KEY = st.secrets["openai_api_key"]
FIRECRAWL_API_KEY = st.secrets["firecrawl_api_key"]

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

# Create a shared OpenAIChat model instance with the API key
model = OpenAIChat(
    id="gpt-4o",
    max_tokens=1024,
    temperature=0.5,
    api_key=OPENAI_API_KEY
)

if st.button("Fetch Data"):
    # Create individual agents with the shared model and FirecrawlTools.
    bls_agent = Agent(
        name="BLS Projections Agent",
        role="Retrieves BLS projections for a given industry and state.",
        tools=[FirecrawlTools(api_key=FIRECRAWL_API_KEY, scrape=False, crawl=True)],
        model=model
    )
    education_agent = Agent(
        name="Education Programs Agent",
        role="Retrieves educational program details from colleges and universities.",
        tools=[FirecrawlTools(api_key=FIRECRAWL_API_KEY, scrape=False, crawl=True)],
        model=model
    )
    linkedin_agent = Agent(
        name="LinkedIn Jobs Agent",
        role="Retrieves LinkedIn job listings for a given industry and state.",
        tools=[FirecrawlTools(api_key=FIRECRAWL_API_KEY, scrape=False, crawl=True)],
        model=model
    )

    # Define queries for each task
    bls_query = (
        f"Retrieve Bureau of Labor Statistics projections for the {selected_trade} industry in {selected_state}."
    )
    education_query = (
        f"List the colleges and universities in {selected_state} that offer programs to train for a career in {selected_trade}. "
        "Provide details including program offerings, descriptions, tuition price, and program length."
    )
    linkedin_query = (
        f"Get current LinkedIn job listings for the {selected_trade} industry in {selected_state}. "
        "Include job title, company name, location, and a brief job description."
    )

    # Run each query using the corresponding agent
    with st.spinner("Fetching BLS projections..."):
        bls_response = bls_agent.run(bls_query)
        st.subheader("Bureau of Labor Statistics Projections")
        st.write(bls_response.content)

    with st.spinner("Fetching Educational Programs..."):
        education_response = education_agent.run(education_query)
        st.subheader("Educational Programs")
        st.write(education_response.content)

    with st.spinner("Fetching LinkedIn Job Listings..."):
        linkedin_response = linkedin_agent.run(linkedin_query)
        st.subheader("LinkedIn Job Listings")
        st.write(linkedin_response.content)
