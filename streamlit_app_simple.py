import streamlit as st
import pandas as pd
import os
import json

try:
    import gspread
    from google.oauth2.service_account import Credentials
    GOOGLE_SHEETS_AVAILABLE = True
except ImportError:
    GOOGLE_SHEETS_AVAILABLE = False

# Page config
st.set_page_config(
    page_title="Joseph Mews - Sales Metrics",
    page_icon="📊",
    layout="centered"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        text-align: center;
        margin-bottom: 2rem;
        color: #1f77b4;
    }
    .metric-container {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        margin-bottom: 1rem;
        border-left: 4px solid #1f77b4;
    }
    .metric-label {
        font-size: 0.9rem;
        color: #666;
        margin-bottom: 0.5rem;
    }
    .metric-value {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
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
        # Try environment variables first (for Render, Railway, etc.)
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
            st.error("Google Sheets credentials not found.")
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

@st.cache_data(ttl=300)
def load_metrics_from_sheets(_client, spreadsheet_url):
    """Load metrics from Google Sheets - NO PERSONAL DATA"""
    try:
        sheet = _client.open_by_url(spreadsheet_url)
        worksheet = sheet.worksheet("Metrics")

        # Get all values - expecting just stage counts
        data = worksheet.get_all_records()
        df = pd.DataFrame(data)

        return df
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame()

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
    st.markdown('<h1 class="main-header">📊 Joseph Mews Sales Metrics</h1>', unsafe_allow_html=True)

    # Sidebar for URL input
    with st.sidebar:
        st.title("⚙️ Configuration")
        spreadsheet_url = st.text_input(
            "Google Sheets URL",
            value=st.session_state.get('spreadsheet_url', ''),
            help="Paste your Google Sheets URL"
        )

        if spreadsheet_url:
            st.session_state['spreadsheet_url'] = spreadsheet_url

        if st.button("🔄 Refresh"):
            st.cache_data.clear()
            st.rerun()

        st.markdown("---")
        st.info("💡 Auto-refresh every 5 minutes")
        st.markdown("---")
        st.caption("🔒 GDPR Compliant - No personal data displayed")

    # Load data
    if not spreadsheet_url:
        st.warning("👈 Please enter your Google Sheets URL")
        st.info("""
        **Google Sheets Setup:**

        Create a worksheet named **"Metrics"** with these columns:

        | Stage | Count |
        |-------|-------|
        | Total Leads | 150 |
        | Qualified Leads | 45 |
        | Viewings Scheduled | 30 |
        | Viewings Completed | 25 |
        | Offers Made | 15 |
        | Offers Accepted | 10 |
        | Closed Sales | 8 |

        No personal data needed! Just numbers.
        """)
        return

    if not GOOGLE_SHEETS_AVAILABLE:
        st.error("Google Sheets integration not available.")
        return

    client = get_google_sheets_client()
    if not client:
        return

    df = load_metrics_from_sheets(client, spreadsheet_url)

    if df.empty:
        st.error("No data found. Check your Google Sheets URL and ensure 'Metrics' worksheet exists.")
        return

    # Calculate metrics
    metrics = calculate_metrics(df)

    # Display metrics
    col1, col2 = st.columns(2)

    with col1:
        st.markdown(f"""
        <div class="metric-container">
            <div class="metric-label">Total Leads</div>
            <div class="metric-value">{metrics.get('Total Leads', 0)}</div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown(f"""
        <div class="metric-container">
            <div class="metric-label">Viewings Scheduled</div>
            <div class="metric-value">{metrics.get('Viewings Scheduled', 0)}</div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown(f"""
        <div class="metric-container">
            <div class="metric-label">Offers Made</div>
            <div class="metric-value">{metrics.get('Offers Made', 0)}</div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown(f"""
        <div class="metric-container">
            <div class="metric-label">Closed Sales</div>
            <div class="metric-value">{metrics.get('Closed Sales', 0)}</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div class="metric-container">
            <div class="metric-label">Qualified Leads</div>
            <div class="metric-value">{metrics.get('Qualified Leads', 0)}</div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown(f"""
        <div class="metric-container">
            <div class="metric-label">Viewings Completed</div>
            <div class="metric-value">{metrics.get('Viewings Completed', 0)}</div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown(f"""
        <div class="metric-container">
            <div class="metric-label">Offers Accepted</div>
            <div class="metric-value">{metrics.get('Offers Accepted', 0)}</div>
        </div>
        """, unsafe_allow_html=True)

    # Conversion rates
    st.markdown("---")
    st.subheader("📈 Conversion Rates")

    total = metrics.get('Total Leads', 0)
    if total > 0:
        col1, col2, col3 = st.columns(3)

        with col1:
            qual_rate = (metrics.get('Qualified Leads', 0) / total * 100) if total > 0 else 0
            st.metric("Lead → Qualified", f"{qual_rate:.1f}%")

        with col2:
            viewing_rate = (metrics.get('Viewings Completed', 0) / total * 100) if total > 0 else 0
            st.metric("Lead → Viewing", f"{viewing_rate:.1f}%")

        with col3:
            close_rate = (metrics.get('Closed Sales', 0) / total * 100) if total > 0 else 0
            st.metric("Lead → Closed", f"{close_rate:.1f}%")

if __name__ == "__main__":
    main()
