"""Data loading (Google Sheets or built-in demo data) and funnel calculations.

Only aggregated counts and pseudonymous lead IDs are handled - no names,
emails or phone numbers (GDPR).
"""
import json
import os
import random
from dataclasses import dataclass
from datetime import date, datetime, timedelta

import pandas as pd
import streamlit as st

try:
    import gspread
    from google.oauth2.service_account import Credentials
    GOOGLE_SHEETS_AVAILABLE = True
except ImportError:
    GOOGLE_SHEETS_AVAILABLE = False


FUNNEL_STAGES = [
    "Total Leads", "Qualified Leads", "Viewings Scheduled", "Viewings Completed",
    "Offers Made", "Offers Accepted", "Closed Sales",
]
DAILY_NUMERIC = FUNNEL_STAGES + ["Daily Budget"]
WHATSAPP_NUMERIC = ["Messages Answered", "Positive", "Negative", "Relevant", "Irrelevant", "Scheduled Leads"]

# (label, from stage, to stage) - the steps bottleneck and what-if analysis work on
CONVERSION_STEPS = [
    ("Lead → Qualified", "Total Leads", "Qualified Leads"),
    ("Qualified → Viewing", "Qualified Leads", "Viewings Completed"),
    ("Viewing → Offer", "Viewings Completed", "Offers Made"),
    ("Offer → Accepted", "Offers Made", "Offers Accepted"),
    ("Accepted → Closed", "Offers Accepted", "Closed Sales"),
]

STAGE_PLAYBOOK = {
    "Lead → Qualified": [
        "Shift budget towards the sources with the highest qualification rate (see Channels).",
        "Reply to new leads within 5 minutes - qualification rates drop sharply after the first hour.",
        "Tighten ad targeting and add a budget question to forms to filter out low-intent leads.",
        "Use the AI lead scoring to call Hot leads first.",
    ],
    "Qualified → Viewing": [
        "Offer a viewing slot within 24 hours of qualification, with online self-booking.",
        "Send a short shortlist of matching properties before suggesting a viewing.",
        "Run a 3-touch WhatsApp/email sequence for qualified leads who haven't booked.",
        "Offer virtual viewings for overseas buyers.",
    ],
    "Viewing → Offer": [
        "Follow up within 4 hours of every viewing while interest is high.",
        "Share comparable sales and demand data to create urgency.",
        "Capture objections during the viewing and answer them in writing the same day.",
        "Invite serious buyers to a second viewing with decision makers present.",
    ],
    "Offer → Accepted": [
        "Back offers with local market data so vendors see them as credible.",
        "Pre-check buyer financing before submitting offers.",
        "Explore non-price terms: completion date, fixtures, chain-free status.",
        "Coach agents on structuring and negotiating offers.",
    ],
    "Accepted → Closed": [
        "Use a closing checklist with a clear timeline shared with both sides.",
        "Prepare legal and survey paperwork in advance to avoid delays.",
        "Send weekly status updates to keep momentum and spot fall-throughs early.",
        "Escalate stalled conveyancing within 48 hours.",
    ],
}

# Lead-level stages (optional "Leads" worksheet) and their base scores
LEAD_STAGES = [
    "New", "Contacted", "Qualified", "Viewing Scheduled", "Viewing Completed",
    "Offer Made", "Offer Accepted", "Closed", "Lost",
]
STAGE_POINTS = {
    "New": 10, "Contacted": 20, "Qualified": 40, "Viewing Scheduled": 55,
    "Viewing Completed": 70, "Offer Made": 85, "Offer Accepted": 95,
}
CLOSED_STAGES = {"Closed", "Lost"}


@dataclass
class DataBundle:
    metrics: dict
    daily: pd.DataFrame | None
    whatsapp: pd.DataFrame | None
    leads: pd.DataFrame | None
    loaded_at: datetime
    source: str  # "sheets" or "demo"


