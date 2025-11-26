import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

# Page config
st.set_page_config(
    page_title="Joseph Mews - Sales Funnel",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 1rem;
    }
    .stButton>button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 5px;
        padding: 0.5rem 2rem;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# Check if Google Sheets credentials are available
try:
    import gspread
    from google.oauth2.service_account import Credentials
    GOOGLE_SHEETS_AVAILABLE = True
except ImportError:
    GOOGLE_SHEETS_AVAILABLE = False

@st.cache_resource
def get_google_sheets_client():
    """Initialize Google Sheets client with credentials"""
    if not GOOGLE_SHEETS_AVAILABLE:
        return None

    try:
        # Try to get credentials from Streamlit secrets first (for Streamlit Cloud)
        if "gcp_service_account" in st.secrets:
            credentials_dict = st.secrets["gcp_service_account"]
        # Fall back to environment variables (for Render, Railway, etc.)
        else:
            import os
            import json

            # Try JSON environment variable first
            if os.getenv("GCP_SERVICE_ACCOUNT"):
                credentials_dict = json.loads(os.getenv("GCP_SERVICE_ACCOUNT"))
            # Build from individual environment variables
            else:
                credentials_dict = {
                    "type": os.getenv("GCP_SERVICE_ACCOUNT_TYPE", "service_account"),
                    "project_id": os.getenv("GCP_SERVICE_ACCOUNT_PROJECT_ID"),
                    "private_key_id": os.getenv("GCP_SERVICE_ACCOUNT_PRIVATE_KEY_ID"),
                    "private_key": os.getenv("GCP_SERVICE_ACCOUNT_PRIVATE_KEY", "").replace("\\n", "\n"),
                    "client_email": os.getenv("GCP_SERVICE_ACCOUNT_CLIENT_EMAIL"),
                    "client_id": os.getenv("GCP_SERVICE_ACCOUNT_CLIENT_ID"),
                    "auth_uri": os.getenv("GCP_SERVICE_ACCOUNT_AUTH_URI", "https://accounts.google.com/o/oauth2/auth"),
                    "token_uri": os.getenv("GCP_SERVICE_ACCOUNT_TOKEN_URI", "https://oauth2.googleapis.com/token"),
                    "auth_provider_x509_cert_url": os.getenv("GCP_SERVICE_ACCOUNT_AUTH_PROVIDER_X509_CERT_URL", "https://www.googleapis.com/oauth2/v1/certs"),
                    "client_x509_cert_url": os.getenv("GCP_SERVICE_ACCOUNT_CLIENT_X509_CERT_URL")
                }

        credentials = Credentials.from_service_account_info(
            credentials_dict,
            scopes=[
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive"
            ]
        )
        client = gspread.authorize(credentials)
        return client
    except Exception as e:
        st.error(f"Error connecting to Google Sheets: {e}")
        return None

@st.cache_data(ttl=300)
def load_data_from_sheets(_client, spreadsheet_url):
    """Load data from Google Sheets"""
    try:
        sheet = _client.open_by_url(spreadsheet_url)
        worksheet = sheet.worksheet("Lead Tracker")
        data = worksheet.get_all_records()
        df = pd.DataFrame(data)
        
        # Convert date columns
        date_columns = ['Date Collected', 'Last Contact Date', 'Next Follow-up']
        for col in date_columns:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')
        
        return df
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame()

def get_funnel_metrics(df):
    """Calculate funnel metrics"""
    stages = [
        'Lead Collected',
        'Contact Attempted',
        'Contact Made',
        'Qualified Lead',
        'Discovery/Presentation',
        'Opportunity',
        'Negotiation',
        'Contract Signed'
    ]
    
    metrics = []
    for stage in stages:
        count = len(df[df['Current Stage'] == stage]) if len(df) > 0 else 0
        metrics.append({'Stage': stage, 'Count': count})
    
    return pd.DataFrame(metrics)

