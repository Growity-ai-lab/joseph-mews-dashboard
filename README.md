# Lead Funnel Dashboard

A Streamlit dashboard for lead-generation projects: funnel performance, lead scoring, channels,
trends, with Claude (Opus 5.5) built in. Data comes from Google Sheets; without a sheet
it runs on built-in demo data whose dates always end today, so it is ready for client demos.

It is white-label: the client name, colours, currency and targets come from `brand.json` or
environment variables.

## What's inside

| Tab | Contents |
|-----|----------|
| **Overview** | KPI row with change vs the previous period, funnel at a glance, priority actions |
| **Funnel** | Funnel chart, step conversion rates, biggest bottleneck with a playbook, targets |
| **Lead Scoring** | Hot/Warm/Cold split from the stage and the outcome noted in the last message, and what each group is made of (aggregate, no per-lead table) |
| **Channels** | WhatsApp conversion flow and conversation quality, performance by lead source |
| **Trends** | Daily leads and sales with 7-day averages, lead mix over time, spend and cost per lead |
| **Ask AI** | Chat with Claude about the figures on the dashboard |

A **reporting period** selector (last 7/30/90 days, custom range or all time) filters every tab, and
the header shows the exact dates covered.

### Claude features

All features use `claude-opus-5-5` with server-side fallback enabled (if a request is declined by a
safety classifier, the API retries it on Anthropic's recommended fallback model). They need
`ANTHROPIC_API_KEY`; without it the buttons are disabled and everything else works.

- **AI insights** – one request returns a short commentary for every tab plus the top three actions.
- **Ask AI** – questions about the current reporting period, answered from the dashboard data.

## Google Sheets format

Share the spreadsheet with the service account email. Provide at least one of `Metrics`, `Daily` or `Leads`:
without `Metrics` the funnel is derived from `Daily`, and without `Daily` from `Leads` (each lead counts for
every stage up to the one it has reached; `Lost` leads count only as leads).

**Metrics** – totals used for "All time"

| Stage | Count |
|-------|-------|
| Total Leads | 150 |
| Qualified Leads | 45 |
| Viewings Scheduled | 30 |
| Viewings Completed | 25 |
| Offers Made | 15 |
| Offers Accepted | 10 |
| Closed Sales | 8 |

**Daily** – enables date filtering and trends. `Source` and `Daily Budget` are optional; with `Source`
add one row per date and source.

| Date | Source | Total Leads | Qualified Leads | Viewings Scheduled | Viewings Completed | Offers Made | Offers Accepted | Closed Sales | Daily Budget |
|------|--------|-------------|-----------------|--------------------|--------------------|-------------|-----------------|--------------|--------------|
| 2026-10-11 | Google Ads | 9 | 3 | 2 | 2 | 1 | 0 | 0 | 220 |
| 2026-10-12 | Google Ads | 7 | 3 | 2 | 1 | 1 | 1 | 0 | 215 |

**WhatsApp** – optional

| Date | Messages Answered | Relevant | Irrelevant | Positive | Negative | Scheduled Leads |
|------|-------------------|----------|------------|----------|----------|-----------------|
| 2026-10-12 | 28 | 20 | 8 | 12 | 8 | 5 |

**Leads** – optional, enables per-lead scoring. Use pseudonymous IDs only (no names, emails or phone
numbers). Stage is one of: New, Contacted, Qualified, Viewing Scheduled, Viewing Completed, Offer Made,
Offer Accepted, Closed, Lost.

| Lead ID | Date | Source | Stage | Budget | Last Contact | Last Message |
|---------|------|--------|-------|--------|--------------|--------------|
| JM-1041 | 2026-10-02 | Google Ads | Viewing Completed | £2M–£3.5M | 2026-10-11 | Could we see it again on Saturday? |

## Configuration

| Variable | Purpose |
|----------|---------|
| `GOOGLE_SHEETS_URL` | Spreadsheet URL. If unset, the dashboard shows demo data |
| `GCP_SERVICE_ACCOUNT` | Service account JSON (or the split `GCP_SERVICE_ACCOUNT_*` variables, see `RENDER_SETUP.md`) |
| `ANTHROPIC_API_KEY` | Enables the Claude features |
| `CLAUDE_MODEL` | Optional model override (default `claude-opus-5-5`) |
| `DEMO_MODE` | `true` forces demo data even when a sheet is configured |
| `BRAND_NAME`, `BRAND_TAGLINE`, `BRAND_INDUSTRY`, `BRAND_PRIMARY_COLOR`, `BRAND_SECONDARY_COLOR`, `BRAND_ACCENT_COLOR`, `BRAND_LOGO_URL`, `BRAND_CURRENCY`, `BRAND_LEAD_ID_PREFIX` | White-label overrides |

For a client demo, either copy `brand.example.json` to `brand.json` and edit it, or set the `BRAND_*`
variables. Add `?demo=1` to the URL to show demo data on a live deployment.

### Lead scoring rules

Open leads are grouped from their `Stage` and the outcome noted in `Last Message` (matched ignoring case and
accents): **Hot** = stage Qualified or later, or a promised callback; **Warm** = Contacted with an information
request or a callback date; **Cold** = New, no answer or unreachable, or no outcome recorded. The phrases are set
in `lead_rules` in `brand.json`; see `brand.example.json`.

## Running locally

```bash
pip install -r requirements.txt
streamlit run streamlit_app_simple.py
```

## Project structure

```
streamlit_app_simple.py   # entry point and tab layout (Render runs this file)
dashboard/
  config.py               # white-label brand settings
  data.py                 # Google Sheets, demo data, funnel and scoring calculations
  ai.py                   # Claude features
  ui.py                   # styling and rendering helpers
brand.example.json        # sample brand configuration
render.yaml, Dockerfile   # deployment
```

## License

© 2026 Joseph Mews Dashboard. All rights reserved.