# --------------------------------------------------------------------------- #
# Google Sheets
# --------------------------------------------------------------------------- #

def _service_account_info():
    if os.getenv("GCP_SERVICE_ACCOUNT"):
        return json.loads(os.getenv("GCP_SERVICE_ACCOUNT"))
    if os.getenv("GCP_SERVICE_ACCOUNT_PROJECT_ID"):
        return {
            "type": os.getenv("GCP_SERVICE_ACCOUNT_TYPE", "service_account"),
            "project_id": os.getenv("GCP_SERVICE_ACCOUNT_PROJECT_ID"),
            "private_key_id": os.getenv("GCP_SERVICE_ACCOUNT_PRIVATE_KEY_ID"),
            "private_key": os.getenv("GCP_SERVICE_ACCOUNT_PRIVATE_KEY", "").replace("\\n", "\n"),
            "client_email": os.getenv("GCP_SERVICE_ACCOUNT_CLIENT_EMAIL"),
            "client_id": os.getenv("GCP_SERVICE_ACCOUNT_CLIENT_ID"),
            "auth_uri": os.getenv("GCP_SERVICE_ACCOUNT_AUTH_URI", "https://accounts.google.com/o/oauth2/auth"),
            "token_uri": os.getenv("GCP_SERVICE_ACCOUNT_TOKEN_URI", "https://oauth2.googleapis.com/token"),
            "auth_provider_x509_cert_url": os.getenv(
                "GCP_SERVICE_ACCOUNT_AUTH_PROVIDER_X509_CERT_URL", "https://www.googleapis.com/oauth2/v1/certs"),
            "client_x509_cert_url": os.getenv("GCP_SERVICE_ACCOUNT_CLIENT_X509_CERT_URL"),
        }
    try:
        if "gcp_service_account" in st.secrets:
            return dict(st.secrets["gcp_service_account"])
    except FileNotFoundError:
        pass
    return None


@st.cache_resource(show_spinner=False)
def _sheets_client():
    info = _service_account_info()
    if not info:
        raise RuntimeError("Google service account credentials are not configured.")
    credentials = Credentials.from_service_account_info(
        info,
        scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"],
    )
    return gspread.authorize(credentials)


def _clean(df, numeric_cols, date_cols=("Date",)):
    for col in date_cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")
    if "Date" in df.columns:
        df = df.dropna(subset=["Date"]).sort_values("Date").reset_index(drop=True)
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    return df


def _optional_worksheet(sheet, name, numeric_cols, date_cols=("Date",)):
    try:
        records = sheet.worksheet(name).get_all_records()
    except gspread.exceptions.WorksheetNotFound:
        return None
    df = pd.DataFrame(records)
    if df.empty:
        return None
    return _clean(df, numeric_cols, date_cols)


def metrics_from_sheet(df):
    metrics = {stage: 0 for stage in FUNNEL_STAGES}
    if df.empty or "Stage" not in df.columns or "Count" not in df.columns:
        return metrics
    for _, row in df.iterrows():
        metrics[str(row["Stage"]).strip()] = int(pd.to_numeric(row["Count"], errors="coerce") or 0)
    return metrics


@st.cache_data(ttl=60, show_spinner=False)
def load_from_sheets(spreadsheet_url):
    if not GOOGLE_SHEETS_AVAILABLE:
        raise RuntimeError("gspread is not installed.")
    sheet = _sheets_client().open_by_url(spreadsheet_url)
    metrics = metrics_from_sheet(pd.DataFrame(sheet.worksheet("Metrics").get_all_records()))
    leads = _optional_worksheet(sheet, "Leads", [], date_cols=("Date", "Last Contact"))
    if leads is not None and "Stage" in leads.columns:
        leads["Stage"] = leads["Stage"].astype(str).str.strip().str.title()
    return DataBundle(
        metrics=metrics,
        daily=_optional_worksheet(sheet, "Daily", DAILY_NUMERIC),
        whatsapp=_optional_worksheet(sheet, "WhatsApp", WHATSAPP_NUMERIC),
        leads=leads,
        loaded_at=datetime.now(),
        source="sheets",
    )


