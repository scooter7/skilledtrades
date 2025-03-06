import streamlit as st
from agno.agent import Agent
from agno.tools.jina import JinaReaderTools
from agno.models.openai import OpenAIChat

# A simple map of U.S. states for demonstration (add more if needed)
STATE_LIST = [
    "Alabama", "Alaska", "Arizona", "Arkansas", "California", "Colorado", 
    "Connecticut", "Delaware", "Florida", "Georgia", "Hawaii", "Idaho", 
    "Illinois", "Indiana", "Iowa", "Kansas", "Kentucky", "Louisiana", 
    "Maine", "Maryland", "Massachusetts", "Michigan", "Minnesota", 
    "Mississippi", "Missouri", "Montana", "Nebraska", "Nevada", 
    "New Hampshire", "New Jersey", "New Mexico", "New York", 
    "North Carolina", "North Dakota", "Ohio", "Oklahoma", "Oregon", 
    "Pennsylvania", "Rhode Island", "South Carolina", "South Dakota", 
    "Tennessee", "Texas", "Utah", "Vermont", "Virginia", "Washington", 
    "West Virginia", "Wisconsin", "Wyoming"
]

TRADE_LIST = [
    "Manufacturing",
    "Automotive",
    "Construction",
    "Energy",
    "Healthcare",
    "Information Technology"
]

def main():
    st.title("Industry & Career Insights via Jina Reader")
    st.markdown("""
    This app retrieves:
    1. **BLS Projections** for a chosen trade & state (fallback to national if none found).
    2. **Colleges** offering programs for that trade in the chosen state.
    3. **Job Listings** from Indeed for the trade & state.
    ---
    """)

    selected_trade = st.selectbox("Select a Trade", TRADE_LIST)
    selected_state = st.selectbox("Select a State", STATE_LIST)

    if st.button("Fetch Data"):
        # 1. BLS Data
        with st.spinner("Searching BLS data..."):
            bls_prompt = (
                f"Search for: BLS data or workforce outlook for '{selected_trade}' in '{selected_state}'. "
                "If no state-level data found, fallback to national data. Summarize the findings clearly."
            )
            bls_result = agent.run(bls_prompt)
            st.subheader("BLS Projections")
            st.write(bls_result.content)

        # 2. Colleges
        with st.spinner("Searching colleges..."):
            college_prompt = (
                f"Search for: colleges or universities in '{selected_state}' offering programs for '{selected_trade}'. "
                "Provide the results in a table-like summary with columns: name, location, degrees offered, "
                "approx tuition cost, microcredentials (yes/no), mentions AI (yes/no)."
            )
            college_result = agent.run(college_prompt)
            st.subheader("Colleges & Universities")
            st.write(college_result.content)

        # 3. Indeed Jobs
        with st.spinner("Searching job listings..."):
            job_prompt = (
                f"Search for: Indeed job listings for '{selected_trade}' in '{selected_state}'. "
                "List job title, company, location, and any direct links if available."
            )
            job_result = agent.run(job_prompt)
            st.subheader("Job Listings (Indeed)")
            st.write(job_result.content)

# Create a single Agent with JinaReaderTools, referencing secrets for API keys.
agent = Agent(
    tools=[JinaReaderTools(api_key=st.secrets["jina_api_key"])],
    model=OpenAIChat(api_key=st.secrets["openai_api_key"])
)

if __name__ == "__main__":
    main()
