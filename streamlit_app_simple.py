import streamlit as st
import pandas as pd
import os
import json
from datetime import datetime
import time

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

    /* Main header */
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        text-align: center;
        margin-bottom: 0.5rem;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
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
        worksheet = sheet.worksheet("Metrics")

        # Get all values
        data = worksheet.get_all_records()
        df = pd.DataFrame(data)

        return df, datetime.now()
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame(), None

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

def main():
    # Header
    st.markdown('<h1 class="main-header">Joseph Mews Sales Dashboard</h1>', unsafe_allow_html=True)
    st.markdown('<p class="subtitle">Real-time Sales Funnel Metrics • GDPR Compliant</p>', unsafe_allow_html=True)

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

        df, last_update = load_metrics_from_sheets(client, spreadsheet_url)

    if df.empty:
        st.error("No data found. Check your Google Sheets and ensure 'Metrics' worksheet exists.")
        st.info("""
        **Expected Format:**

        Worksheet name: **Metrics**

        | Stage | Count |
        |-------|-------|
        | Total Leads | 150 |
        | Qualified Leads | 45 |
        | Viewings Scheduled | 30 |
        | Viewings Completed | 25 |
        | Offers Made | 15 |
        | Offers Accepted | 10 |
        | Closed Sales | 8 |
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

    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Qualified</div>
            <div class="metric-value">{metrics.get('Qualified Leads', 0)}</div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Offers</div>
            <div class="metric-value">{metrics.get('Offers Made', 0)}</div>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Closed</div>
            <div class="metric-value">{metrics.get('Closed Sales', 0)}</div>
        </div>
        """, unsafe_allow_html=True)

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

    # Conversion funnel section
    st.markdown("---")
    st.subheader("📈 Conversion Funnel")

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