# --------------------------------------------------------------------------- #
# Demo data - always ends today so demos never show stale dates
# --------------------------------------------------------------------------- #

DEMO_SOURCES = {
    # source: (avg daily leads, qualification rate, daily budget)
    "Google Ads": (7.0, 0.38, 220),
    "Meta Ads": (6.0, 0.27, 160),
    "Instagram": (4.0, 0.31, 120),
    "Organic": (3.0, 0.45, 0),
    "Referral": (1.5, 0.62, 0),
}

DEMO_MESSAGES = {
    "hot": [
        "We'd like to make an offer close to asking. What's the vendor's timeline?",
        "Mortgage in principle is approved - we can move quickly on the right place.",
        "Loved the second viewing. Can you send the lease length and service charge breakdown?",
        "Could we see the penthouse again on Saturday with my architect?",
        "Our sale has completed, so we're chain-free and ready to proceed.",
    ],
    "warm": [
        "Can you send more photos of the garden and the floor plan?",
        "Is there any flexibility on the price?",
        "What's the parking situation for two cars?",
        "We're relocating from Dubai in spring - can we do a video viewing?",
        "Which schools are in the catchment area?",
    ],
    "cold": [
        "Just browsing for now, maybe next year.",
        "We've decided to rent for another year.",
        "It's above our budget, unfortunately.",
        "Too far from the office for us, sorry.",
        "",
    ],
}

DEMO_BUDGETS = ["£1M–£2M", "£2M–£3.5M", "£3.5M–£5M", "£5M+"]


def _binomial(rng, n, p):
    return sum(rng.random() < p for _ in range(int(n)))


@st.cache_data(show_spinner=False)
def build_demo_data(today: date, lead_id_prefix: str = "JM"):
    rng = random.Random(2026)
    days = 90
    start = today - timedelta(days=days - 1)

    daily_rows, whatsapp_rows = [], []
    for i in range(days):
        day = start + timedelta(days=i)
        growth = 1 + 0.3 * i / days
        weekend = 0.7 if day.weekday() >= 5 else 1.0
        for source, (mu, qual_rate, budget) in DEMO_SOURCES.items():
            leads = max(0, round(rng.gauss(mu * growth * weekend, mu * 0.35)))
            qualified = _binomial(rng, leads, qual_rate)
            scheduled = _binomial(rng, qualified, 0.62)
            completed = _binomial(rng, scheduled, 0.80)
            offers = _binomial(rng, completed, 0.34)
            accepted = _binomial(rng, offers, 0.58)
            closed = _binomial(rng, accepted, 0.85)
            daily_rows.append({
                "Date": pd.Timestamp(day), "Source": source,
                "Total Leads": leads, "Qualified Leads": qualified,
                "Viewings Scheduled": scheduled, "Viewings Completed": completed,
                "Offers Made": offers, "Offers Accepted": accepted, "Closed Sales": closed,
                "Daily Budget": round(budget * rng.uniform(0.9, 1.1)) if budget else 0,
            })

        answered = max(0, round(rng.gauss(26 * growth, 6)))
        relevant = _binomial(rng, answered, 0.72)
        positive = _binomial(rng, relevant, 0.58)
        whatsapp_rows.append({
            "Date": pd.Timestamp(day), "Messages Answered": answered,
            "Relevant": relevant, "Irrelevant": answered - relevant,
            "Positive": positive, "Negative": relevant - positive,
            "Scheduled Leads": _binomial(rng, positive, 0.42),
        })

    daily = pd.DataFrame(daily_rows)
    whatsapp = pd.DataFrame(whatsapp_rows)

    stage_weights = {
        "New": 12, "Contacted": 14, "Qualified": 12, "Viewing Scheduled": 8,
        "Viewing Completed": 7, "Offer Made": 4, "Offer Accepted": 2, "Closed": 3, "Lost": 8,
    }
    lead_rows = []
    for n in range(70):
        stage = rng.choices(list(stage_weights), weights=list(stage_weights.values()))[0]
        created = today - timedelta(days=rng.randint(0, 45))
        if stage in ("Offer Made", "Offer Accepted", "Viewing Completed"):
            mood = rng.choices(["hot", "warm", "cold"], weights=[6, 3, 1])[0]
        elif stage in ("New", "Contacted", "Lost"):
            mood = rng.choices(["hot", "warm", "cold"], weights=[1, 3, 6])[0]
        else:
            mood = rng.choices(["hot", "warm", "cold"], weights=[3, 5, 2])[0]
        quiet_days = {"hot": rng.randint(0, 4), "warm": rng.randint(2, 12), "cold": rng.randint(8, 30)}[mood]
        last_contact = max(created, today - timedelta(days=quiet_days))
        lead_rows.append({
            "Lead ID": f"{lead_id_prefix}-{1041 + n}",
            "Date": pd.Timestamp(created),
            "Source": rng.choices(list(DEMO_SOURCES), weights=[7, 6, 4, 3, 1.5])[0],
            "Stage": stage,
            "Budget": rng.choice(DEMO_BUDGETS),
            "Last Contact": pd.Timestamp(last_contact),
            "Last Message": rng.choice(DEMO_MESSAGES[mood]),
        })
    leads = pd.DataFrame(lead_rows).sort_values("Date", ascending=False).reset_index(drop=True)

    return DataBundle(
        metrics=metrics_from_daily(daily),
        daily=daily,
        whatsapp=whatsapp,
        leads=leads,
        loaded_at=datetime.now(),
        source="demo",
    )


