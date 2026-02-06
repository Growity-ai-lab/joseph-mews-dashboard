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

try:
    from anthropic import Anthropic
    AI_AVAILABLE = True
except ImportError:
    AI_AVAILABLE = False

# Page config
st.set_page_config(
    page_title="Joseph Mews Lead Funnel Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Initialize session state for dark mode
if 'dark_mode' not in st.session_state:
    st.session_state.dark_mode = False

# Theme colors
if st.session_state.dark_mode:
    bg_color = "#0e1117"
    card_bg = "rgba(255, 255, 255, 0.05)"
    text_color = "#fafafa"
    subtitle_color = "#a0a0a0"
    border_color = "rgba(255, 255, 255, 0.1)"
else:
    bg_color = "#ffffff"
    card_bg = "rgba(255, 255, 255, 0.9)"
    text_color = "#333333"
    subtitle_color = "#666666"
    border_color = "rgba(0, 0, 0, 0.1)"

# Custom CSS - Modern Enhanced Design
st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    /* Global Styles */
    * {{
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    }}

    /* Main container */
    .main {{
        background: {bg_color};
        color: {text_color};
        transition: all 0.3s ease;
    }}

    /* Hide sidebar completely */
    [data-testid="stSidebar"] {{
        display: none;
    }}

    /* Section spacing */
    hr {{
        margin: 1.5rem 0;
        opacity: 0.3;
    }}

    h1, h2, h3, h4 {{
        margin-top: 0.75rem;
        margin-bottom: 0.75rem;
    }}

    .stPlotlyChart {{
        margin-bottom: 0.5rem;
    }}

    /* Smooth transitions for all elements */
    .element-container, .stMarkdown, .stPlotlyChart {{
        animation: fadeInUp 0.6s ease-out;
    }}

    @keyframes fadeInUp {{
        from {{
            opacity: 0;
            transform: translateY(20px);
        }}
        to {{
            opacity: 1;
            transform: translateY(0);
        }}
    }}

    /* Counter animation */
    @keyframes countUp {{
        from {{
            opacity: 0;
            transform: scale(0.5);
        }}
        to {{
            opacity: 1;
            transform: scale(1);
        }}
    }}

    /* Logo styling with glassmorphism */
    .logo-container {{
        text-align: center;
        padding: 1.5rem 0 1rem 0;
        margin-bottom: 1.25rem;
        background: {card_bg};
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
        border: 1px solid {border_color};
        border-radius: 16px;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08);
    }}

    .logo-text {{
        font-size: 2.5rem;
        font-weight: 700;
        background: linear-gradient(135deg, #F4B23E 0%, #E09F3E 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        letter-spacing: 1.5px;
        margin: 0;
        line-height: 1;
        animation: fadeInUp 0.8s ease-out;
    }}

    /* Main header */
    .main-header {{
        font-size: 1.5rem;
        font-weight: 600;
        text-align: center;
        margin-bottom: 0.5rem;
        color: {text_color};
    }}

    .subtitle {{
        text-align: center;
        color: {subtitle_color};
        font-size: 1.1rem;
        margin-bottom: 2rem;
        font-weight: 400;
    }}

    /* Glassmorphism Metric cards */
    .metric-card {{
        background: {card_bg};
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        border: 1px solid {border_color};
        padding: 1.25rem;
        border-radius: 12px;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08);
        margin-bottom: 0.75rem;
        text-align: center;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        position: relative;
        overflow: hidden;
    }}

    .metric-card::before {{
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: linear-gradient(135deg, rgba(102, 126, 234, 0.1) 0%, rgba(118, 75, 162, 0.1) 100%);
        opacity: 0;
        transition: opacity 0.3s ease;
        z-index: 0;
    }}

    .metric-card:hover {{
        transform: translateY(-4px);
        box-shadow: 0 8px 24px rgba(102, 126, 234, 0.2);
        border-color: rgba(102, 126, 234, 0.3);
    }}

    .metric-card:hover::before {{
        opacity: 1;
    }}

    .metric-label {{
        font-size: 0.75rem;
        color: {subtitle_color};
        margin-bottom: 0.5rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 1px;
        position: relative;
        z-index: 1;
    }}

    .metric-value {{
        font-size: 2rem;
        font-weight: 700;
        color: {text_color};
        line-height: 1;
        position: relative;
        z-index: 1;
        animation: countUp 0.6s ease-out;
    }}

    /* Modern Flow chart styling */
    .flow-container {{
        display: flex;
        align-items: center;
        justify-content: center;
        margin: 1rem 0;
        flex-wrap: wrap;
        gap: 1rem;
        padding: 1.25rem;
        background: {card_bg};
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        border-radius: 16px;
        border: 1px solid {border_color};
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.06);
    }}

    .flow-metric {{
        background: linear-gradient(135deg, rgba(102, 126, 234, 0.9) 0%, rgba(118, 75, 162, 0.9) 100%);
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        padding: 1rem 1.5rem;
        border-radius: 12px;
        box-shadow: 0 4px 12px rgba(102, 126, 234, 0.25);
        border: 1px solid rgba(255, 255, 255, 0.2);
        text-align: center;
        min-width: 120px;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        position: relative;
        overflow: hidden;
    }}

    .flow-metric::before {{
        content: '';
        position: absolute;
        top: -50%;
        left: -50%;
        width: 200%;
        height: 200%;
        background: linear-gradient(45deg, transparent, rgba(255, 255, 255, 0.1), transparent);
        transform: rotate(45deg);
        transition: all 0.5s;
    }}

    .flow-metric:hover {{
        transform: translateY(-2px) scale(1.02);
        box-shadow: 0 8px 20px rgba(102, 126, 234, 0.4);
    }}

    .flow-metric:hover::before {{
        left: 100%;
    }}

    .flow-metric-label {{
        font-size: 0.7rem;
        color: rgba(255,255,255,0.9);
        margin-bottom: 0.5rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }}

    .flow-metric-value {{
        font-size: 1.75rem;
        font-weight: 700;
        color: white;
        text-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
        animation: countUp 0.6s ease-out;
    }}

    .flow-arrow {{
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 0.25rem;
        color: #667eea;
        font-weight: 700;
        animation: pulse 2s ease-in-out infinite;
    }}

    @keyframes pulse {{
        0%, 100% {{
            opacity: 1;
            transform: scale(1);
        }}
        50% {{
            opacity: 0.8;
            transform: scale(1.1);
        }}
    }}

    .flow-arrow-icon {{
        font-size: 1.5rem;
        filter: drop-shadow(0 2px 4px rgba(102, 126, 234, 0.3));
    }}

    .flow-arrow-rate {{
        font-size: 0.9rem;
        font-weight: 700;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }}

    /* Dark mode toggle */
    .dark-mode-toggle {{
        position: fixed;
        top: 20px;
        right: 20px;
        z-index: 1000;
        background: {card_bg};
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        border: 1px solid {border_color};
        border-radius: 50px;
        padding: 0.5rem 1rem;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
        transition: all 0.3s ease;
    }}

    .dark-mode-toggle:hover {{
        transform: scale(1.05);
        box-shadow: 0 6px 24px rgba(0, 0, 0, 0.15);
    }}

    /* Last updated */
    .last-update {{
        text-align: center;
        color: {subtitle_color};
        font-size: 0.9rem;
        margin-top: 3rem;
        padding: 1.5rem;
        background: {card_bg};
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        border-radius: 16px;
        border: 1px solid {border_color};
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.05);
    }}

    /* Footer */
    .footer {{
        text-align: center;
        color: {subtitle_color};
        font-size: 0.85rem;
        margin-top: 4rem;
        padding: 2rem;
        border-top: 1px solid {border_color};
        background: {card_bg};
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
    }}

    /* Loading animation */
    .stSpinner > div {{
        border-top-color: #667eea !important;
    }}

    /* Progress bars styling */
    .stProgress > div > div > div > div {{
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        border-radius: 10px;
        box-shadow: 0 2px 8px rgba(102, 126, 234, 0.3);
    }}

    /* Buttons */
    .stButton > button {{
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        padding: 0.75rem 2rem;
        border-radius: 12px;
        font-weight: 600;
        font-size: 0.95rem;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
    }}

    .stButton > button:hover {{
        transform: translateY(-2px);
        box-shadow: 0 8px 20px rgba(102, 126, 234, 0.4);
    }}

    /* Download button */
    .download-section {{
        text-align: center;
        margin: 2rem 0;
    }}

    .download-btn {{
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1rem 2.5rem;
        border-radius: 12px;
        text-decoration: none;
        display: inline-block;
        font-weight: 600;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        border: none;
        cursor: pointer;
        box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
    }}

    .download-btn:hover {{
        transform: translateY(-2px);
        box-shadow: 0 8px 20px rgba(102, 126, 234, 0.4);
    }}

    /* Metric comparison */
    .comparison-box {{
        background: {card_bg};
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        padding: 1.5rem;
        border-radius: 12px;
        margin: 1rem 0;
        border-left: 4px solid #667eea;
        border: 1px solid {border_color};
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.05);
    }}

    /* Expander styling */
    .streamlit-expanderHeader {{
        background: {card_bg};
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        border-radius: 12px;
        border: 1px solid {border_color};
        font-weight: 600;
    }}

    /* Plotly charts */
    .js-plotly-plot {{
        border-radius: 16px;
        overflow: hidden;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.05);
    }}

    /* AI Insight Cards */
    .ai-insight-card {{
        background: linear-gradient(135deg, rgba(102, 126, 234, 0.05) 0%, rgba(118, 75, 162, 0.05) 100%);
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        border: 1px solid {border_color};
        border-left: 4px solid #667eea;
        border-radius: 12px;
        padding: 1rem 1.5rem;
        margin: 1rem 0;
        box-shadow: 0 4px 16px rgba(102, 126, 234, 0.1);
        transition: all 0.3s ease;
    }}

    .ai-insight-card:hover {{
        transform: translateY(-2px);
        box-shadow: 0 6px 24px rgba(102, 126, 234, 0.15);
    }}

    .ai-insight-icon {{
        font-size: 1.5rem;
        margin-right: 0.75rem;
        vertical-align: middle;
    }}

    .ai-insight-text {{
        color: {text_color};
        line-height: 1.6;
        font-size: 0.95rem;
        display: inline;
    }}

    /* Scoring Cards */
    .temp-card {{
        background: linear-gradient(135deg, {{gradient_start}} 0%, {{gradient_end}} 100%);
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        border: 1px solid {border_color};
        border-radius: 12px;
        padding: 1rem;
        text-align: center;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08);
        transition: all 0.3s ease;
        animation: fadeInUp 0.6s ease-out;
    }}

    .temp-card:hover {{
        transform: translateY(-3px);
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
    }}

    .temp-icon {{
        font-size: 2rem;
        margin-bottom: 0.35rem;
        display: block;
    }}

    .temp-label {{
        font-size: 0.7rem;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        opacity: 0.9;
        margin-bottom: 0.35rem;
    }}

    .temp-value {{
        font-size: 1.75rem;
        font-weight: bold;
        margin-bottom: 0.2rem;
    }}

    .temp-percentage {{
        font-size: 0.85rem;
        opacity: 0.8;
    }}

    .temp-conversion {{
        font-size: 0.7rem;
        margin-top: 0.5rem;
        padding-top: 0.5rem;
        border-top: 1px solid rgba(255, 255, 255, 0.2);
        opacity: 0.9;
    }}
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

            # Convert numeric columns to numeric type
            numeric_columns = ['Total Leads', 'Qualified Leads', 'Viewings Scheduled',
                             'Viewings Completed', 'Offers Made', 'Offers Accepted',
                             'Closed Sales', 'Daily Budget']
            for col in numeric_columns:
                if col in daily_df.columns:
                    daily_df[col] = pd.to_numeric(daily_df[col], errors='coerce').fillna(0)
        except:
            # Daily sheet doesn't exist yet
            pass

        # Try to load WhatsApp metrics
        whatsapp_df = None
        try:
            whatsapp_worksheet = sheet.worksheet("WhatsApp")
            whatsapp_data = whatsapp_worksheet.get_all_records()
            whatsapp_df = pd.DataFrame(whatsapp_data)

            # Convert Date column to datetime
            if 'Date' in whatsapp_df.columns:
                whatsapp_df['Date'] = pd.to_datetime(whatsapp_df['Date'], errors='coerce')
                whatsapp_df = whatsapp_df.dropna(subset=['Date'])
                whatsapp_df = whatsapp_df.sort_values('Date')

            # Convert numeric columns to numeric type
            numeric_columns = ['Messages Answered', 'Positive', 'Negative',
                             'Relevant', 'Irrelevant', 'Scheduled Leads']
            for col in numeric_columns:
                if col in whatsapp_df.columns:
                    whatsapp_df[col] = pd.to_numeric(whatsapp_df[col], errors='coerce').fillna(0)
        except:
            # WhatsApp sheet doesn't exist yet
            pass

        return df, daily_df, whatsapp_df, datetime.now()
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame(), None, None, None

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