def get_summary_stats(df):
    """Get summary statistics"""
    if len(df) == 0:
        return {
            'total_leads': 0,
            'qualified': 0,
            'won': 0,
            'lost': 0,
            'win_rate': 0,
            'active': 0
        }
    
    total_leads = len(df)
    qualified_stages = ['Qualified Lead', 'Discovery/Presentation', 'Opportunity', 
                       'Negotiation', 'Contract Signed']
    qualified = len(df[df['Current Stage'].isin(qualified_stages)])
    won = len(df[df['Current Stage'] == 'Contract Signed'])
    lost = len(df[df['Current Stage'] == 'Lost'])
    
    win_rate = (won / total_leads * 100) if total_leads > 0 else 0
    
    return {
        'total_leads': total_leads,
        'qualified': qualified,
        'won': won,
        'lost': lost,
        'win_rate': win_rate,
        'active': total_leads - won - lost
    }

def get_source_performance(df):
    """Get performance by lead source"""
    if len(df) == 0:
        return pd.DataFrame()
    
    sources = df.groupby('Lead Source').agg({
        'Lead ID': 'count',
    }).rename(columns={'Lead ID': 'Total'}).reset_index()
    
    qualified_stages = ['Qualified Lead', 'Discovery/Presentation', 'Opportunity', 
                       'Negotiation', 'Contract Signed']
    
    for idx, row in sources.iterrows():
        source_df = df[df['Lead Source'] == row['Lead Source']]
        qualified = len(source_df[source_df['Current Stage'].isin(qualified_stages)])
        won = len(source_df[source_df['Current Stage'] == 'Contract Signed'])
        
        sources.at[idx, 'Qualified'] = int(qualified)
        sources.at[idx, 'Won'] = int(won)
        sources.at[idx, 'Qual Rate'] = round((qualified / row['Total'] * 100), 1) if row['Total'] > 0 else 0
        sources.at[idx, 'Win Rate'] = round((won / row['Total'] * 100), 1) if row['Total'] > 0 else 0
    
    return sources

def get_agent_performance(df):
    """Get performance by agent"""
    if len(df) == 0:
        return pd.DataFrame()
    
    agent_df = df[df['Agent Assigned'].notna() & (df['Agent Assigned'] != 'Unassigned')]
    
    if len(agent_df) == 0:
        return pd.DataFrame()
    
    agents = agent_df.groupby('Agent Assigned').agg({
        'Lead ID': 'count',
    }).rename(columns={'Lead ID': 'Total'}).reset_index()
    
    qualified_stages = ['Qualified Lead', 'Discovery/Presentation', 'Opportunity', 
                       'Negotiation', 'Contract Signed']
    
    for idx, row in agents.iterrows():
        agent_leads = agent_df[agent_df['Agent Assigned'] == row['Agent Assigned']]
        qualified = len(agent_leads[agent_leads['Current Stage'].isin(qualified_stages)])
        won = len(agent_leads[agent_leads['Current Stage'] == 'Contract Signed'])
        
        agents.at[idx, 'Qualified'] = int(qualified)
        agents.at[idx, 'Won'] = int(won)
        agents.at[idx, 'Qual Rate'] = round((qualified / row['Total'] * 100), 1) if row['Total'] > 0 else 0
        agents.at[idx, 'Win Rate'] = round((won / row['Total'] * 100), 1) if row['Total'] > 0 else 0
    
    return agents.sort_values('Won', ascending=False)

