import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import gspread
from google.oauth2.service_account import Credentials
import json

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
    .metric-card {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        border-left: 4px solid #667eea;
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

# Load Google Sheets credentials from Streamlit secrets
@st.cache_resource
def get_google_sheets_client():
    """Initialize Google Sheets client with credentials"""
    try:
        # Try to get credentials from Streamlit secrets
        credentials_dict = st.secrets["gcp_service_account"]
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
        st.info("Please configure Google Sheets credentials in Streamlit secrets.")
        return None

@st.cache_data(ttl=300)  # Cache for 5 minutes
def load_data_from_sheets(_client, spreadsheet_url):
    """Load data from Google Sheets"""
    try:
        # Open the spreadsheet
        sheet = _client.open_by_url(spreadsheet_url)
        
        # Get Lead Tracker worksheet
        worksheet = sheet.worksheet("Lead Tracker")
        
        # Get all values
        data = worksheet.get_all_records()
        
        # Convert to DataFrame
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
        count = len(df[df['Current Stage'] == stage])
        metrics.append({'Stage': stage, 'Count': count})
    
    return pd.DataFrame(metrics)

def get_summary_stats(df):
    """Get summary statistics"""
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
    sources = df.groupby('Lead Source').agg({
        'Lead ID': 'count',
    }).rename(columns={'Lead ID': 'Total'}).reset_index()
    
    qualified_stages = ['Qualified Lead', 'Discovery/Presentation', 'Opportunity', 
                       'Negotiation', 'Contract Signed']
    
    for idx, row in sources.iterrows():
        source_df = df[df['Lead Source'] == row['Lead Source']]
        qualified = len(source_df[source_df['Current Stage'].isin(qualified_stages)])
        won = len(source_df[source_df['Current Stage'] == 'Contract Signed'])
        
        sources.at[idx, 'Qualified'] = qualified
        sources.at[idx, 'Won'] = won
        sources.at[idx, 'Qual Rate'] = (qualified / row['Total'] * 100) if row['Total'] > 0 else 0
        sources.at[idx, 'Win Rate'] = (won / row['Total'] * 100) if row['Total'] > 0 else 0
    
    return sources

def get_agent_performance(df):
    """Get performance by agent"""
    # Filter out unassigned
    agent_df = df[df['Agent Assigned'].notna() & (df['Agent Assigned'] != 'Unassigned')]
    
    agents = agent_df.groupby('Agent Assigned').agg({
        'Lead ID': 'count',
    }).rename(columns={'Lead ID': 'Total'}).reset_index()
    
    qualified_stages = ['Qualified Lead', 'Discovery/Presentation', 'Opportunity', 
                       'Negotiation', 'Contract Signed']
    
    for idx, row in agents.iterrows():
        agent_leads = agent_df[agent_df['Agent Assigned'] == row['Agent Assigned']]
        qualified = len(agent_leads[agent_leads['Current Stage'].isin(qualified_stages)])
        won = len(agent_leads[agent_leads['Current Stage'] == 'Contract Signed'])
        
        agents.at[idx, 'Qualified'] = qualified
        agents.at[idx, 'Won'] = won
        agents.at[idx, 'Qual Rate'] = (qualified / row['Total'] * 100) if row['Total'] > 0 else 0
        agents.at[idx, 'Win Rate'] = (won / row['Total'] * 100) if row['Total'] > 0 else 0
    
    return agents.sort_values('Won', ascending=False)

# Main app
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
    
    client = get_google_sheets_client()
    if not client:
        return
    
    df = load_data_from_sheets(client, spreadsheet_url)
    
    if df.empty:
        st.error("No data found. Please check your Google Sheets URL.")
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
        fig = px.funnel(funnel_data, x='Count', y='Stage', 
                       color_discrete_sequence=['#667eea'])
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("📈 Stage Distribution")
        stage_data = df['Current Stage'].value_counts().reset_index()
        stage_data.columns = ['Stage', 'Count']
        fig = px.pie(stage_data, values='Count', names='Stage',
                    color_discrete_sequence=px.colors.sequential.Purples_r)
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("---")
    
    # Tables row 2
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🎯 Source Performance")
        source_perf = get_source_performance(df)
        
        # Color code the qual rate
        def color_rate(val):
            if val > 50:
                return 'background-color: #d4edda'
            elif val > 30:
                return 'background-color: #fff3cd'
            else:
                return 'background-color: #f8d7da'
        
        styled_df = source_perf.style.applymap(color_rate, subset=['Qual Rate'])
        st.dataframe(styled_df, use_container_width=True)
    
    with col2:
        st.subheader("👥 Agent Leaderboard")
        agent_perf = get_agent_performance(df)
        styled_df = agent_perf.style.applymap(color_rate, subset=['Win Rate'])
        st.dataframe(styled_df, use_container_width=True)
    
    # Recent activity
    st.markdown("---")
    st.subheader("📋 Recent Leads")
    recent_leads = df.sort_values('Date Collected', ascending=False).head(10)
    st.dataframe(
        recent_leads[['Lead ID', 'First Name', 'Last Name', 'Current Stage', 
                     'Agent Assigned', 'Date Collected']],
        use_container_width=True
    )

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
    
    with col2:
        st.subheader("📈 Source Breakdown")
        source_data = df['Lead Source'].value_counts().reset_index()
        source_data.columns = ['Source', 'Leads']
        
        fig = px.pie(source_data, values='Leads', names='Source',
                    hole=0.4,
                    color_discrete_sequence=['#667eea', '#764ba2', '#f093fb', '#4facfe'])
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("---")
    
    # Top campaigns
    st.subheader("🚀 Top Performing Campaigns")
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

def show_agent_dashboard(df):
    """Agent dashboard for call center"""
    st.markdown('<h1 class="main-header">👤 Agent Dashboard</h1>', unsafe_allow_html=True)
    
    # Agent selector
    agents = df[df['Agent Assigned'].notna() & (df['Agent Assigned'] != 'Unassigned')]['Agent Assigned'].unique()
    
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
    urgent_leads = agent_leads[agent_leads['Next Follow-up'].dt.date == today]
    
    st.subheader(f"🔴 Today's Follow-ups ({len(urgent_leads)})")
    
    if len(urgent_leads) > 0:
        for idx, lead in urgent_leads.iterrows():
            with st.expander(f"🔴 {lead['First Name']} {lead['Last Name']} - {lead['Current Stage']}"):
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**📞 Phone:** {lead['Phone']}")
                    st.write(f"**📧 Email:** {lead['Email']}")
                with col2:
                    st.write(f"**💰 Budget:** {lead['Budget Range']}")
                    st.write(f"**📅 Follow-up:** {lead['Next Follow-up'].strftime('%d/%m/%Y') if pd.notna(lead['Next Follow-up']) else 'Not set'}")
                
                st.write(f"**📝 Notes:** {lead['Notes'] if pd.notna(lead['Notes']) else 'No notes'}")
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
    for idx, lead in filtered_leads.iterrows():
        with st.expander(f"{lead['First Name']} {lead['Last Name']} - {lead['Current Stage']}"):
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**Lead ID:** {lead['Lead ID']}")
                st.write(f"**📞 Phone:** {lead['Phone']}")
                st.write(f"**📧 Email:** {lead['Email']}")
            with col2:
                st.write(f"**💰 Budget:** {lead['Budget Range']}")
                st.write(f"**📅 Next Follow-up:** {lead['Next Follow-up'].strftime('%d/%m/%Y') if pd.notna(lead['Next Follow-up']) else 'Not set'}")
                st.write(f"**🎯 Lead Source:** {lead['Lead Source']}")
            
            st.write(f"**📝 Notes:** {lead['Notes'] if pd.notna(lead['Notes']) else 'No notes'}")

if __name__ == "__main__":
    main()