def calculate_lead_temperature(metrics):
    """Calculate lead distribution by temperature (Hot/Warm/Cold)"""
    total = metrics.get('Total Leads', 0)
    if total == 0:
        return {'hot': 0, 'warm': 0, 'cold': 0, 'hot_pct': 0, 'warm_pct': 0, 'cold_pct': 0}

    qualified = metrics.get('Qualified Leads', 0)
    viewings_scheduled = metrics.get('Viewings Scheduled', 0)
    viewings_completed = metrics.get('Viewings Completed', 0)
    offers_made = metrics.get('Offers Made', 0)
    offers_accepted = metrics.get('Offers Accepted', 0)

    # HOT Leads: Viewing completed + in offer stage
    # High intent, ready to close
    hot = min(viewings_completed, offers_made + offers_accepted)

    # WARM Leads: Qualified + viewing stage (not yet hot)
    # Interested and engaged, needs nurturing
    warm = max(0, min(qualified, viewings_scheduled + viewings_completed) - hot)

    # COLD Leads: Everything else
    # Early stage, needs qualification
    cold = max(0, total - hot - warm)

    # Calculate percentages
    hot_pct = (hot / total * 100) if total > 0 else 0
    warm_pct = (warm / total * 100) if total > 0 else 0
    cold_pct = (cold / total * 100) if total > 0 else 0

    # Calculate conversion rates
    hot_to_close = (metrics.get('Closed Sales', 0) / hot * 100) if hot > 0 else 0
    warm_to_hot = (hot / warm * 100) if warm > 0 else 0
    cold_to_warm = (warm / cold * 100) if cold > 0 else 0

    return {
        'hot': hot,
        'warm': warm,
        'cold': cold,
        'hot_pct': hot_pct,
        'warm_pct': warm_pct,
        'cold_pct': cold_pct,
        'hot_to_close': hot_to_close,
        'warm_to_hot': warm_to_hot,
        'cold_to_warm': cold_to_warm,
        'quality_score': (hot * 3 + warm * 2 + cold * 1) / total if total > 0 else 0
    }