def main():
    # Sidebar navigation
    st.sidebar.title("🏢 Joseph Mews")
    st.sidebar.markdown("---")
    
    page = st.sidebar.radio(
        "Dashboard View",
        ["🎯 Admin Dashboard", "🏘️ Client Dashboard", "👤 Agent Dashboard"]
    )
    
    st.sidebar.markdown("---")
    
    # Google Sheets URL input
    spreadsheet_url = st.sidebar.text_input(
        "Google Sheets URL",
        value=st.session_state.get('spreadsheet_url', ''),
        help="Paste your Joseph Mews Funnel Tracker URL here"
    )
    
    if spreadsheet_url:
        st.session_state['spreadsheet_url'] = spreadsheet_url
    
    # Refresh button
    if st.sidebar.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()
    
    st.sidebar.markdown("---")
    st.sidebar.info("💡 Dashboard updates every 5 minutes automatically")
    
    # Load data
    if not spreadsheet_url:
        st.warning("👈 Please enter your Google Sheets URL in the sidebar")
        st.info("""
        **How to get your Google Sheets URL:**
        1. Open your Joseph Mews Funnel Tracker
        2. Copy the URL from your browser
        3. Paste it in the sidebar
        """)
        return
    
    if not GOOGLE_SHEETS_AVAILABLE:
        st.error("Google Sheets integration is not available. Please check your configuration.")
        return
    
    client = get_google_sheets_client()
    if not client:
        st.error("Could not connect to Google Sheets. Please check your credentials in Streamlit secrets.")
        return
    
    df = load_data_from_sheets(client, spreadsheet_url)
    
    if df.empty:
        st.error("No data found. Please check your Google Sheets URL and ensure the 'Lead Tracker' sheet exists.")
        return
    
    # Route to appropriate page
    if page == "🎯 Admin Dashboard":
        show_admin_dashboard(df)
    elif page == "🏘️ Client Dashboard":
        show_client_dashboard(df)
    else:
        show_agent_dashboard(df)