# --------------------------------------------------------------------------- #
# Calculations
# --------------------------------------------------------------------------- #

def has_funnel_columns(df):
    return df is not None and not df.empty and "Date" in df.columns and "Total Leads" in df.columns


def metrics_from_daily(daily):
    return {stage: int(daily[stage].sum()) if stage in daily.columns else 0 for stage in FUNNEL_STAGES}


def daily_totals(daily):
    """One row per date (the Daily sheet may have one row per date and source)."""
    cols = [c for c in DAILY_NUMERIC if c in daily.columns]
    return daily.groupby("Date", as_index=False)[cols].sum()


def pct(numerator, denominator):
    return numerator / denominator * 100 if denominator else 0.0


def conversion_steps(metrics):
    steps = []
    for label, src, dst in CONVERSION_STEPS:
        start, end = metrics.get(src, 0), metrics.get(dst, 0)
        steps.append({"stage": label, "from": start, "to": end,
                      "rate": pct(end, start), "drop_off": max(start - end, 0)})
    return steps


def bottlenecks(metrics):
    return sorted((s for s in conversion_steps(metrics) if s["from"] > 0), key=lambda s: s["rate"])


def project(metrics, n_leads):
    total = metrics.get("Total Leads", 0)
    if not total:
        return {}
    return {stage: n_leads * metrics.get(stage, 0) / total for stage in FUNNEL_STAGES}


def what_if(metrics, n_leads, uplift_points=10.0):
    """Extra closed sales if one conversion step improves by `uplift_points` percentage points."""
    base_closed = project(metrics, n_leads).get("Closed Sales", 0.0)
    rows = []
    for step in conversion_steps(metrics):
        rate = step["rate"]
        if rate <= 0:
            rows.append({**step, "new_rate": None, "closed": None, "gain": None})
            continue
        new_rate = min(rate + uplift_points, 100.0)
        closed = base_closed * new_rate / rate
        rows.append({**step, "new_rate": new_rate, "closed": closed, "gain": closed - base_closed})
    return base_closed, rows


