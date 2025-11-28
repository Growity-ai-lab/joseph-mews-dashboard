# Joseph Mews Dashboard

Modern sales funnel tracking dashboard built with Streamlit, integrated with Google Sheets for real-time lead management.

## Features

### 🎯 Admin Dashboard
- Complete sales funnel analytics
- Performance metrics and KPIs
- Lead source analysis
- Agent performance leaderboard
- Recent lead activity tracking

### 🏘️ Client Dashboard
- Campaign performance overview
- Lead pipeline visualization
- Source breakdown and analytics
- Top performing campaigns
- Real-time conversion metrics

### 👤 Agent Dashboard
- Personal lead management
- Today's follow-up reminders
- Individual performance tracking
- Lead filtering by stage
- Contact information quick access

## Quick Start

### Prerequisites
- Python 3.11 or higher
- Google Cloud Platform account (for Google Sheets integration)
- Google Sheets with "Lead Tracker" worksheet

### Installation

1. **Clone the repository**
```bash
git clone <repository-url>
cd joseph-mews-dashboard
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Set up Google Cloud credentials**
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select existing one
   - Enable Google Sheets API and Google Drive API
   - Create a Service Account
   - Download the JSON key file

4. **Configure Streamlit secrets**
   - Create `.streamlit` folder in the project root
   - Create `secrets.toml` file inside `.streamlit` folder
   - Copy content from `secrets.toml.example`
   - Fill in your Google Service Account credentials

```bash
mkdir -p .streamlit
cp secrets.toml.example .streamlit/secrets.toml
# Edit .streamlit/secrets.toml with your credentials
```

5. **Run the application**
```bash
streamlit run streamlit_app_v2.py
```

The dashboard will open in your browser at `http://localhost:8501`

## Google Sheets Setup

### Required Sheet Structure

Your Google Sheets document must have a worksheet named "Lead Tracker" with these columns:

- **Lead ID**: Unique identifier
- **First Name**: Lead's first name
- **Last Name**: Lead's last name
- **Email**: Contact email
- **Phone**: Contact phone number
- **Lead Source**: Where the lead came from
- **Campaign Name**: Associated campaign
- **Current Stage**: Current position in sales funnel
  - Lead Collected
  - Contact Attempted
  - Contact Made
  - Qualified Lead
  - Discovery/Presentation
  - Opportunity
  - Negotiation
  - Contract Signed
  - Lost
- **Agent Assigned**: Sales agent handling the lead
- **Budget Range**: Lead's budget information
- **Date Collected**: When lead was acquired
- **Last Contact Date**: Last interaction date
- **Next Follow-up**: Scheduled follow-up date
- **Notes**: Additional notes and comments

### Sharing Permissions

1. Open your Google Sheet
2. Click "Share" button
3. Add your Service Account email (from secrets.toml)
4. Grant "Editor" permissions

## Usage

1. **Launch the dashboard**
   ```bash
   streamlit run streamlit_app_v2.py
   ```

2. **Enter Google Sheets URL**
   - Copy your Google Sheets URL from browser
   - Paste it in the sidebar
   - Dashboard will load automatically

3. **Select Dashboard View**
   - **Admin Dashboard**: Full analytics and team overview
   - **Client Dashboard**: Campaign performance for stakeholders
   - **Agent Dashboard**: Personal lead management for agents

4. **Refresh Data**
   - Click "🔄 Refresh Data" button in sidebar
   - Dashboard auto-refreshes every 5 minutes

## Deployment

### Streamlit Community Cloud

1. Push your code to GitHub
2. Go to [Streamlit Community Cloud](https://streamlit.io/cloud)
3. Connect your GitHub repository
4. Add secrets in the dashboard settings
5. Deploy!

### Environment Variables

For production deployment, ensure these secrets are configured:
- `gcp_service_account` - Full Google Service Account credentials

## Troubleshooting

### Common Issues

**"Error connecting to Google Sheets"**
- Verify Service Account credentials in secrets.toml
- Check if APIs are enabled in Google Cloud Console
- Ensure Service Account has access to the spreadsheet

**"No data found"**
- Confirm worksheet is named "Lead Tracker"
- Check Google Sheets URL is correct
- Verify spreadsheet has data

**"No agents found"**
- Ensure "Agent Assigned" column has values
- Check for "Unassigned" entries (these are filtered out)

## Tech Stack

- **Streamlit**: Web application framework
- **Pandas**: Data manipulation
- **Plotly**: Interactive visualizations
- **gspread**: Google Sheets integration
- **Google Auth**: Authentication handling

## File Structure

```
joseph-mews-dashboard/
├── streamlit_app_v2.py      # Main application (recommended)
├── streamlit_app.py          # Alternative version
├── requirements.txt          # Python dependencies
├── runtime.txt              # Python version
├── secrets.toml.example     # Secrets template
├── .streamlit/
│   └── secrets.toml         # Your credentials (not in git)
└── README.md                # This file
```

## Development

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run with auto-reload
streamlit run streamlit_app_v2.py --server.runOnSave true
```

### Features Roadmap

- [ ] Export reports to PDF
- [ ] Email notifications for follow-ups
- [ ] Advanced filtering and search
- [ ] Custom date range selection
- [ ] Lead scoring system
- [ ] Integration with CRM systems

## Support

For issues or questions:
1. Check the Troubleshooting section
2. Review Google Sheets setup requirements
3. Verify all dependencies are installed

## License

© 2024 Joseph Mews Dashboard. All rights reserved.