def show_admin_dashboard(df):
    """Admin dashboard with full analytics"""
    st.markdown('<h1 class="main-header">🎯 Admin Dashboard</h1>', unsafe_allow_html=True)
    st.markdown("Complete funnel overview and analytics")
    
    # Summary stats
    stats = get_summary_stats(df)
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("Total Leads", stats['total_leads'])
    with col2:
        st.metric("Qualified", stats['qualified'], 
                 delta=f"{stats['qualified']/stats['total_leads']*100:.1f}%" if stats['total_leads'] > 0 else "0%")
    with col3:
        st.metric("Won", stats['won'], delta=f"{stats['win_rate']:.1f}%")
    with col4:
        st.metric("Lost", stats['lost'])
    with col5:
        st.metric("Active Pipeline", stats['active'])
    
    st.markdown("---")
    
    # Charts row 1
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📊 Sales Funnel")
        funnel_data = get_funnel_metrics(df)
        if len(funnel_data) > 0:
            fig = px.bar(funnel_data, x='Count', y='Stage', orientation='h',
                        color_discrete_sequence=['#667eea'])
            fig.update_layout(height=400, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No data available for funnel chart")
    
    with col2:
        st.subheader("📈 Stage Distribution")
        if len(df) > 0:
            stage_data = df['Current Stage'].value_counts().reset_index()
            stage_data.columns = ['Stage', 'Count']
            fig = px.pie(stage_data, values='Count', names='Stage',
                        color_discrete_sequence=px.colors.sequential.Purples_r)
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No data available for distribution chart")
    
    st.markdown("---")
    
    # Tables row 2
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🎯 Source Performance")
        source_perf = get_source_performance(df)
        if len(source_perf) > 0:
            st.dataframe(source_perf, use_container_width=True, hide_index=True)
        else:
            st.info("No source data available")
    
    with col2:
        st.subheader("👥 Agent Leaderboard")
        agent_perf = get_agent_performance(df)
        if len(agent_perf) > 0:
            st.dataframe(agent_perf, use_container_width=True, hide_index=True)
        else:
            st.info("No agent data available")
    
    # Recent activity
    st.markdown("---")
    st.subheader("📋 Recent Leads")
    if len(df) > 0:
        recent_leads = df.sort_values('Date Collected', ascending=False).head(10)
        display_cols = ['Lead ID', 'First Name', 'Last Name', 'Current Stage', 
                       'Agent Assigned', 'Date Collected']
        display_cols = [col for col in display_cols if col in df.columns]
        st.dataframe(recent_leads[display_cols], use_container_width=True, hide_index=True)
    else:
        st.info("No recent leads to display")

def show_client_dashboard(df):
    """Client dashboard for Joseph Mews"""
    st.markdown('<h1 class="main-header">🏘️ Joseph Mews Campaign Dashboard</h1>', unsafe_allow_html=True)
    st.markdown("Birmingham Property Campaign Performance")
    
    # Hero stats
    stats = get_summary_stats(df)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("📬 Total Leads", stats['total_leads'], help="Total campaign reach")
    with col2:
        st.metric("✅ Qualified Buyers", stats['qualified'],
                 delta=f"{stats['qualified']/stats['total_leads']*100:.1f}% qual rate" if stats['total_leads'] > 0 else "0%")
    with col3:
        st.metric("🎉 Sales Closed", stats['won'],
                 delta=f"{stats['win_rate']:.1f}% conversion")
    with col4:
        st.metric("💼 Active Pipeline", stats['active'], help="Deals in progress")
    
    st.markdown("---")
    
    # Charts
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📊 Lead Pipeline Progression")
        funnel_data = get_funnel_metrics(df)
        if len(funnel_data) > 0:
            funnel_data = funnel_data[funnel_data['Stage'] != 'Lost']
            
            fig = go.Figure()
            fig.add_trace(go.Bar(
                y=funnel_data['Stage'],
                x=funnel_data['Count'],
                orientation='h',
                marker=dict(
                    color=funnel_data['Count'],
                    colorscale='Purples',
                ),
                text=funnel_data['Count'],
                textposition='auto',
            ))
            fig.update_layout(height=400, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No pipeline data available")
    
    with col2:
        st.subheader("📈 Source Breakdown")
        if len(df) > 0:
            source_data = df['Lead Source'].value_counts().reset_index()
            source_data.columns = ['Source', 'Leads']
            
            fig = px.pie(source_data, values='Leads', names='Source',
                        hole=0.4,
                        color_discrete_sequence=['#667eea', '#764ba2', '#f093fb', '#4facfe'])
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No source data available")
    
    st.markdown("---")
    
    # Top campaigns
    st.subheader("🚀 Top Performing Campaigns")
    if len(df) > 0 and 'Campaign Name' in df.columns:
        campaign_data = df.groupby('Campaign Name').agg({
            'Lead ID': 'count'
        }).rename(columns={'Lead ID': 'Leads'}).reset_index()
        campaign_data = campaign_data.sort_values('Leads', ascending=False).head(5)
        
        for idx, row in campaign_data.iterrows():
            campaign_leads = df[df['Campaign Name'] == row['Campaign Name']]
            qualified = len(campaign_leads[campaign_leads['Current Stage'].isin(
                ['Qualified Lead', 'Discovery/Presentation', 'Opportunity', 'Negotiation', 'Contract Signed']
            )])
            won = len(campaign_leads[campaign_leads['Current Stage'] == 'Contract Signed'])
            
            with st.container():
                st.markdown(f"""
                **{row['Campaign Name']}**  
                {row['Leads']} leads · {qualified} qualified · {won} won · {qualified/row['Leads']*100:.0f}% qual rate
                """)
                st.progress(qualified / row['Leads'] if row['Leads'] > 0 else 0)
                st.markdown("---")
    else:
        st.info("No campaign data available")

def show_agent_dashboard(df):
    """Agent dashboard for call center"""
    st.markdown('<h1 class="main-header">👤 Agent Dashboard</h1>', unsafe_allow_html=True)
    
    # Agent selector
    if len(df) > 0 and 'Agent Assigned' in df.columns:
        agents = df[df['Agent Assigned'].notna() & (df['Agent Assigned'] != 'Unassigned')]['Agent Assigned'].unique()
    else:
        agents = []
    
    if len(agents) == 0:
        st.warning("No agents found with assigned leads.")
        return
    
    selected_agent = st.selectbox("Select Your Name:", sorted(agents))
    
    # Filter for selected agent
    agent_leads = df[df['Agent Assigned'] == selected_agent]
    
    # Stats
    total = len(agent_leads)
    qualified = len(agent_leads[agent_leads['Current Stage'].isin(
        ['Qualified Lead', 'Discovery/Presentation', 'Opportunity', 'Negotiation', 'Contract Signed']
    )])
    won = len(agent_leads[agent_leads['Current Stage'] == 'Contract Signed'])
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("📊 Total Leads", total)
    with col2:
        st.metric("✅ Qualified", qualified)
    with col3:
        st.metric("🎉 Won", won)
    with col4:
        st.metric("📈 Win Rate", f"{won/total*100:.1f}%" if total > 0 else "0%")
    
    st.markdown("---")
    
    # Today's follow-ups
    today = datetime.now().date()
    if 'Next Follow-up' in agent_leads.columns:
        urgent_leads = agent_leads[agent_leads['Next Follow-up'].dt.date == today]
    else:
        urgent_leads = pd.DataFrame()
    
    st.subheader(f"🔴 Today's Follow-ups ({len(urgent_leads)})")
    
    if len(urgent_leads) > 0:
        for idx, lead in urgent_leads.iterrows():
            with st.expander(f"🔴 {lead.get('First Name', 'N/A')} {lead.get('Last Name', 'N/A')} - {lead.get('Current Stage', 'N/A')}"):
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**📞 Phone:** {lead.get('Phone', 'N/A')}")
                    st.write(f"**📧 Email:** {lead.get('Email', 'N/A')}")
                with col2:
                    st.write(f"**💰 Budget:** {lead.get('Budget Range', 'N/A')}")
                    follow_up = lead.get('Next Follow-up')
                    follow_up_str = follow_up.strftime('%d/%m/%Y') if pd.notna(follow_up) else 'Not set'
                    st.write(f"**📅 Follow-up:** {follow_up_str}")
                
                notes = lead.get('Notes', 'No notes')
                st.write(f"**📝 Notes:** {notes if pd.notna(notes) else 'No notes'}")
    else:
        st.success("✨ No urgent follow-ups today! Great job!")
    
    st.markdown("---")
    
    # All leads
    st.subheader("📋 All My Leads")
    
    # Stage filter
    stages = ['All'] + sorted(agent_leads['Current Stage'].unique().tolist())
    stage_filter = st.selectbox("Filter by Stage:", stages)
    
    if stage_filter != 'All':
        filtered_leads = agent_leads[agent_leads['Current Stage'] == stage_filter]
    else:
        filtered_leads = agent_leads
    
    # Display leads
    if len(filtered_leads) > 0:
        for idx, lead in filtered_leads.iterrows():
            with st.expander(f"{lead.get('First Name', 'N/A')} {lead.get('Last Name', 'N/A')} - {lead.get('Current Stage', 'N/A')}"):
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Lead ID:** {lead.get('Lead ID', 'N/A')}")
                    st.write(f"**📞 Phone:** {lead.get('Phone', 'N/A')}")
                    st.write(f"**📧 Email:** {lead.get('Email', 'N/A')}")
                with col2:
                    st.write(f"**💰 Budget:** {lead.get('Budget Range', 'N/A')}")
                    follow_up = lead.get('Next Follow-up')
                    follow_up_str = follow_up.strftime('%d/%m/%Y') if pd.notna(follow_up) else 'Not set'
                    st.write(f"**📅 Next Follow-up:** {follow_up_str}")
                    st.write(f"**🎯 Lead Source:** {lead.get('Lead Source', 'N/A')}")
                
                notes = lead.get('Notes', 'No notes')
                st.write(f"**📝 Notes:** {notes if pd.notna(notes) else 'No notes'}")
    else:
        st.info("No leads match the selected filter")

if __name__ == "__main__":
    main()