def calculate_temperature_trend(daily_df):
    """Calculate temperature distribution over time from daily data"""
    if daily_df is None or daily_df.empty:
        return None

    trends = []
    for _, row in daily_df.iterrows():
        metrics = {
            'Total Leads': row.get('Total Leads', 0),
            'Qualified Leads': row.get('Qualified Leads', 0),
            'Viewings Scheduled': row.get('Viewings Scheduled', 0),
            'Viewings Completed': row.get('Viewings Completed', 0),
            'Offers Made': row.get('Offers Made', 0),
            'Offers Accepted': row.get('Offers Accepted', 0),
            'Closed Sales': row.get('Closed Sales', 0)
        }
        temp = calculate_lead_temperature(metrics)
        trends.append({
            'Date': row['Date'],
            'Hot': temp['hot'],
            'Warm': temp['warm'],
            'Cold': temp['cold'],
            'Quality Score': temp['quality_score']
        })

    return pd.DataFrame(trends)

def calculate_temperature_by_source(daily_df):
    """Calculate temperature distribution by lead source"""
    if daily_df is None or daily_df.empty or 'Source' not in daily_df.columns:
        return None

    sources = daily_df['Source'].unique()
    source_temps = []

    for source in sources:
        source_data = daily_df[daily_df['Source'] == source]

        # Sum all metrics for this source
        metrics = {
            'Total Leads': source_data.get('Total Leads', pd.Series([0])).sum(),
            'Qualified Leads': source_data.get('Qualified Leads', pd.Series([0])).sum(),
            'Viewings Scheduled': source_data.get('Viewings Scheduled', pd.Series([0])).sum(),
            'Viewings Completed': source_data.get('Viewings Completed', pd.Series([0])).sum(),
            'Offers Made': source_data.get('Offers Made', pd.Series([0])).sum(),
            'Offers Accepted': source_data.get('Offers Accepted', pd.Series([0])).sum(),
            'Closed Sales': source_data.get('Closed Sales', pd.Series([0])).sum()
        }

        temp = calculate_lead_temperature(metrics)
        source_temps.append({
            'Source': source,
            'Hot': temp['hot'],
            'Warm': temp['warm'],
            'Cold': temp['cold'],
            'Total': metrics['Total Leads'],
            'Quality Score': temp['quality_score']
        })

    return pd.DataFrame(source_temps).sort_values('Quality Score', ascending=False)

def generate_section_insight(section, metrics, daily_df=None, whatsapp_df=None):
    """Generate AI insight for a specific section"""
    if not AI_AVAILABLE:
        return None

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return None

    try:
        client = Anthropic(api_key=api_key)

        total = metrics.get('Total Leads', 0)
        if total == 0:
            return None

        # Section-specific prompts
        if section == "funnel":
            qualified = metrics.get('Qualified Leads', 0)
            closed = metrics.get('Closed Sales', 0)
            close_rate = (closed / total * 100)

            prompt = f"""Luxury real estate funnel: {total} leads → {qualified} qualified ({qualified/total*100:.1f}%) → {closed} closed ({close_rate:.1f}%).

ONE insight (2-3 sentences): What stands out about this funnel performance? Be specific and actionable."""

        elif section == "whatsapp" and whatsapp_df is not None and not whatsapp_df.empty:
            latest = whatsapp_df.iloc[-1]
            messages = int(latest.get('Messages Answered', 0))
            scheduled = int(latest.get('Scheduled Leads', 0))
            conv_rate = (scheduled / messages * 100) if messages > 0 else 0

            prompt = f"""WhatsApp: {messages} messages → {scheduled} scheduled leads ({conv_rate:.1f}% conversion).

ONE insight (2-3 sentences): How effective is WhatsApp? Be specific and actionable."""

        elif section == "bottleneck":
            bottlenecks = calculate_bottleneck(metrics)
            worst = bottlenecks[0] if bottlenecks else None

            if not worst:
                return None

            prompt = f"""Critical bottleneck: {worst['stage']} at {worst['rate']:.1f}% ({worst['drop_off']} lost leads).

ONE recommendation (2-3 sentences): How to fix this bottleneck? Be specific and actionable."""

        elif section == "trends" and daily_df is not None and not daily_df.empty:
            recent = daily_df.tail(7)
            trend_leads = recent['Total Leads'].values[-3:]  # last 3 days

            prompt = f"""7-day trend: Last 3 days had {trend_leads[0]}, {trend_leads[1]}, {trend_leads[2]} leads.

ONE observation (2-3 sentences): What pattern do you see? Be specific."""

        elif section == "temperature":
            temp_data = calculate_lead_temperature(metrics)
            hot = temp_data['hot']
            warm = temp_data['warm']
            cold = temp_data['cold']
            quality_score = temp_data['quality_score']

            prompt = f"""Lead temperature: {hot} hot ({temp_data['hot_pct']:.1f}%), {warm} warm ({temp_data['warm_pct']:.1f}%), {cold} cold ({temp_data['cold_pct']:.1f}%). Quality score: {quality_score:.1f}/3.0.

ONE insight (2-3 sentences): What does this temperature distribution tell us about lead quality? Be specific and actionable."""

        else:
            return None

        message = client.messages.create(
            model="claude-opus-4-20250514",
            max_tokens=150,
            messages=[{"role": "user", "content": prompt}]
        )

        return message.content[0].text.strip()

    except Exception as e:
        return None

