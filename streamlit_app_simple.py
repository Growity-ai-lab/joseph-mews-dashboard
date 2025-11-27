import streamlit as st
import pandas as pd
import os
import json
from datetime import datetime
import time
import plotly.graph_objects as go
import plotly.express as px

try:
    import gspread
    from google.oauth2.service_account import Credentials
    GOOGLE_SHEETS_AVAILABLE = True
except ImportError:
    GOOGLE_SHEETS_AVAILABLE = False

# Page config
st.set_page_config(
    page_title="Joseph Mews - Sales Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Auto-refresh every 30 seconds
st_autorefresh = st.empty()
with st_autorefresh:
    time.sleep(0.1)

# Custom CSS - Enhanced design
st.markdown("""
<style>
    /* Hide sidebar completely */
    [data-testid="stSidebar"] {
        display: none;
    }

    /* Logo styling */
    .logo-container {
        text-align: center;
        padding: 2rem 0 1rem 0;
        margin-bottom: 1rem;
    }

    .logo-text {
        font-size: 4.5rem;
        font-weight: bold;
        color: #F4B23E;
        text-shadow: 2px 2px 4px rgba(244, 178, 62, 0.3);
        letter-spacing: 2px;
        font-family: 'Georgia', serif;
        margin: 0;
        line-height: 1;
    }

    /* Main header */
    .main-header {
        font-size: 2rem;
        font-weight: 600;
        text-align: center;
        margin-bottom: 0.5rem;
        color: #333;
    }

    .subtitle {
        text-align: center;
        color: #666;
        font-size: 1.1rem;
        margin-bottom: 2rem;
    }

    /* Metric cards */
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 15px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.15);
        margin-bottom: 1.5rem;
        text-align: center;
        transition: transform 0.2s;
    }

    .metric-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 6px 20px rgba(0,0,0,0.2);
    }

    .metric-label {
        font-size: 1rem;
        color: rgba(255,255,255,0.9);
        margin-bottom: 0.8rem;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 1px;
    }

    .metric-value {
        font-size: 3.5rem;
        font-weight: bold;
        color: white;
        line-height: 1;
    }

    /* Conversion rate cards */
    .conversion-card {
        background: white;
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        border-left: 4px solid #667eea;
    }

    /* Last updated */
    .last-update {
        text-align: center;
        color: #888;
        font-size: 0.9rem;
        margin-top: 2rem;
        padding: 1rem;
        background: #f8f9fa;
        border-radius: 8px;
    }

    /* Footer */
    .footer {
        text-align: center;
        color: #999;
        font-size: 0.8rem;
        margin-top: 3rem;
        padding: 1rem;
        border-top: 1px solid #eee;
    }

    /* Loading animation */
    .stSpinner > div {
        border-top-color: #667eea !important;
    }

    /* Progress bars styling */
    .stProgress > div > div > div > div {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
    }

    /* Download button */
    .download-section {
        text-align: center;
        margin: 2rem 0;
    }

    .download-btn {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 0.8rem 2rem;
        border-radius: 8px;
        text-decoration: none;
        display: inline-block;
        font-weight: 600;
        transition: transform 0.2s;
        border: none;
        cursor: pointer;
    }

    .download-btn:hover {
        transform: scale(1.05);
    }

    /* Metric comparison */
    .comparison-box {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
        border-left: 3px solid #667eea;
    }

    /* Animation for metrics */
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(20px); }
        to { opacity: 1; transform: translateY(0); }
    }

    .metric-card {
        animation: fadeIn 0.5s ease-out;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_resource
def get_google_sheets_client():
    """Initialize Google Sheets client with credentials"""
    if not GOOGLE_SHEETS_AVAILABLE:
        return None

    credentials_dict = None

    try:
        # Try environment variables first
        if os.getenv("GCP_SERVICE_ACCOUNT"):
            credentials_dict = json.loads(os.getenv("GCP_SERVICE_ACCOUNT"))
        elif os.getenv("GCP_SERVICE_ACCOUNT_PROJECT_ID"):
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
        else:
            try:
                if "gcp_service_account" in st.secrets:
                    credentials_dict = st.secrets["gcp_service_account"]
            except:
                pass

        if not credentials_dict:
            return None

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

@st.cache_data(ttl=30)  # Refresh every 30 seconds
def load_metrics_from_sheets(_client, spreadsheet_url):
    """Load metrics from Google Sheets - NO PERSONAL DATA"""
    try:
        sheet = _client.open_by_url(spreadsheet_url)

        # Load current metrics
        worksheet = sheet.worksheet("Metrics")
        data = worksheet.get_all_records()
        df = pd.DataFrame(data)

        # Try to load daily data for trends
        daily_df = None
        try:
            daily_worksheet = sheet.worksheet("Daily")
            daily_data = daily_worksheet.get_all_records()
            daily_df = pd.DataFrame(daily_data)

            # Convert Date column to datetime
            if 'Date' in daily_df.columns:
                daily_df['Date'] = pd.to_datetime(daily_df['Date'], errors='coerce')
                daily_df = daily_df.dropna(subset=['Date'])
                daily_df = daily_df.sort_values('Date')
        except:
            # Daily sheet doesn't exist yet
            pass

        return df, daily_df, datetime.now()
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame(), None, None

def calculate_metrics(df):
    """Calculate sales funnel metrics"""
    if df.empty or 'Stage' not in df.columns or 'Count' not in df.columns:
        return {
            'Total Leads': 0,
            'Qualified Leads': 0,
            'Viewings Scheduled': 0,
            'Viewings Completed': 0,
            'Offers Made': 0,
            'Offers Accepted': 0,
            'Closed Sales': 0
        }

    metrics = {}
    for _, row in df.iterrows():
        stage = row['Stage']
        count = row['Count']
        metrics[stage] = int(count)

    return metrics

def calculate_bottleneck(metrics):
    """Identify the biggest bottleneck in the funnel"""
    conversion_stages = [
        ('Lead → Qualified', metrics.get('Total Leads', 0), metrics.get('Qualified Leads', 0)),
        ('Qualified → Viewing', metrics.get('Qualified Leads', 0), metrics.get('Viewings Completed', 0)),
        ('Viewing → Offer', metrics.get('Viewings Completed', 0), metrics.get('Offers Made', 0)),
        ('Offer → Accepted', metrics.get('Offers Made', 0), metrics.get('Offers Accepted', 0)),
        ('Accepted → Closed', metrics.get('Offers Accepted', 0), metrics.get('Closed Sales', 0)),
    ]

    bottlenecks = []
    for stage_name, from_count, to_count in conversion_stages:
        if from_count > 0:
            conversion_rate = (to_count / from_count) * 100
            drop_off = from_count - to_count
            bottlenecks.append({
                'stage': stage_name,
                'rate': conversion_rate,
                'drop_off': drop_off,
                'from': from_count,
                'to': to_count
            })

    # Sort by conversion rate (lowest = biggest bottleneck)
    bottlenecks.sort(key=lambda x: x['rate'])
    return bottlenecks

def calculate_projections(metrics):
    """Calculate projected outcomes based on current conversion rates"""
    total = metrics.get('Total Leads', 0)
    if total == 0:
        return {}

    # Current rates
    qual_rate = metrics.get('Qualified Leads', 0) / total
    viewing_rate = metrics.get('Viewings Completed', 0) / total
    offer_rate = metrics.get('Offers Made', 0) / total
    close_rate = metrics.get('Closed Sales', 0) / total

    # Projections for next 100 leads
    projection_input = 100

    projections = {
        'input_leads': projection_input,
        'projected_qualified': int(projection_input * qual_rate),
        'projected_viewings': int(projection_input * viewing_rate),
        'projected_offers': int(projection_input * offer_rate),
        'projected_closed': int(projection_input * close_rate),
        'current_close_rate': close_rate * 100
    }

    # What if scenarios
    projections['if_qual_improves_10'] = int(projection_input * min(qual_rate * 1.1, 1.0) * close_rate / qual_rate) if qual_rate > 0 else 0
    projections['if_viewing_improves_10'] = int(projection_input * close_rate / viewing_rate * min(viewing_rate * 1.1, 1.0)) if viewing_rate > 0 else 0

    return projections

def main():
    # Logo and Header
    st.markdown('''
    <div class="logo-container">
        <h1 class="logo-text">Joseph Mews</h1>
    </div>
    ''', unsafe_allow_html=True)

    st.markdown('<h2 class="main-header">Sales Dashboard</h2>', unsafe_allow_html=True)
    st.markdown('<p class="subtitle">Real-time Sales Funnel Metrics • GDPR Compliant</p>', unsafe_allow_html=True)

    # Filters in an expander
    with st.expander("⚙️ Dashboard Settings", expanded=False):
        col1, col2, col3 = st.columns(3)

        with col1:
            show_funnel = st.checkbox("Show Funnel Chart", value=True)
            show_trends = st.checkbox("Show Daily Trends", value=True)

        with col2:
            show_projections = st.checkbox("Show Projections", value=True)
            show_bottleneck = st.checkbox("Show Bottleneck Analysis", value=True)

        with col3:
            show_targets = st.checkbox("Show Performance Targets", value=True)
            show_pipeline = st.checkbox("Show Pipeline Health", value=True)

    # Get Google Sheets URL from environment variable
    spreadsheet_url = os.getenv("GOOGLE_SHEETS_URL")

    if not spreadsheet_url:
        st.error("⚠️ Configuration Error")
        st.info("""
        **Google Sheets URL not configured.**

        Please add `GOOGLE_SHEETS_URL` environment variable in Render:
        1. Go to Render Dashboard
        2. Select your service
        3. Environment → Add Environment Variable
        4. Key: `GOOGLE_SHEETS_URL`
        5. Value: Your Google Sheets URL
        """)
        return

    if not GOOGLE_SHEETS_AVAILABLE:
        st.error("Google Sheets integration not available.")
        return

    # Load data with spinner
    with st.spinner('Loading latest data...'):
        client = get_google_sheets_client()
        if not client:
            st.error("Could not connect to Google Sheets. Please check credentials.")
            return

        df, daily_df, last_update = load_metrics_from_sheets(client, spreadsheet_url)

    if df.empty:
        st.error("No data found. Check your Google Sheets and ensure 'Metrics' worksheet exists.")
        st.info("""
        **Expected Format:**

        **Worksheet 1: Metrics** (Total numbers)
        | Stage | Count |
        |-------|-------|
        | Total Leads | 150 |
        | Qualified Leads | 45 |
        | Viewings Scheduled | 30 |
        | Viewings Completed | 25 |
        | Offers Made | 15 |
        | Offers Accepted | 10 |
        | Closed Sales | 8 |

        **Worksheet 2: Daily** (Optional - for trends)
        | Date | Total Leads | Qualified Leads | Viewings Completed | Offers Made | Offers Accepted | Closed Sales |
        |------|-------------|-----------------|-----------------------|-------------|-----------------|--------------|
        | 2024-01-01 | 10 | 3 | 2 | 1 | 1 | 1 |
        | 2024-01-02 | 15 | 5 | 3 | 2 | 1 | 1 |
        """)
        return

    # Calculate metrics
    metrics = calculate_metrics(df)

    # Display metrics in 4 columns for better layout
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Total Leads</div>
            <div class="metric-value">{metrics.get('Total Leads', 0)}</div>
        </div>
        """, unsafe_allow_html=True)

        # Drill-down detail
        with st.expander("📊 View Details"):
            total = metrics.get('Total Leads', 0)
            qualified = metrics.get('Qualified Leads', 0)
            st.write(f"**Qualified Rate:** {(qualified/total*100):.1f}%" if total > 0 else "No data")
            st.write(f"**Not Qualified:** {total - qualified}" if total > 0 else "No data")

    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Qualified</div>
            <div class="metric-value">{metrics.get('Qualified Leads', 0)}</div>
        </div>
        """, unsafe_allow_html=True)

        # Drill-down detail
        with st.expander("📊 View Details"):
            qualified = metrics.get('Qualified Leads', 0)
            viewings = metrics.get('Viewings Completed', 0)
            st.write(f"**To Viewing Rate:** {(viewings/qualified*100):.1f}%" if qualified > 0 else "No data")
            st.write(f"**Pending Viewings:** {qualified - viewings}" if qualified > 0 else "No data")

    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Offers</div>
            <div class="metric-value">{metrics.get('Offers Made', 0)}</div>
        </div>
        """, unsafe_allow_html=True)

        # Drill-down detail
        with st.expander("📊 View Details"):
            offers = metrics.get('Offers Made', 0)
            accepted = metrics.get('Offers Accepted', 0)
            st.write(f"**Acceptance Rate:** {(accepted/offers*100):.1f}%" if offers > 0 else "No data")
            st.write(f"**Pending Offers:** {offers - accepted}" if offers > 0 else "No data")

    with col4:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Closed</div>
            <div class="metric-value">{metrics.get('Closed Sales', 0)}</div>
        </div>
        """, unsafe_allow_html=True)

        # Drill-down detail
        with st.expander("📊 View Details"):
            total = metrics.get('Total Leads', 0)
            closed = metrics.get('Closed Sales', 0)
            close_rate = (closed / total * 100) if total > 0 else 0
            st.write(f"**Overall Close Rate:** {close_rate:.1f}%")
            st.write(f"**Average Value:** N/A (add to sheets)")
            st.write(f"**Total Pipeline:** {total - closed} active")

    # Second row
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Viewings Scheduled</div>
            <div class="metric-value">{metrics.get('Viewings Scheduled', 0)}</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Viewings Completed</div>
            <div class="metric-value">{metrics.get('Viewings Completed', 0)}</div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Offers Accepted</div>
            <div class="metric-value">{metrics.get('Offers Accepted', 0)}</div>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        # Conversion rate
        total = metrics.get('Total Leads', 0)
        close_rate = (metrics.get('Closed Sales', 0) / total * 100) if total > 0 else 0
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Close Rate</div>
            <div class="metric-value">{close_rate:.1f}%</div>
        </div>
        """, unsafe_allow_html=True)

    # Visual Funnel Chart
    if show_funnel:
        st.markdown("---")
        st.subheader("📊 Sales Funnel Visualization")

    total = metrics.get('Total Leads', 0)
    if total > 0 and show_funnel:
        # Create funnel data
        funnel_data = {
            'Stage': [
                'Total Leads',
                'Qualified Leads',
                'Viewings Completed',
                'Offers Made',
                'Offers Accepted',
                'Closed Sales'
            ],
            'Count': [
                metrics.get('Total Leads', 0),
                metrics.get('Qualified Leads', 0),
                metrics.get('Viewings Completed', 0),
                metrics.get('Offers Made', 0),
                metrics.get('Offers Accepted', 0),
                metrics.get('Closed Sales', 0)
            ]
        }

        # Create two columns for funnel and progress bars
        col_funnel, col_progress = st.columns([3, 2])

        with col_funnel:
            # Create Plotly funnel chart
            fig = go.Figure(go.Funnel(
                y=funnel_data['Stage'],
                x=funnel_data['Count'],
                textposition="inside",
                textinfo="value+percent initial",
                marker={
                    "color": ["#667eea", "#764ba2", "#f093fb", "#4facfe", "#00f2fe", "#43e97b"],
                    "line": {"width": 2, "color": "white"}
                },
                connector={"line": {"color": "#667eea", "dash": "dot", "width": 3}}
            ))

            fig.update_layout(
                height=500,
                margin=dict(l=20, r=20, t=20, b=20),
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(size=14, color='#333')
            )

            st.plotly_chart(fig, use_container_width=True)

        with col_progress:
            st.markdown("#### Stage Conversion Rates")

            # Progress bars for each stage
            stages_progress = [
                ("Qualified", metrics.get('Qualified Leads', 0), total),
                ("Viewings", metrics.get('Viewings Completed', 0), total),
                ("Offers", metrics.get('Offers Made', 0), total),
                ("Accepted", metrics.get('Offers Accepted', 0), total),
                ("Closed", metrics.get('Closed Sales', 0), total),
            ]

            for stage_name, stage_count, total_count in stages_progress:
                percentage = (stage_count / total_count * 100) if total_count > 0 else 0
                st.markdown(f"**{stage_name}**: {stage_count} ({percentage:.1f}%)")
                st.progress(percentage / 100)
                st.markdown("")  # spacing

    # Daily Trends
    if show_trends and daily_df is not None and not daily_df.empty:
        st.markdown("---")
        st.subheader("📅 Daily Lead Trends")

        # Date range filter
        col1, col2, col3 = st.columns([2, 2, 3])

        with col1:
            min_date = daily_df['Date'].min().date()
            max_date = daily_df['Date'].max().date()
            start_date = st.date_input("From", value=min_date, min_value=min_date, max_value=max_date)

        with col2:
            end_date = st.date_input("To", value=max_date, min_value=min_date, max_value=max_date)

        with col3:
            st.markdown("##### Quick Filters")
            col_a, col_b, col_c = st.columns(3)
            with col_a:
                if st.button("Last 7 Days"):
                    start_date = max_date - pd.Timedelta(days=7)
            with col_b:
                if st.button("Last 30 Days"):
                    start_date = max_date - pd.Timedelta(days=30)
            with col_c:
                if st.button("All Time"):
                    start_date = min_date

        # Filter data by date range
        mask = (daily_df['Date'].dt.date >= start_date) & (daily_df['Date'].dt.date <= end_date)
        filtered_daily = daily_df[mask]

        if not filtered_daily.empty:
            # Daily totals line chart
            col1, col2 = st.columns(2)

            with col1:
                st.markdown("#### 📊 Daily Total Leads")

                fig = go.Figure()

                fig.add_trace(go.Scatter(
                    x=filtered_daily['Date'],
                    y=filtered_daily.get('Total Leads', [0] * len(filtered_daily)),
                    mode='lines+markers',
                    name='Total Leads',
                    line=dict(color='#667eea', width=3),
                    marker=dict(size=8),
                    fill='tozeroy',
                    fillcolor='rgba(102, 126, 234, 0.1)'
                ))

                fig.update_layout(
                    height=350,
                    margin=dict(l=20, r=20, t=20, b=20),
                    xaxis_title="Date",
                    yaxis_title="Leads",
                    hovermode='x unified',
                    showlegend=False
                )

                st.plotly_chart(fig, use_container_width=True)

                # Daily stats
                total_period = filtered_daily.get('Total Leads', pd.Series([0])).sum()
                avg_daily = filtered_daily.get('Total Leads', pd.Series([0])).mean()

                col_a, col_b = st.columns(2)
                with col_a:
                    st.metric("Total in Period", int(total_period))
                with col_b:
                    st.metric("Daily Average", f"{avg_daily:.1f}")

            with col2:
                st.markdown("#### 🎯 Daily Closed Sales")

                fig = go.Figure()

                fig.add_trace(go.Bar(
                    x=filtered_daily['Date'],
                    y=filtered_daily.get('Closed Sales', [0] * len(filtered_daily)),
                    name='Closed Sales',
                    marker=dict(
                        color=filtered_daily.get('Closed Sales', [0] * len(filtered_daily)),
                        colorscale='Greens',
                        line=dict(color='white', width=1)
                    )
                ))

                fig.update_layout(
                    height=350,
                    margin=dict(l=20, r=20, t=20, b=20),
                    xaxis_title="Date",
                    yaxis_title="Sales",
                    hovermode='x unified',
                    showlegend=False
                )

                st.plotly_chart(fig, use_container_width=True)

                # Sales stats
                total_sales = filtered_daily.get('Closed Sales', pd.Series([0])).sum()
                avg_sales = filtered_daily.get('Closed Sales', pd.Series([0])).mean()

                col_a, col_b = st.columns(2)
                with col_a:
                    st.metric("Total Sales", int(total_sales))
                with col_b:
                    st.metric("Daily Average", f"{avg_sales:.1f}")

            # Budget Analysis (if budget column exists)
            if 'Daily Budget' in filtered_daily.columns:
                st.markdown("---")
                st.markdown("#### 💰 Budget & Cost Analysis")

                col1, col2, col3 = st.columns(3)

                with col1:
                    st.markdown("##### 📊 Daily Budget vs Leads")

                    fig = go.Figure()

                    # Budget bars
                    fig.add_trace(go.Bar(
                        x=filtered_daily['Date'],
                        y=filtered_daily['Daily Budget'],
                        name='Daily Budget',
                        marker=dict(color='rgba(102, 126, 234, 0.6)'),
                        yaxis='y'
                    ))

                    # Leads line
                    fig.add_trace(go.Scatter(
                        x=filtered_daily['Date'],
                        y=filtered_daily.get('Total Leads', [0] * len(filtered_daily)),
                        name='Total Leads',
                        line=dict(color='#43e97b', width=3),
                        marker=dict(size=8),
                        yaxis='y2'
                    ))

                    fig.update_layout(
                        height=300,
                        margin=dict(l=20, r=20, t=20, b=20),
                        xaxis_title="Date",
                        yaxis=dict(title="Budget (£)", side='left'),
                        yaxis2=dict(title="Leads", side='right', overlaying='y'),
                        hovermode='x unified',
                        showlegend=True,
                        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                    )

                    st.plotly_chart(fig, use_container_width=True)

                with col2:
                    st.markdown("##### 💸 Cost Per Lead")

                    # Calculate cost per lead
                    filtered_daily['Cost Per Lead'] = filtered_daily.apply(
                        lambda row: row['Daily Budget'] / row['Total Leads'] if row.get('Total Leads', 0) > 0 else 0,
                        axis=1
                    )

                    fig = go.Figure()

                    fig.add_trace(go.Scatter(
                        x=filtered_daily['Date'],
                        y=filtered_daily['Cost Per Lead'],
                        mode='lines+markers',
                        name='Cost Per Lead',
                        line=dict(color='#f093fb', width=3),
                        marker=dict(size=8),
                        fill='tozeroy',
                        fillcolor='rgba(240, 147, 251, 0.1)'
                    ))

                    fig.update_layout(
                        height=300,
                        margin=dict(l=20, r=20, t=20, b=20),
                        xaxis_title="Date",
                        yaxis_title="Cost (£)",
                        hovermode='x unified',
                        showlegend=False
                    )

                    st.plotly_chart(fig, use_container_width=True)

                    # Average cost per lead
                    avg_cost = filtered_daily['Cost Per Lead'].mean()
                    st.metric("Avg Cost Per Lead", f"£{avg_cost:.2f}")

                with col3:
                    st.markdown("##### 📈 Budget Efficiency")

                    # Calculate efficiency metrics
                    total_budget = filtered_daily['Daily Budget'].sum()
                    total_leads_period = filtered_daily.get('Total Leads', pd.Series([0])).sum()
                    total_sales_period = filtered_daily.get('Closed Sales', pd.Series([0])).sum()

                    overall_cost_per_lead = total_budget / total_leads_period if total_leads_period > 0 else 0
                    cost_per_sale = total_budget / total_sales_period if total_sales_period > 0 else 0

                    st.metric("Total Budget", f"£{total_budget:,.0f}")
                    st.metric("Cost Per Lead", f"£{overall_cost_per_lead:.2f}")
                    st.metric("Cost Per Sale", f"£{cost_per_sale:.2f}")

                    # Efficiency score
                    if overall_cost_per_lead > 0:
                        efficiency = (1 / overall_cost_per_lead) * 100
                        st.metric("Efficiency Score", f"{efficiency:.1f}")

            # Multi-line funnel progression
            st.markdown("---")
            st.markdown("#### 📈 Funnel Progression Over Time")

            fig = go.Figure()

            metrics_to_plot = [
                ('Total Leads', '#667eea'),
                ('Qualified Leads', '#764ba2'),
                ('Viewings Completed', '#f093fb'),
                ('Offers Made', '#4facfe'),
                ('Closed Sales', '#43e97b')
            ]

            for metric_name, color in metrics_to_plot:
                if metric_name in filtered_daily.columns:
                    fig.add_trace(go.Scatter(
                        x=filtered_daily['Date'],
                        y=filtered_daily[metric_name],
                        mode='lines+markers',
                        name=metric_name,
                        line=dict(color=color, width=2),
                        marker=dict(size=6)
                    ))

            fig.update_layout(
                height=400,
                margin=dict(l=20, r=20, t=20, b=60),
                xaxis_title="Date",
                yaxis_title="Count",
                hovermode='x unified',
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=-0.3,
                    xanchor="center",
                    x=0.5
                )
            )

            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("No data available for selected date range")

    elif show_trends:
        st.info("💡 **Add Daily Tracking:** Create a 'Daily' worksheet in your Google Sheets to see trends over time!")

    # Bottleneck Analysis
    if show_bottleneck and total > 0:
        st.markdown("---")
        st.subheader("🔴 Bottleneck Analysis")

        bottlenecks = calculate_bottleneck(metrics)

        if bottlenecks:
            # Highlight the biggest bottleneck
            worst = bottlenecks[0]

            col1, col2 = st.columns([2, 3])

            with col1:
                st.error(f"### 🚨 Critical Bottleneck")
                st.markdown(f"""
                **{worst['stage']}**
                - Conversion Rate: **{worst['rate']:.1f}%**
                - Drop-off: **{worst['drop_off']}** leads
                - From: {worst['from']} → To: {worst['to']}
                """)

                # Recommendation
                if worst['rate'] < 50:
                    st.warning("⚠️ **Action Needed:** Focus improvement efforts here for maximum impact!")

            with col2:
                st.markdown("#### All Conversion Stages")

                # Create bar chart for all stages
                bottleneck_df = pd.DataFrame(bottlenecks)

                fig = px.bar(
                    bottleneck_df,
                    x='rate',
                    y='stage',
                    orientation='h',
                    color='rate',
                    color_continuous_scale=['#ff4444', '#ffaa00', '#44ff44'],
                    labels={'rate': 'Conversion Rate (%)', 'stage': 'Stage'},
                    text='rate'
                )

                fig.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
                fig.update_layout(
                    height=300,
                    showlegend=False,
                    margin=dict(l=20, r=20, t=20, b=20)
                )

                st.plotly_chart(fig, use_container_width=True)

    # Projections & Forecasting
    if show_projections and total > 0:
        st.markdown("---")
        st.subheader("🔮 Projections & Forecasting")

        projections = calculate_projections(metrics)

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("#### 📊 Next 100 Leads Projection")
            st.markdown("*Based on current conversion rates*")

            st.metric("Expected Qualified", projections['projected_qualified'])
            st.metric("Expected Viewings", projections['projected_viewings'])
            st.metric("Expected Offers", projections['projected_offers'])
            st.metric("Expected Closed Sales", projections['projected_closed'],
                     delta=f"{projections['current_close_rate']:.1f}% close rate")

        with col2:
            st.markdown("#### 🎯 What-If Scenarios")
            st.markdown("*Impact of 10% improvement*")

            current_closed = projections['projected_closed']

            st.info(f"**If Qualification improves by 10%:**")
            st.write(f"Closed Sales: {projections['if_qual_improves_10']} (+{projections['if_qual_improves_10'] - current_closed})")

            st.info(f"**If Viewing Conversion improves by 10%:**")
            st.write(f"Closed Sales: {projections['if_viewing_improves_10']} (+{projections['if_viewing_improves_10'] - current_closed})")

            st.success("💡 **Tip:** Focus on the bottleneck stage for maximum ROI")

    # Conversion funnel section
    st.markdown("---")
    st.subheader("📈 Conversion Rates")

    total = metrics.get('Total Leads', 0)
    if total > 0:
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            qual_rate = (metrics.get('Qualified Leads', 0) / total * 100) if total > 0 else 0
            delta = f"+{qual_rate:.1f}%" if qual_rate > 0 else "0%"
            st.metric(
                "Lead → Qualified",
                f"{qual_rate:.1f}%",
                delta=None,
                help=f"{metrics.get('Qualified Leads', 0)} out of {total} leads"
            )

        with col2:
            viewing_rate = (metrics.get('Viewings Completed', 0) / total * 100) if total > 0 else 0
            st.metric(
                "Lead → Viewing",
                f"{viewing_rate:.1f}%",
                delta=None,
                help=f"{metrics.get('Viewings Completed', 0)} out of {total} leads"
            )

        with col3:
            offer_rate = (metrics.get('Offers Made', 0) / total * 100) if total > 0 else 0
            st.metric(
                "Lead → Offer",
                f"{offer_rate:.1f}%",
                delta=None,
                help=f"{metrics.get('Offers Made', 0)} out of {total} leads"
            )

        with col4:
            st.metric(
                "Lead → Closed",
                f"{close_rate:.1f}%",
                delta=None,
                help=f"{metrics.get('Closed Sales', 0)} out of {total} leads"
            )

    # Pipeline Health & Performance Targets
    if (show_pipeline or show_targets) and total > 0:
        st.markdown("---")
        col1, col2 = st.columns(2)

        if show_pipeline:
            with col1:
                st.markdown("#### 📊 Pipeline Health")
                pipeline_stages = [
                    ("In Viewings", metrics.get('Viewings Scheduled', 0) + metrics.get('Viewings Completed', 0)),
                    ("In Negotiation", metrics.get('Offers Made', 0) + metrics.get('Offers Accepted', 0)),
                    ("Ready to Close", metrics.get('Offers Accepted', 0))
                ]

                for stage, count in pipeline_stages:
                    st.metric(stage, count)

        if show_targets:
            with col2:
                st.markdown("#### 🎯 Performance Targets")

                # Calculate rates
                qualified_rate = (metrics.get('Qualified Leads', 0) / total * 100) if total > 0 else 0
                viewing_to_offer = (metrics.get('Offers Made', 0) / metrics.get('Viewings Completed', 1) * 100) if metrics.get('Viewings Completed', 0) > 0 else 0
                close_rate = (metrics.get('Closed Sales', 0) / total * 100) if total > 0 else 0

                # Calculate if targets are being met (example thresholds)
                targets = {
                    "Qualification Rate": (qualified_rate, 30, "%"),
                    "Close Rate": (close_rate, 5, "%"),
                    "Viewing Conversion": (viewing_to_offer, 40, "%")
                }

                for metric_name, (value, target, unit) in targets.items():
                    if value >= target:
                        st.success(f"✅ {metric_name}: {value:.1f}{unit} (Target: {target}{unit})")
                    else:
                        st.error(f"❌ {metric_name}: {value:.1f}{unit} (Target: {target}{unit})")

    # Last updated timestamp
    if last_update:
        st.markdown(f"""
        <div class="last-update">
            🕐 Last updated: {last_update.strftime('%B %d, %Y at %H:%M:%S')}
            <br>
            <small>Auto-refreshes every 30 seconds</small>
        </div>
        """, unsafe_allow_html=True)

    # Footer
    st.markdown("""
    <div class="footer">
        🔒 GDPR Compliant Dashboard • No Personal Data Stored or Displayed
        <br>
        Joseph Mews © 2024 • All Rights Reserved
    </div>
    """, unsafe_allow_html=True)

    # Auto-refresh mechanism
    time.sleep(30)
    st.rerun()

if __name__ == "__main__":
    main()