def funnel_temperature(metrics):
    """Hot/Warm/Cold estimated from aggregate funnel counts (used when there is no Leads sheet)."""
    total = metrics.get("Total Leads", 0)
    if not total:
        return {"hot": 0, "warm": 0, "cold": 0, "quality_score": 0.0}
    hot = min(metrics.get("Viewings Completed", 0), metrics.get("Offers Made", 0) + metrics.get("Offers Accepted", 0))
    warm = max(0, min(metrics.get("Qualified Leads", 0),
                      metrics.get("Viewings Scheduled", 0) + metrics.get("Viewings Completed", 0)) - hot)
    cold = max(0, total - hot - warm)
    return {"hot": hot, "warm": warm, "cold": cold, "quality_score": (hot * 3 + warm * 2 + cold) / total}


def temperature_trend(daily):
    rows = []
    for _, row in daily_totals(daily).iterrows():
        temp = funnel_temperature({s: row.get(s, 0) for s in FUNNEL_STAGES})
        rows.append({"Date": row["Date"], "Hot": temp["hot"], "Warm": temp["warm"],
                     "Cold": temp["cold"], "Quality Score": temp["quality_score"]})
    return pd.DataFrame(rows)


def source_breakdown(daily, leads_scored=None):
    if daily is None or daily.empty or "Source" not in daily.columns:
        return None
    cols = [c for c in DAILY_NUMERIC if c in daily.columns]
    grouped = daily.groupby("Source", as_index=False)[cols].sum()
    rows = []
    for _, row in grouped.iterrows():
        metrics = {s: row.get(s, 0) for s in FUNNEL_STAGES}
        budget = row.get("Daily Budget", 0)
        entry = {
            "Source": row["Source"],
            "Leads": int(metrics["Total Leads"]),
            "Qualified %": pct(metrics["Qualified Leads"], metrics["Total Leads"]),
            "Close %": pct(metrics["Closed Sales"], metrics["Total Leads"]),
            "Closed": int(metrics["Closed Sales"]),
            "Spend": budget,
            "Cost / Lead": budget / metrics["Total Leads"] if budget and metrics["Total Leads"] else None,
            "Quality Score": funnel_temperature(metrics)["quality_score"],
        }
        if leads_scored is not None and not leads_scored.empty:
            open_leads = leads_scored[leads_scored["Source"] == row["Source"]]
            entry["Hot leads"] = int((open_leads["Temperature"] == "Hot").sum())
        rows.append(entry)
    return pd.DataFrame(rows).sort_values("Quality Score", ascending=False).reset_index(drop=True)


def temperature_from_score(score):
    if score >= 70:
        return "Hot"
    if score >= 40:
        return "Warm"
    return "Cold"


def score_leads(leads, today):
    """Rule-based score for open leads: funnel stage plus recency of last contact."""
    if leads is None or leads.empty or "Stage" not in leads.columns:
        return None
    df = leads[~leads["Stage"].isin(CLOSED_STAGES)].copy()
    if df.empty:
        return None
    if "Lead ID" not in df.columns:
        df["Lead ID"] = [f"L-{i + 1}" for i in range(len(df))]
    df["Lead ID"] = df["Lead ID"].astype(str)
    last_contact = df["Last Contact"] if "Last Contact" in df.columns else df.get("Date")
    today_ts = pd.Timestamp(today)
    df["Days Since Contact"] = (today_ts - last_contact).dt.days.clip(lower=0) if last_contact is not None else None

    def rule(row):
        score = STAGE_POINTS.get(row["Stage"], 10)
        days = row.get("Days Since Contact")
        if pd.notna(days):
            if days <= 3:
                score += 10
            elif days > 21:
                score -= 20
            elif days > 10:
                score -= 10
        return max(0, min(100, score))

    df["Score"] = df.apply(rule, axis=1)
    df["Temperature"] = df["Score"].map(temperature_from_score)
    return df.reset_index(drop=True)