def display_ai_insight(icon, text):
    """Display an AI insight card"""
    if text:
        st.markdown(f"""
        <div class="ai-insight-card">
            <span class="ai-insight-icon">{icon}</span>
            <span class="ai-insight-text">{text}</span>
        </div>
        """, unsafe_allow_html=True)

def main():
    # Dark Mode Toggle
    col_left, col_center, col_right = st.columns([4, 1, 1])
    with col_right:
        dark_mode_icon = "🌙" if not st.session_state.dark_mode else "☀️"
        dark_mode_text = "Dark" if not st.session_state.dark_mode else "Light"
        if st.button(f"{dark_mode_icon} {dark_mode_text}", key="dark_mode_toggle", use_container_width=True):
            st.session_state.dark_mode = not st.session_state.dark_mode
            st.rerun()

    # Logo and Header
    st.markdown('''
    <div class="logo-container">
        <h1 class="logo-text">Joseph Mews</h1>
    </div>
    ''', unsafe_allow_html=True)

    st.markdown('<h2 class="main-header">Lead Funnel Dashboard</h2>', unsafe_allow_html=True)

    # Subtitle with refresh button
    col1, col2, col3 = st.columns([2, 3, 2])
    with col1:
        st.markdown("")  # Empty space
    with col2:
        subcol1, subcol2 = st.columns([0.5, 6])
        with subcol1:
            if st.button("🔄", help="Refresh Data", key="refresh_btn"):
                st.cache_data.clear()
                st.rerun()
        with subcol2:
            st.markdown('<p class="subtitle" style="margin-top: 0.3rem;">Real-time Sales Funnel Metrics • GDPR Compliant</p>', unsafe_allow_html=True)
    with col3:
        st.markdown("")  # Empty space

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

        df, daily_df, whatsapp_df, last_update = load_metrics_from_sheets(client, spreadsheet_url)

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

    # Calculate conversion rates
    total = metrics.get('Total Leads', 0)
    qualified = metrics.get('Qualified Leads', 0)
    viewings_scheduled = metrics.get('Viewings Scheduled', 0)
    viewings_completed = metrics.get('Viewings Completed', 0)
    offers = metrics.get('Offers Made', 0)
    offers_accepted = metrics.get('Offers Accepted', 0)
    closed = metrics.get('Closed Sales', 0)

    lead_to_qual_rate = (qualified / total * 100) if total > 0 else 0
    qual_to_sched_rate = (viewings_scheduled / qualified * 100) if qualified > 0 else 0
    sched_to_comp_rate = (viewings_completed / viewings_scheduled * 100) if viewings_scheduled > 0 else 0
    comp_to_offer_rate = (offers / viewings_completed * 100) if viewings_completed > 0 else 0
    offer_to_accept_rate = (offers_accepted / offers * 100) if offers > 0 else 0
    accept_to_close_rate = (closed / offers_accepted * 100) if offers_accepted > 0 else 0
    overall_close_rate = (closed / total * 100) if total > 0 else 0

    # Initialize AI insights state
    if 'show_ai_insights' not in st.session_state:
        st.session_state.show_ai_insights = False
    if 'ai_insights_cache' not in st.session_state:
        st.session_state.ai_insights_cache = {}

    # AI Insights Toggle
    col1, col2 = st.columns([5, 1])
    with col1:
        st.markdown("")  # Empty space
    with col2:
        if st.button(
            "🤖 AI Insights" if not st.session_state.show_ai_insights else "🤖 Hide AI",
            key="ai_toggle",
            use_container_width=True
        ):
            st.session_state.show_ai_insights = not st.session_state.show_ai_insights
            # Generate insights when toggled on
            if st.session_state.show_ai_insights and not st.session_state.ai_insights_cache:
                with st.spinner('🧠 Generating AI insights...'):
                    st.session_state.ai_insights_cache['funnel'] = generate_section_insight('funnel', metrics)
                    st.session_state.ai_insights_cache['temperature'] = generate_section_insight('temperature', metrics)
                    st.session_state.ai_insights_cache['whatsapp'] = generate_section_insight('whatsapp', metrics, whatsapp_df=whatsapp_df)
                    st.session_state.ai_insights_cache['bottleneck'] = generate_section_insight('bottleneck', metrics)
                    st.session_state.ai_insights_cache['trends'] = generate_section_insight('trends', metrics, daily_df=daily_df)

    # Sales Funnel Flow Chart
    st.markdown("---")
    st.markdown("### 📊 Sales Funnel Flow")

    # Row 1: Total Leads → Qualified → Viewings Scheduled → Viewings Completed
    st.markdown(f"""
    <div class="flow-container">
        <div class="flow-metric">
            <div class="flow-metric-label">Total Leads</div>
            <div class="flow-metric-value">{total}</div>
        </div>
        <div class="flow-arrow">
            <div class="flow-arrow-icon">→</div>
            <div class="flow-arrow-rate">{lead_to_qual_rate:.1f}%</div>
        </div>
        <div class="flow-metric">
            <div class="flow-metric-label">Qualified</div>
            <div class="flow-metric-value">{qualified}</div>
        </div>
        <div class="flow-arrow">
            <div class="flow-arrow-icon">→</div>
            <div class="flow-arrow-rate">{qual_to_sched_rate:.1f}%</div>
        </div>
        <div class="flow-metric">
            <div class="flow-metric-label">Viewings Scheduled</div>
            <div class="flow-metric-value">{viewings_scheduled}</div>
        </div>
        <div class="flow-arrow">
            <div class="flow-arrow-icon">→</div>
            <div class="flow-arrow-rate">{sched_to_comp_rate:.1f}%</div>
        </div>
        <div class="flow-metric">
            <div class="flow-metric-label">Viewings Completed</div>
            <div class="flow-metric-value">{viewings_completed}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Row 2: Viewings Completed → Offers → Offers Accepted → Closed
    st.markdown(f"""
    <div class="flow-container">
        <div class="flow-metric">
            <div class="flow-metric-label">Viewings Completed</div>
            <div class="flow-metric-value">{viewings_completed}</div>
        </div>
        <div class="flow-arrow">
            <div class="flow-arrow-icon">→</div>
            <div class="flow-arrow-rate">{comp_to_offer_rate:.1f}%</div>
        </div>
        <div class="flow-metric">
            <div class="flow-metric-label">Offers</div>
            <div class="flow-metric-value">{offers}</div>
        </div>
        <div class="flow-arrow">
            <div class="flow-arrow-icon">→</div>
            <div class="flow-arrow-rate">{offer_to_accept_rate:.1f}%</div>
        </div>
        <div class="flow-metric">
            <div class="flow-metric-label">Offers Accepted</div>
            <div class="flow-metric-value">{offers_accepted}</div>
        </div>
        <div class="flow-arrow">
            <div class="flow-arrow-icon">→</div>
            <div class="flow-arrow-rate">{accept_to_close_rate:.1f}%</div>
        </div>
        <div class="flow-metric">
            <div class="flow-metric-label">Closed</div>
            <div class="flow-metric-value">{closed}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Overall Close Rate
    st.markdown(f"""
    <div style="text-align: center; margin: 2rem 0;">
        <div style="display: inline-block; background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);
                    padding: 1.5rem 3rem; border-radius: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.15);">
            <div style="font-size: 1rem; color: rgba(255,255,255,0.95); margin-bottom: 0.5rem; text-transform: uppercase; letter-spacing: 0.5px;">Overall Close Rate</div>
            <div style="font-size: 3rem; font-weight: bold; color: white;">{overall_close_rate:.1f}%</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # AI Insight for Funnel
    if st.session_state.show_ai_insights and 'funnel' in st.session_state.ai_insights_cache:
        display_ai_insight("💡", st.session_state.ai_insights_cache['funnel'])

    # Lead Scoring
    st.markdown("---")
    st.subheader("Lead Scoring")

    temp_data = calculate_lead_temperature(metrics)

    # Scoring Cards
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(f"""
        <div class="temp-card" style="background: linear-gradient(135deg, rgba(255, 68, 68, 0.15) 0%, rgba(255, 136, 0, 0.15) 100%);">
            <div class="temp-label" style="color: #ff4444;">Hot Leads</div>
            <div class="temp-value" style="color: #ff4444;">{temp_data['hot']}</div>
            <div class="temp-percentage" style="color: #ff6666;">{temp_data['hot_pct']:.1f}%</div>
            <div class="temp-conversion" style="color: #ff6666;">
                {temp_data['hot_to_close']:.1f}% → Close
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div class="temp-card" style="background: linear-gradient(135deg, rgba(255, 170, 0, 0.15) 0%, rgba(255, 196, 0, 0.15) 100%);">
            <div class="temp-label" style="color: #ffaa00;">Warm Leads</div>
            <div class="temp-value" style="color: #ffaa00;">{temp_data['warm']}</div>
            <div class="temp-percentage" style="color: #ffbb33;">{temp_data['warm_pct']:.1f}%</div>
            <div class="temp-conversion" style="color: #ffbb33;">
                {temp_data['warm_to_hot']:.1f}% → Hot
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
        <div class="temp-card" style="background: linear-gradient(135deg, rgba(79, 172, 254, 0.15) 0%, rgba(0, 242, 254, 0.15) 100%);">
            <div class="temp-label" style="color: #4facfe;">Cold Leads</div>
            <div class="temp-value" style="color: #4facfe;">{temp_data['cold']}</div>
            <div class="temp-percentage" style="color: #6fc0ff;">{temp_data['cold_pct']:.1f}%</div>
            <div class="temp-conversion" style="color: #6fc0ff;">
                {temp_data['cold_to_warm']:.1f}% → Warm
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        quality_color = "#43e97b" if temp_data['quality_score'] >= 2.0 else "#ffaa00" if temp_data['quality_score'] >= 1.5 else "#ff4444"
        st.markdown(f"""
        <div class="temp-card" style="background: linear-gradient(135deg, rgba(102, 126, 234, 0.15) 0%, rgba(118, 75, 162, 0.15) 100%);">
            <div class="temp-label" style="color: {quality_color};">Quality Score</div>
            <div class="temp-value" style="color: {quality_color};">{temp_data['quality_score']:.2f}</div>
            <div class="temp-percentage" style="color: {quality_color};">/ 3.00</div>
            <div class="temp-conversion" style="color: {quality_color};">
                {"Excellent" if temp_data['quality_score'] >= 2.0 else "Good" if temp_data['quality_score'] >= 1.5 else "Improving"}
            </div>
        </div>
        """, unsafe_allow_html=True)

    # Lead Distribution Chart
    st.markdown("### Lead Distribution")

    col_chart1, col_chart2 = st.columns(2)

    with col_chart1:
        fig_pie = go.Figure(data=[go.Pie(
            labels=['Hot', 'Warm', 'Cold'],
            values=[temp_data['hot'], temp_data['warm'], temp_data['cold']],
            hole=0.4,
            marker=dict(colors=['#ff4444', '#ffaa00', '#4facfe']),
            textinfo='label+percent',
            textposition='outside',
            hovertemplate='<b>%{label}</b><br>Count: %{value}<br>%{percent}<extra></extra>'
        )])

        fig_pie.update_layout(
            title="Distribution by Stage",
            height=280,
            showlegend=False,
            margin=dict(l=10, r=10, t=30, b=10)
        )

        st.plotly_chart(fig_pie, use_container_width=True)

    with col_chart2:
        fig_bar = go.Figure()

        fig_bar.add_trace(go.Bar(
            y=['Cold → Warm', 'Warm → Hot', 'Hot → Close'],
            x=[temp_data['cold_to_warm'], temp_data['warm_to_hot'], temp_data['hot_to_close']],
            orientation='h',
            marker=dict(
                color=[temp_data['cold_to_warm'], temp_data['warm_to_hot'], temp_data['hot_to_close']],
                colorscale=[[0, '#4facfe'], [0.5, '#ffaa00'], [1, '#ff4444']],
                showscale=False
            ),
            text=[f"{temp_data['cold_to_warm']:.1f}%", f"{temp_data['warm_to_hot']:.1f}%", f"{temp_data['hot_to_close']:.1f}%"],
            textposition='outside',
            hovertemplate='<b>%{y}</b><br>Conversion: %{x:.1f}%<extra></extra>'
        ))

        fig_bar.update_layout(
            title="Conversion Rates",
            height=280,
            showlegend=False,
            margin=dict(l=10, r=10, t=30, b=10),
            xaxis=dict(title="Rate (%)", range=[0, max(100, max(temp_data['cold_to_warm'], temp_data['warm_to_hot'], temp_data['hot_to_close']) * 1.2)])
        )

        st.plotly_chart(fig_bar, use_container_width=True)

    # AI Insight for Scoring
    if st.session_state.show_ai_insights and 'temperature' in st.session_state.ai_insights_cache:
        display_ai_insight("📊", st.session_state.ai_insights_cache['temperature'])

    # Lead Scoring Trends
    if daily_df is not None and not daily_df.empty:
        st.markdown("---")
        st.markdown("### Lead Scoring Trends")

        temp_trend_df = calculate_temperature_trend(daily_df)

        if temp_trend_df is not None and not temp_trend_df.empty:
            fig_trend = go.Figure()

            fig_trend.add_trace(go.Scatter(
                x=temp_trend_df['Date'],
                y=temp_trend_df['Hot'],
                mode='lines+markers',
                name='Hot',
                line=dict(color='#ff4444', width=2.5),
                marker=dict(size=6),
                fill='tonexty',
                fillcolor='rgba(255, 68, 68, 0.1)',
                hovertemplate='<b>Hot Leads</b><br>%{x}<br>Count: %{y}<extra></extra>'
            ))

            fig_trend.add_trace(go.Scatter(
                x=temp_trend_df['Date'],
                y=temp_trend_df['Warm'],
                mode='lines+markers',
                name='Warm',
                line=dict(color='#ffaa00', width=2.5),
                marker=dict(size=6),
                fill='tonexty',
                fillcolor='rgba(255, 170, 0, 0.1)',
                hovertemplate='<b>Warm Leads</b><br>%{x}<br>Count: %{y}<extra></extra>'
            ))

            fig_trend.add_trace(go.Scatter(
                x=temp_trend_df['Date'],
                y=temp_trend_df['Cold'],
                mode='lines+markers',
                name='Cold',
                line=dict(color='#4facfe', width=2.5),
                marker=dict(size=6),
                fill='tozeroy',
                fillcolor='rgba(79, 172, 254, 0.1)',
                hovertemplate='<b>Cold Leads</b><br>%{x}<br>Count: %{y}<extra></extra>'
            ))

            fig_trend.update_layout(
                height=300,
                margin=dict(l=10, r=10, t=10, b=40),
                xaxis_title="Date",
                yaxis_title="Leads",
                hovermode='x unified',
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=-0.25,
                    xanchor="center",
                    x=0.5
                )
            )

            st.plotly_chart(fig_trend, use_container_width=True)

            # Quality Score Trend
            st.markdown("#### Quality Score Trend")

            fig_quality = go.Figure()

            fig_quality.add_trace(go.Scatter(
                x=temp_trend_df['Date'],
                y=temp_trend_df['Quality Score'],
                mode='lines+markers',
                name='Quality Score',
                line=dict(color='#667eea', width=2.5),
                marker=dict(size=8, color=temp_trend_df['Quality Score'], colorscale='RdYlGn', cmin=0, cmax=3, showscale=False),
                fill='tozeroy',
                fillcolor='rgba(102, 126, 234, 0.2)',
                hovertemplate='<b>Quality Score</b><br>%{x}<br>%{y:.2f}/3.00<extra></extra>'
            ))

            fig_quality.add_hline(y=2.0, line_dash="dash", line_color="green", annotation_text="Excellent")
            fig_quality.add_hline(y=1.5, line_dash="dash", line_color="orange", annotation_text="Good")

            fig_quality.update_layout(
                height=250,
                margin=dict(l=10, r=10, t=10, b=10),
                xaxis_title="Date",
                yaxis_title="Score",
                yaxis=dict(range=[0, 3.2]),
                hovermode='x unified',
                showlegend=False
            )

            st.plotly_chart(fig_quality, use_container_width=True)

    # Lead Source Breakdown
    source_temp_df = calculate_temperature_by_source(daily_df)

    if source_temp_df is not None and not source_temp_df.empty:
        st.markdown("---")
        st.markdown("### Lead Scoring by Source")

        # Source cards
        cols = st.columns(min(len(source_temp_df), 4))

        for idx, (_, row) in enumerate(source_temp_df.iterrows()):
            if idx < 4:
                with cols[idx]:
                    source = row['Source']
                    quality = row['Quality Score']
                    quality_color = "#43e97b" if quality >= 2.0 else "#ffaa00" if quality >= 1.5 else "#ff4444"

                    st.markdown(f"""
                    <div class="temp-card" style="background: linear-gradient(135deg, rgba(102, 126, 234, 0.1) 0%, rgba(118, 75, 162, 0.1) 100%);">
                        <div class="temp-label" style="color: {quality_color}; font-size: 0.85rem; font-weight: bold; margin-bottom: 0.5rem;">
                            {source}
                        </div>
                        <div style="display: flex; justify-content: space-around; margin-bottom: 0.4rem;">
                            <div style="text-align: center;">
                                <div style="font-size: 0.65rem; opacity: 0.8;">Hot</div>
                                <div style="font-weight: bold; color: #ff4444; font-size: 1.1rem;">{int(row['Hot'])}</div>
                            </div>
                            <div style="text-align: center;">
                                <div style="font-size: 0.65rem; opacity: 0.8;">Warm</div>
                                <div style="font-weight: bold; color: #ffaa00; font-size: 1.1rem;">{int(row['Warm'])}</div>
                            </div>
                            <div style="text-align: center;">
                                <div style="font-size: 0.65rem; opacity: 0.8;">Cold</div>
                                <div style="font-weight: bold; color: #4facfe; font-size: 1.1rem;">{int(row['Cold'])}</div>
                            </div>
                        </div>
                        <div style="border-top: 1px solid rgba(255,255,255,0.2); padding-top: 0.4rem; margin-top: 0.4rem;">
                            <div style="font-size: 0.7rem; opacity: 0.8;">Total: {int(row['Total'])}</div>
                            <div style="font-size: 1rem; font-weight: bold; color: {quality_color}; margin-top: 0.2rem;">
                                {quality:.2f}/3.00
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

        # Source comparison chart
        st.markdown("#### Source Comparison")

        fig_source = go.Figure()

        fig_source.add_trace(go.Bar(
            name='Hot',
            x=source_temp_df['Source'],
            y=source_temp_df['Hot'],
            marker_color='#ff4444',
            hovertemplate='<b>%{x}</b><br>Hot: %{y}<extra></extra>'
        ))

        fig_source.add_trace(go.Bar(
            name='Warm',
            x=source_temp_df['Source'],
            y=source_temp_df['Warm'],
            marker_color='#ffaa00',
            hovertemplate='<b>%{x}</b><br>Warm: %{y}<extra></extra>'
        ))

        fig_source.add_trace(go.Bar(
            name='Cold',
            x=source_temp_df['Source'],
            y=source_temp_df['Cold'],
            marker_color='#4facfe',
            hovertemplate='<b>%{x}</b><br>Cold: %{y}<extra></extra>'
        ))

        fig_source.update_layout(
            barmode='stack',
            height=300,
            margin=dict(l=10, r=10, t=10, b=40),
            xaxis_title="Source",
            yaxis_title="Leads",
            hovermode='x unified',
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=-0.25,
                xanchor="center",
                x=0.5
            )
        )

        st.plotly_chart(fig_source, use_container_width=True)

    elif daily_df is not None and not daily_df.empty:
        st.info("**Add Source Tracking:** Add a 'Source' column to your Daily worksheet to track lead quality by platform (Google Ads, Facebook, Instagram, Organic, etc.)")

    # Visual Funnel Chart
    if show_funnel:
        st.markdown("---")
        st.subheader("Sales Funnel Visualization")

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

    # WhatsApp Metrics
    if whatsapp_df is not None and not whatsapp_df.empty:
        st.markdown("---")
        st.subheader("WhatsApp Metrics")

        # Get latest day's data
        latest_whatsapp = whatsapp_df.iloc[-1]

        # Calculate conversion rates
        messages_answered = latest_whatsapp.get('Messages Answered', 0)
        relevant = latest_whatsapp.get('Relevant', 0)
        positive = latest_whatsapp.get('Positive', 0)
        scheduled = latest_whatsapp.get('Scheduled Leads', 0)

        # Conversion rates
        answered_to_relevant = (relevant / messages_answered * 100) if messages_answered > 0 else 0
        relevant_to_positive = (positive / relevant * 100) if relevant > 0 else 0
        positive_to_scheduled = (scheduled / positive * 100) if positive > 0 else 0
        overall_conversion = (scheduled / messages_answered * 100) if messages_answered > 0 else 0

        # WhatsApp Flow Chart
        st.markdown("### 📊 WhatsApp Conversion Flow")

        st.markdown(f"""
        <div class="flow-container">
            <div class="flow-metric">
                <div class="flow-metric-label">Messages Answered</div>
                <div class="flow-metric-value">{int(messages_answered)}</div>
            </div>
            <div class="flow-arrow">
                <div class="flow-arrow-icon">→</div>
                <div class="flow-arrow-rate">{answered_to_relevant:.1f}%</div>
            </div>
            <div class="flow-metric">
                <div class="flow-metric-label">Relevant</div>
                <div class="flow-metric-value">{int(relevant)}</div>
            </div>
            <div class="flow-arrow">
                <div class="flow-arrow-icon">→</div>
                <div class="flow-arrow-rate">{relevant_to_positive:.1f}%</div>
            </div>
            <div class="flow-metric">
                <div class="flow-metric-label">Positive</div>
                <div class="flow-metric-value">{int(positive)}</div>
            </div>
            <div class="flow-arrow">
                <div class="flow-arrow-icon">→</div>
                <div class="flow-arrow-rate">{positive_to_scheduled:.1f}%</div>
            </div>
            <div class="flow-metric">
                <div class="flow-metric-label">Scheduled Leads</div>
                <div class="flow-metric-value">{int(scheduled)}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Overall Conversion Rate
        st.markdown(f"""
        <div style="text-align: center; margin: 2rem 0;">
            <div style="display: inline-block; background: linear-gradient(135deg, #25D366 0%, #128C7E 100%);
                        padding: 1.5rem 3rem; border-radius: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.15);">
                <div style="font-size: 1rem; color: rgba(255,255,255,0.95); margin-bottom: 0.5rem; text-transform: uppercase; letter-spacing: 0.5px;">Overall Conversion Rate</div>
                <div style="font-size: 3rem; font-weight: bold; color: white;">{overall_conversion:.1f}%</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Summary cards in columns
        st.markdown("---")
        st.markdown("#### 📈 Daily Summary")

        col1, col2, col3, col4, col5, col6 = st.columns(6)

        with col1:
            st.markdown("""
            <div style="background: linear-gradient(135deg, #25D366 0%, #128C7E 100%);
                        padding: 1.5rem; border-radius: 12px; text-align: center; box-shadow: 0 4px 15px rgba(0,0,0,0.15);">
                <div style="font-size: 0.85rem; color: rgba(255,255,255,0.9); margin-bottom: 0.5rem; text-transform: uppercase;">
                    Answered
                </div>
                <div style="font-size: 2rem; font-weight: bold; color: white;">
                    {}
                </div>
            </div>
            """.format(int(messages_answered)), unsafe_allow_html=True)

        with col2:
            st.markdown("""
            <div style="background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);
                        padding: 1.5rem; border-radius: 12px; text-align: center; box-shadow: 0 4px 15px rgba(0,0,0,0.15);">
                <div style="font-size: 0.85rem; color: rgba(255,255,255,0.9); margin-bottom: 0.5rem; text-transform: uppercase;">
                    Positive
                </div>
                <div style="font-size: 2rem; font-weight: bold; color: white;">
                    {}
                </div>
            </div>
            """.format(int(positive)), unsafe_allow_html=True)

        with col3:
            st.markdown("""
            <div style="background: linear-gradient(135deg, #ff6b6b 0%, #ee5a6f 100%);
                        padding: 1.5rem; border-radius: 12px; text-align: center; box-shadow: 0 4px 15px rgba(0,0,0,0.15);">
                <div style="font-size: 0.85rem; color: rgba(255,255,255,0.9); margin-bottom: 0.5rem; text-transform: uppercase;">
                    Negative
                </div>
                <div style="font-size: 2rem; font-weight: bold; color: white;">
                    {}
                </div>
            </div>
            """.format(int(latest_whatsapp.get('Negative', 0))), unsafe_allow_html=True)

        with col4:
            st.markdown("""
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        padding: 1.5rem; border-radius: 12px; text-align: center; box-shadow: 0 4px 15px rgba(0,0,0,0.15);">
                <div style="font-size: 0.85rem; color: rgba(255,255,255,0.9); margin-bottom: 0.5rem; text-transform: uppercase;">
                    Relevant
                </div>
                <div style="font-size: 2rem; font-weight: bold; color: white;">
                    {}
                </div>
            </div>
            """.format(int(relevant)), unsafe_allow_html=True)

        with col5:
            st.markdown("""
            <div style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
                        padding: 1.5rem; border-radius: 12px; text-align: center; box-shadow: 0 4px 15px rgba(0,0,0,0.15);">
                <div style="font-size: 0.85rem; color: rgba(255,255,255,0.9); margin-bottom: 0.5rem; text-transform: uppercase;">
                    Irrelevant
                </div>
                <div style="font-size: 2rem; font-weight: bold; color: white;">
                    {}
                </div>
            </div>
            """.format(int(latest_whatsapp.get('Irrelevant', 0))), unsafe_allow_html=True)

        with col6:
            st.markdown("""
            <div style="background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
                        padding: 1.5rem; border-radius: 12px; text-align: center; box-shadow: 0 4px 15px rgba(0,0,0,0.15);">
                <div style="font-size: 0.85rem; color: rgba(255,255,255,0.9); margin-bottom: 0.5rem; text-transform: uppercase;">
                    Scheduled
                </div>
                <div style="font-size: 2rem; font-weight: bold; color: white;">
                    {}
                </div>
            </div>
            """.format(int(scheduled)), unsafe_allow_html=True)

        # Daily trends for WhatsApp
        st.markdown("---")
        st.markdown("#### 📊 WhatsApp Daily Trends")

        col1, col2 = st.columns(2)

        with col1:
            # Messages Answered trend
            fig = go.Figure()

            fig.add_trace(go.Scatter(
                x=whatsapp_df['Date'],
                y=whatsapp_df.get('Messages Answered', [0] * len(whatsapp_df)),
                mode='lines+markers',
                name='Messages Answered',
                line=dict(color='#25D366', width=3),
                marker=dict(size=8),
                fill='tozeroy',
                fillcolor='rgba(37, 211, 102, 0.1)'
            ))

            fig.update_layout(
                title="Messages Answered",
                height=300,
                margin=dict(l=20, r=20, t=40, b=20),
                xaxis_title="Date",
                yaxis_title="Messages",
                hovermode='x unified',
                showlegend=False
            )

            st.plotly_chart(fig, use_container_width=True)

        with col2:
            # Positive vs Negative
            fig = go.Figure()

            fig.add_trace(go.Bar(
                x=whatsapp_df['Date'],
                y=whatsapp_df.get('Positive', [0] * len(whatsapp_df)),
                name='Positive',
                marker=dict(color='#43e97b')
            ))

            fig.add_trace(go.Bar(
                x=whatsapp_df['Date'],
                y=whatsapp_df.get('Negative', [0] * len(whatsapp_df)),
                name='Negative',
                marker=dict(color='#ff6b6b')
            ))

            fig.update_layout(
                title="Positive vs Negative",
                height=300,
                margin=dict(l=20, r=20, t=40, b=20),
                xaxis_title="Date",
                yaxis_title="Messages",
                hovermode='x unified',
                barmode='group'
            )

            st.plotly_chart(fig, use_container_width=True)

        # Relevant vs Irrelevant & Scheduled Leads
        col1, col2 = st.columns(2)

        with col1:
            # Relevant vs Irrelevant
            fig = go.Figure()

            fig.add_trace(go.Bar(
                x=whatsapp_df['Date'],
                y=whatsapp_df.get('Relevant', [0] * len(whatsapp_df)),
                name='Relevant',
                marker=dict(color='#667eea')
            ))

            fig.add_trace(go.Bar(
                x=whatsapp_df['Date'],
                y=whatsapp_df.get('Irrelevant', [0] * len(whatsapp_df)),
                name='Irrelevant',
                marker=dict(color='#f093fb')
            ))

            fig.update_layout(
                title="Relevant vs Irrelevant",
                height=300,
                margin=dict(l=20, r=20, t=40, b=20),
                xaxis_title="Date",
                yaxis_title="Messages",
                hovermode='x unified',
                barmode='group'
            )

            st.plotly_chart(fig, use_container_width=True)

        with col2:
            # Scheduled Leads
            fig = go.Figure()

            fig.add_trace(go.Scatter(
                x=whatsapp_df['Date'],
                y=whatsapp_df.get('Scheduled Leads', [0] * len(whatsapp_df)),
                mode='lines+markers',
                name='Scheduled Leads',
                line=dict(color='#4facfe', width=3),
                marker=dict(size=8),
                fill='tozeroy',
                fillcolor='rgba(79, 172, 254, 0.1)'
            ))

            fig.update_layout(
                title="Scheduled Leads",
                height=300,
                margin=dict(l=20, r=20, t=40, b=20),
                xaxis_title="Date",
                yaxis_title="Leads",
                hovermode='x unified',
                showlegend=False
            )

            st.plotly_chart(fig, use_container_width=True)

        # AI Insight for WhatsApp
        if st.session_state.show_ai_insights and 'whatsapp' in st.session_state.ai_insights_cache:
            display_ai_insight("💬", st.session_state.ai_insights_cache['whatsapp'])

    # Daily Trends
    if show_trends and daily_df is not None and not daily_df.empty:
        st.markdown("---")
        st.subheader("Daily Lead Trends")

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

            # AI Insight for Trends
            if st.session_state.show_ai_insights and 'trends' in st.session_state.ai_insights_cache:
                display_ai_insight("📈", st.session_state.ai_insights_cache['trends'])
        else:
            st.warning("No data available for selected date range")

    elif show_trends:
        st.info("💡 **Add Daily Tracking:** Create a 'Daily' worksheet in your Google Sheets to see trends over time!")

    # Bottleneck Analysis
    if show_bottleneck and total > 0:
        st.markdown("---")
        st.subheader("Bottleneck Analysis")

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

        # AI Insight for Bottleneck
        if st.session_state.show_ai_insights and 'bottleneck' in st.session_state.ai_insights_cache:
            display_ai_insight("🔴", st.session_state.ai_insights_cache['bottleneck'])

    # Projections & Forecasting
    if show_projections and total > 0:
        st.markdown("---")
        st.subheader("Projections & Forecasting")

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
            <small>Use 🔄 button or Rerun from menu to refresh</small>
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

if __name__ == "__main__":
    main()
