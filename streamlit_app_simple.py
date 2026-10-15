"""Lead funnel dashboard - entry point (Render runs this file)."""
import hashlib
import json
import os
from datetime import date, datetime, timedelta

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from dashboard import ai, data, ui
from dashboard.config import load_brand

brand = load_brand()

st.set_page_config(
    page_title=f"{brand.name} · {brand.tagline}",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

PERIODS = {"Last 7 days": 7, "Last 30 days": 30, "Last 90 days": 90}
CHAT_SUGGESTIONS = [
    "Which lead source brings the best quality leads?",
    "Where are we losing the most leads, and what should we do?",
    "How did this period compare with the previous one?",
    "Which hot leads should the team call first today?",
]
AI_DISABLED_HELP = "Set ANTHROPIC_API_KEY to enable Claude features."


# --------------------------------------------------------------------------- #
# Data
# --------------------------------------------------------------------------- #

def load_bundle(today):
    url = os.getenv("GOOGLE_SHEETS_URL")
    force_demo = (os.getenv("DEMO_MODE", "").lower() in ("1", "true", "yes")
                  or st.query_params.get("demo") in ("1", "true"))
    if url and not force_demo:
        try:
            return data.load_from_sheets(url), None
        except Exception as e:  # any connection/format problem: explain it and keep the demo usable
            note = f"Could not load Google Sheets ({e}). Showing demo data instead."
            return data.build_demo_data(today, brand.lead_id_prefix), note
    note = None if force_demo else (
        "Google Sheets is not connected (GOOGLE_SHEETS_URL is not set), so the dashboard is showing demo data.")
    return data.build_demo_data(today, brand.lead_id_prefix), note


def in_range(df, date_range):
    if df is None or date_range is None or "Date" not in df.columns:
        return df
    start, end = date_range
    return df[(df["Date"].dt.date >= start) & (df["Date"].dt.date <= end)]


def choose_period(bundle, select_col, custom_col):
    daily = bundle.daily
    if not data.has_funnel_columns(daily):
        select_col.selectbox("Reporting period", ["All time"], disabled=True,
                             help="Add a 'Daily' worksheet to filter by date.")
        return None, "All time"

    first, last = daily["Date"].min().date(), daily["Date"].max().date()
    options = ["All time", *PERIODS, "Custom range"]
    default = options.index("Last 30 days") if bundle.source == "demo" else 0
    choice = select_col.selectbox("Reporting period", options, index=default,
                                  help="Periods end on the latest date in the data.")

    if choice == "All time":
        return None, f"{first:%d %b %Y} – {last:%d %b %Y}"
    if choice == "Custom range":
        picked = custom_col.date_input("Dates", value=(max(first, last - timedelta(days=29)), last),
                                       min_value=first, max_value=last, format="DD/MM/YYYY")
        start, end = (picked if len(picked) == 2 else (picked[0], picked[0]))
    else:
        start, end = max(first, last - timedelta(days=PERIODS[choice] - 1)), last
    return (start, end), f"{start:%d %b} – {end:%d %b %Y}"


def previous_period(daily, date_range):
    if date_range is None or not data.has_funnel_columns(daily):
        return None
    start, end = date_range
    length = (end - start).days + 1
    prev_start, prev_end = start - timedelta(days=length), start - timedelta(days=1)
    if daily["Date"].min().date() > prev_start:
        return None
    return data.metrics_from_daily(in_range(daily, (prev_start, prev_end)))


def change_note(current, previous):
    if not previous:
        return ""
    change = (current - previous) / previous * 100
    return f"{'▲' if change >= 0 else '▼'} {abs(change):.0f}% vs previous period"


def fingerprint(obj):
    return hashlib.md5(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()


def apply_ai_scores(scored):
    """Overlay Claude's per-lead scores (if generated for these exact leads) on the rule-based scores."""
    scored["Scored by"] = "Rules"
    cached = st.session_state.get("lead_ai")
    if not cached or cached["key"] != lead_fingerprint(scored):
        return scored, False
    results = cached["data"]
    scored["Reason"], scored["Next Action"] = "", ""
    for i, lead_id in scored["Lead ID"].items():
        result = results.get(str(lead_id))
        if result:
            scored.at[i, "Score"] = result["score"]
            scored.at[i, "Temperature"] = result["temperature"]
            scored.at[i, "Reason"] = result["reason"]
            scored.at[i, "Next Action"] = result["next_action"]
            scored.at[i, "Scored by"] = "Claude"
    return scored, True


def lead_records(scored, limit=80):
    cols = {"Lead ID": "lead_id", "Stage": "stage", "Source": "source", "Budget": "budget",
            "Days Since Contact": "days_since_contact", "Last Message": "last_message", "Date": "created"}
    present = [c for c in cols if c in scored.columns]
    records = scored.head(limit)[present].rename(columns=cols)
    if "created" in records.columns:
        records["created"] = records["created"].dt.strftime("%Y-%m-%d")
    return records.to_dict("records")


def lead_fingerprint(scored):
    return fingerprint(lead_records(scored))


def build_ai_context(bundle, period_label, metrics, steps, temp, whatsapp, sources, totals, scored, today):
    ctx = {
        "business": brand.name,
        "industry": brand.industry,
        "currency": brand.currency,
        "today": today.isoformat(),
        "reporting_period": period_label,
        "data_source": "demo data" if bundle.source == "demo" else "live Google Sheets",
        "funnel_counts": metrics,
        "conversion_steps": [{"step": s["stage"], "rate_pct": round(s["rate"], 1), "lost": s["drop_off"]}
                             for s in steps],
        "overall_close_rate_pct": round(data.pct(metrics["Closed Sales"], metrics["Total Leads"]), 2),
        "lead_temperature": temp,
        "targets_pct": brand.targets,
    }
    if whatsapp:
        ctx["whatsapp_totals"] = whatsapp
    if sources is not None:
        ctx["lead_sources"] = sources.round(2).to_dict("records")
    if totals is not None and not totals.empty:
        weekly = totals.set_index("Date").resample("W-SUN").sum(numeric_only=True).reset_index()
        weekly["Date"] = weekly["Date"].dt.strftime("week ending %Y-%m-%d")
        ctx["weekly_totals"] = weekly.to_dict("records")
    if scored is not None:
        hottest = scored.sort_values("Score", ascending=False).head(10)
        ctx["open_leads"] = {
            "scoring_method": temp["method"],
            "by_temperature": scored["Temperature"].value_counts().to_dict(),
            "by_stage": scored["Stage"].value_counts().to_dict(),
            "hottest": [{**record, "temperature": t, "score": int(s)} for record, t, s in zip(
                lead_records(hottest, limit=10), hottest["Temperature"], hottest["Score"])],
        }
    return ctx


# --------------------------------------------------------------------------- #
# Sections
# --------------------------------------------------------------------------- #

def section_insight(name):
    cached = st.session_state.get("insights")
    if cached and cached["key"] == st.session_state.get("context_key"):
        ui.insight(cached["data"].get(name))


def render_overview(metrics, prev, totals, temp, spend, context, today):
    total, qualified = metrics["Total Leads"], metrics["Qualified Leads"]
    closed, viewings = metrics["Closed Sales"], metrics["Viewings Completed"]
    prev = prev or {}

    cols = st.columns(6)
    with cols[0]:
        avg = f"{total / len(totals):.1f}/day · " if totals is not None and len(totals) else ""
        ui.kpi("Leads", f"{total:,}", avg + change_note(total, prev.get("Total Leads")))
    with cols[1]:
        ui.kpi("Qualified", f"{data.pct(qualified, total):.1f}%", f"{qualified:,} leads")
    with cols[2]:
        ui.kpi("Viewings", f"{viewings:,}", f"{data.pct(viewings, qualified):.0f}% of qualified")
    with cols[3]:
        ui.kpi("Closed sales", f"{closed:,}", change_note(closed, prev.get("Closed Sales"))
               or f"{data.pct(closed, total):.1f}% close rate")
    with cols[4]:
        ui.kpi("Close rate", f"{data.pct(closed, total):.2f}%", f"target {brand.targets.get('Close Rate', 0)}%")
    with cols[5]:
        if spend:
            ui.kpi("Cost per lead", f"{brand.currency}{spend / total:,.0f}" if total else "–",
                   f"{brand.currency}{spend / closed:,.0f} per sale" if closed else "")
        else:
            ui.kpi("Lead quality", f"{temp['quality_score']:.2f} / 3", "weighted Hot/Warm/Cold")

    st.markdown("#### Funnel at a glance")
    ui.flow([
        ("Leads", total, data.pct(qualified, total)),
        ("Qualified", qualified, data.pct(metrics["Viewings Scheduled"], qualified)),
        ("Viewings booked", metrics["Viewings Scheduled"], data.pct(viewings, metrics["Viewings Scheduled"])),
        ("Viewings done", viewings, data.pct(metrics["Offers Made"], viewings)),
        ("Offers", metrics["Offers Made"], data.pct(metrics["Offers Accepted"], metrics["Offers Made"])),
        ("Accepted", metrics["Offers Accepted"], data.pct(closed, metrics["Offers Accepted"])),
        ("Closed", closed, None),
    ], final=("Close rate", f"{data.pct(closed, total):.1f}%"))
    section_insight("overview")

    left, right = st.columns([3, 2])
    with left:
        render_report(context, today)
    with right:
        st.markdown("#### Priority actions")
        cached = st.session_state.get("insights")
        if cached and cached["key"] == st.session_state.get("context_key"):
            for i, action in enumerate(cached["data"].get("actions", [])[:3], 1):
                st.markdown(f"**{i}.** {action}")
        else:
            st.caption("Generate AI insights (top right) to get this week's three highest-impact actions.")


def render_report(context, today):
    st.markdown("#### Executive report")
    st.caption("A one-page summary for leadership, written by Claude from the figures on this dashboard.")
    cached = st.session_state.get("report")
    if st.button("Write report", disabled=not ai.is_configured(),
                 help=None if ai.is_configured() else AI_DISABLED_HELP):
        with st.container(border=True):
            try:
                text = st.write_stream(ai.stream_report(brand, context, today))
                cached = {"key": st.session_state.context_key, "text": text, "date": today}
                st.session_state.report = cached
            except ai.AIError as e:
                st.error(str(e))
                return
    elif cached:
        if cached["key"] != st.session_state.context_key:
            st.caption("The report below was written for different filters. Write it again to refresh it.")
        with st.expander("Latest report", expanded=False):
            st.markdown(cached["text"])
    if cached:
        slug = "".join(ch if ch.isalnum() else "-" for ch in brand.name.lower()).strip("-")
        st.download_button("Download report (.md)", cached["text"],
                           file_name=f"{slug}-lead-report-{cached['date']:%Y-%m-%d}.md", mime="text/markdown")


def render_targets(metrics):
    actuals = {
        "Qualification Rate": data.pct(metrics["Qualified Leads"], metrics["Total Leads"]),
        "Viewing → Offer": data.pct(metrics["Offers Made"], metrics["Viewings Completed"]),
        "Close Rate": data.pct(metrics["Closed Sales"], metrics["Total Leads"]),
    }
    lines = []
    for name, target in brand.targets.items():
        value = actuals.get(name)
        if value is not None:
            lines.append(f"{'✅' if value >= float(target) else '⚠️'} **{name}**: {value:.1f}% (target {target}%)")
    if lines:
        st.markdown("#### Targets")
        st.markdown("\n\n".join(lines))


def render_funnel_and_scoring(metrics, steps, temp, scored, ai_scored, today):
    st.markdown("### Funnel")
    section_insight("funnel")
    left, right = st.columns([3, 2])
    with left:
        fig = go.Figure(go.Funnel(
            y=data.FUNNEL_STAGES, x=[metrics[s] for s in data.FUNNEL_STAGES],
            textinfo="value+percent initial",
            marker={"color": [brand.primary_color, brand.secondary_color, "#9f7aea", "#4facfe",
                              "#00b8d9", "#38b2ac", ui.GOOD]},
            connector={"line": {"color": "rgba(128,128,128,.4)", "dash": "dot"}},
        ))
        ui.chart(fig, "funnel", height=360, legend=False)
    with right:
        colors = [ui.BAD if s["rate"] < 30 else ui.WARM if s["rate"] < 70 else ui.GOOD for s in steps]
        fig = go.Figure(go.Bar(
            x=[s["rate"] for s in steps], y=[s["stage"] for s in steps], orientation="h",
            marker_color=colors, text=[f"{s['rate']:.0f}%" for s in steps], textposition="outside",
            hovertemplate="%{y}: %{x:.1f}%<extra></extra>",
        ))
        fig.update_layout(title="Step conversion (red < 30% · amber 30–70% · green > 70%)",
                          xaxis=dict(range=[0, 110], title=None), yaxis=dict(autorange="reversed"))
        ui.chart(fig, "step_rates", height=360, legend=False)

    worst = data.bottlenecks(metrics)
    if worst:
        w = worst[0]
        st.markdown("#### Biggest bottleneck")
        c1, c2 = st.columns([1, 2])
        with c1:
            ui.kpi(w["stage"], f"{w['rate']:.1f}%", f"{w['drop_off']:,} of {w['from']:,} leads lost at this step")
        with c2:
            st.markdown("\n".join(f"- {tip}" for tip in data.STAGE_PLAYBOOK[w["stage"]]))
    render_targets(metrics)

    st.divider()
    st.markdown("### Lead scoring")
    with st.expander("How is lead scoring calculated?"):
        st.markdown("""
- **Hot** – ready to transact soon: viewing done and in the offer stage, or a strong buying signal in their last message.
- **Warm** – qualified and engaged (viewings booked or done) but still needs nurturing.
- **Cold** – early stage or gone quiet: new, not yet qualified, or no contact for weeks.

**With a `Leads` worksheet** every open lead gets a 0–100 score: a base score for its stage
(New 10 → Offer Accepted 95), +10 if contacted in the last 3 days, −10 after 10 days and −20 after
21 days of silence. Hot ≥ 70, Warm 40–69, Cold < 40. **Score with Claude** re-scores each lead by also
reading the lead's last message, and explains every score.

**Without a `Leads` worksheet** the split is estimated from the funnel counts.
The **quality score** is (Hot × 3 + Warm × 2 + Cold × 1) ÷ leads, from 1.0 (all cold) to 3.0 (all hot).
""")
    section_insight("scoring")

    total = temp["hot"] + temp["warm"] + temp["cold"]
    cols = st.columns(4)
    cards = [("Hot", temp["hot"], ui.HOT), ("Warm", temp["warm"], ui.WARM), ("Cold", temp["cold"], ui.COLD)]
    for col, (label, count, color) in zip(cols, cards):
        with col:
            ui.temperature_card(f"{label} leads", f"{count:,}", f"{data.pct(count, total):.0f}% of {temp['basis']}",
                                temp["notes"][label], color)
    with cols[3]:
        q = temp["quality_score"]
        ui.temperature_card("Quality score", f"{q:.2f}", "out of 3.00",
                            "Excellent" if q >= 2.0 else "Good" if q >= 1.5 else "Needs work",
                            ui.GOOD if q >= 2.0 else ui.WARM if q >= 1.5 else ui.BAD)

    if scored is None:
        st.info("Add a **Leads** worksheet (Lead ID, Date, Source, Stage, Budget, Last Contact, Last Message) "
                "to score every open lead individually and let Claude prioritise them. Use pseudonymous IDs only.")
        return

    st.markdown("#### Open leads")
    c1, c2 = st.columns([3, 2])
    with c1:
        st.caption(f"{len(scored)} open leads across all dates · "
                   + ("scored by Claude from stage, recency, budget and the lead's last message" if ai_scored
                      else "rule-based scores · use Claude for message-aware scoring"))
    with c2:
        if st.button("Score leads with Claude", disabled=not ai.is_configured(),
                     help=None if ai.is_configured() else AI_DISABLED_HELP, width="stretch"):
            with st.spinner("Claude is reading every lead…"):
                try:
                    st.session_state.lead_ai = {"key": lead_fingerprint(scored),
                                                "data": ai.score_leads(brand, lead_records(scored), today)}
                    st.rerun()
                except ai.AIError as e:
                    st.error(str(e))

    show = st.segmented_control("Show", ["Hot", "Warm", "Cold"], selection_mode="multi",
                                default=["Hot", "Warm", "Cold"], key="temp_filter")
    view = scored[scored["Temperature"].isin(show or [])].sort_values("Score", ascending=False)
    columns = ["Lead ID", "Temperature", "Score", "Stage", "Source", "Budget", "Days Since Contact", "Last Message"]
    if ai_scored:
        columns += ["Reason", "Next Action"]
    st.dataframe(
        view[[c for c in columns if c in view.columns]],
        hide_index=True, width="stretch", height=min(420, 38 + 35 * len(view)),
        column_config={
            "Score": st.column_config.ProgressColumn("Score", min_value=0, max_value=100, format="%d"),
            "Days Since Contact": st.column_config.NumberColumn("Days quiet", format="%d"),
            "Last Message": st.column_config.TextColumn(width="large"),
            "Reason": st.column_config.TextColumn(width="large"),
            "Next Action": st.column_config.TextColumn(width="medium"),
        },
    )


def render_channels(whatsapp_df, whatsapp, sources):
    section_insight("channels")
    if not whatsapp and sources is None:
        st.info("Add a **WhatsApp** worksheet and a **Source** column in the Daily worksheet to see channel performance.")
        return

    if whatsapp:
        st.markdown("### WhatsApp")
        answered, relevant = whatsapp["Messages Answered"], whatsapp["Relevant"]
        positive, scheduled = whatsapp["Positive"], whatsapp["Scheduled Leads"]
        ui.flow([
            ("Answered", answered, data.pct(relevant, answered)),
            ("Relevant", relevant, data.pct(positive, relevant)),
            ("Positive", positive, data.pct(scheduled, positive)),
            ("Scheduled", scheduled, None),
        ], final=("Conversion", f"{data.pct(scheduled, answered):.1f}%"))

        left, right = st.columns(2)
        with left:
            fig = go.Figure()
            fig.add_bar(x=whatsapp_df["Date"], y=whatsapp_df["Messages Answered"], name="Answered",
                        marker_color=ui.rgba("#25D366", .55))
            fig.add_scatter(x=whatsapp_df["Date"], y=whatsapp_df["Scheduled Leads"], name="Scheduled",
                            mode="lines+markers", line=dict(color="#128C7E", width=2.5), yaxis="y2")
            fig.update_layout(title="Messages answered vs leads scheduled",
                              yaxis2=dict(overlaying="y", side="right", showgrid=False))
            ui.chart(fig, "wa_daily", time_series=True)
        with right:
            fig = go.Figure()
            for col, color in (("Positive", ui.GOOD), ("Negative", ui.BAD), ("Irrelevant", "#a0aec0")):
                if col in whatsapp_df.columns:
                    fig.add_bar(x=whatsapp_df["Date"], y=whatsapp_df[col], name=col, marker_color=color)
            fig.update_layout(title="Conversation quality", barmode="stack")
            ui.chart(fig, "wa_quality", time_series=True)

    if sources is not None:
        st.markdown("### Lead sources")
        left, right = st.columns([3, 2])
        with left:
            st.dataframe(
                sources, hide_index=True, width="stretch",
                column_config={
                    "Qualified %": st.column_config.NumberColumn(format="%.1f%%"),
                    "Close %": st.column_config.NumberColumn(format="%.2f%%"),
                    "Spend": st.column_config.NumberColumn(format=f"{brand.currency}%,.0f"),
                    "Cost / Lead": st.column_config.NumberColumn(format=f"{brand.currency}%.0f"),
                    "Quality Score": st.column_config.ProgressColumn(min_value=1, max_value=3, format="%.2f"),
                },
            )
        with right:
            fig = go.Figure(go.Bar(
                x=sources["Source"], y=sources["Qualified %"], marker_color=brand.primary_color,
                text=[f"{v:.0f}%" for v in sources["Qualified %"]], textposition="outside",
            ))
            fig.update_layout(title="Qualification rate by source", yaxis=dict(title=None))
            ui.chart(fig, "source_quality", legend=False)


def render_trends(totals):
    section_insight("trends")
    if totals is None or totals.empty:
        st.info("Add a **Daily** worksheet (Date plus the funnel columns) to see trends over time.")
        return

    rolling = totals.set_index("Date")[["Total Leads", "Closed Sales"]].rolling(7, min_periods=1).mean()
    left, right = st.columns(2)
    with left:
        fig = go.Figure()
        fig.add_bar(x=totals["Date"], y=totals["Total Leads"], name="Leads", marker_color=ui.rgba(brand.primary_color, .35))
        fig.add_scatter(x=rolling.index, y=rolling["Total Leads"], name="7-day average",
                        line=dict(color=brand.primary_color, width=2.5))
        fig.update_layout(title="Daily leads")
        ui.chart(fig, "trend_leads", time_series=True)
    with right:
        fig = go.Figure()
        fig.add_bar(x=totals["Date"], y=totals["Closed Sales"], name="Closed", marker_color=ui.rgba(ui.GOOD, .4))
        fig.add_scatter(x=rolling.index, y=rolling["Closed Sales"], name="7-day average",
                        line=dict(color=ui.GOOD, width=2.5))
        fig.update_layout(title="Daily closed sales")
        ui.chart(fig, "trend_closed", time_series=True)

    left, right = st.columns(2)
    with left:
        temps = data.temperature_trend(totals)
        fig = go.Figure()
        for label, color in (("Cold", ui.COLD), ("Warm", ui.WARM), ("Hot", ui.HOT)):
            fig.add_scatter(x=temps["Date"], y=temps[label], name=label, stackgroup="one",
                            line=dict(width=0.5, color=color))
        fig.update_layout(title="Lead mix over time (estimated from daily funnel counts)")
        ui.chart(fig, "trend_temperature", time_series=True)
    with right:
        if totals.get("Daily Budget", pd.Series(dtype=float)).sum() > 0:
            cpl = totals["Daily Budget"] / totals["Total Leads"].where(totals["Total Leads"] > 0)
            fig = go.Figure()
            fig.add_bar(x=totals["Date"], y=totals["Daily Budget"], name="Spend", marker_color=ui.rgba("#a0aec0", .5))
            fig.add_scatter(x=totals["Date"], y=cpl.rolling(7, min_periods=1).mean(), name="Cost per lead (7-day)",
                            line=dict(color=brand.secondary_color, width=2.5), yaxis="y2")
            fig.update_layout(title=f"Spend and cost per lead ({brand.currency})",
                              yaxis2=dict(overlaying="y", side="right", showgrid=False))
            ui.chart(fig, "trend_spend", time_series=True)
        else:
            fig = go.Figure(go.Scatter(x=temps["Date"], y=temps["Quality Score"].rolling(7, min_periods=1).mean(),
                                       line=dict(color=brand.primary_color, width=2.5), name="Quality"))
            fig.update_layout(title="Lead quality score (7-day average)", yaxis=dict(range=[1, 3]))
            ui.chart(fig, "trend_quality", legend=False, time_series=True)


def render_chat(context):
    st.caption("Ask anything about the figures on this dashboard. Claude answers from the selected reporting period.")
    if not ai.is_configured():
        st.info(AI_DISABLED_HELP)
        return

    history = st.session_state.setdefault("chat", [])
    prompt = None
    cols = st.columns(len(CHAT_SUGGESTIONS))
    for col, suggestion in zip(cols, CHAT_SUGGESTIONS):
        if col.button(suggestion, width="stretch"):
            prompt = suggestion

    for message in history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    typed = st.chat_input("Ask about leads, channels, conversion…")
    prompt = typed or prompt
    if prompt:
        history.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        with st.chat_message("assistant"):
            try:
                answer = st.write_stream(ai.stream_chat(brand, context, history))
                history.append({"role": "assistant", "content": answer})
            except ai.AIError as e:
                history.pop()
                st.error(str(e))

    if history and st.button("Clear conversation"):
        history.clear()
        st.rerun()


# --------------------------------------------------------------------------- #
# Page
# --------------------------------------------------------------------------- #

def main():
    ui.inject_css(brand)
    today = date.today()
    header_slot = st.container()

    bundle, note = load_bundle(today)

    c_period, c_custom, _, c_refresh, c_ai = st.columns([2, 2, 2, 1, 1.6], vertical_alignment="bottom")
    date_range, period_label = choose_period(bundle, c_period, c_custom)
    if c_refresh.button("Refresh", width="stretch", help="Reload data from Google Sheets"):
        st.cache_data.clear()
        st.rerun()

    with header_slot:
        ui.header(brand, period_label, bundle.loaded_at, bundle.source)
        if note:
            st.info(note)

    daily = in_range(bundle.daily, date_range)
    metrics = bundle.metrics if date_range is None else data.metrics_from_daily(daily)
    prev = previous_period(bundle.daily, date_range)
    totals = data.daily_totals(daily) if data.has_funnel_columns(daily) else None
    spend = float(daily["Daily Budget"].sum()) if daily is not None and "Daily Budget" in daily.columns else 0.0

    whatsapp_df = in_range(bundle.whatsapp, date_range)
    whatsapp = None
    if whatsapp_df is not None and not whatsapp_df.empty:
        whatsapp = {c: int(whatsapp_df[c].sum()) if c in whatsapp_df.columns else 0
                    for c in data.WHATSAPP_NUMERIC}

    steps = data.conversion_steps(metrics)
    scored = data.score_leads(bundle.leads, today)
    ai_scored = False
    if scored is not None:
        scored, ai_scored = apply_ai_scores(scored)
        counts = scored["Temperature"].value_counts()
        hot, warm, cold = (int(counts.get(t, 0)) for t in ("Hot", "Warm", "Cold"))
        temp = {
            "hot": hot, "warm": warm, "cold": cold,
            "quality_score": (hot * 3 + warm * 2 + cold) / len(scored),
            "basis": "open leads",
            "method": "scored by Claude" if ai_scored else "rule-based per-lead score",
            "notes": {"Hot": "ready to transact", "Warm": "needs nurturing", "Cold": "early or quiet"},
        }
    else:
        temp = data.funnel_temperature(metrics)
        temp.update({
            "basis": "leads", "method": "estimated from funnel counts",
            "notes": {
                "Hot": f"{data.pct(metrics['Closed Sales'], temp['hot']):.0f}% → close" if temp["hot"] else "",
                "Warm": f"{data.pct(temp['hot'], temp['warm']):.0f}% → hot" if temp["warm"] else "",
                "Cold": f"{data.pct(temp['warm'], temp['cold']):.0f}% → warm" if temp["cold"] else "",
            },
        })
    sources = data.source_breakdown(daily, scored)

    ai_temp = {k: v for k, v in temp.items() if k != "notes"}
    context = build_ai_context(bundle, period_label, metrics, steps, ai_temp, whatsapp, sources, totals, scored, today)
    st.session_state.context_key = fingerprint(context)

    insights_ready = (st.session_state.get("insights", {}).get("key") == st.session_state.context_key)
    if c_ai.button("Refresh AI insights" if insights_ready else "✨ AI insights", type="primary", width="stretch",
                   disabled=not ai.is_configured(), help=None if ai.is_configured() else AI_DISABLED_HELP):
        with st.spinner("Claude is analysing the dashboard…"):
            try:
                st.session_state.insights = {"key": st.session_state.context_key,
                                             "data": ai.generate_insights(brand, context)}
            except ai.AIError as e:
                st.error(str(e))

    tabs = st.tabs(["Overview", "Funnel & Scoring", "Channels", "Trends", "Ask AI"])
    with tabs[0]:
        render_overview(metrics, prev, totals, temp, spend, context, today)
    with tabs[1]:
        render_funnel_and_scoring(metrics, steps, temp, scored, ai_scored, today)
    with tabs[2]:
        render_channels(whatsapp_df, whatsapp, sources)
    with tabs[3]:
        render_trends(totals)
    with tabs[4]:
        render_chat(context)

    ui.footer(brand, datetime.now().year)


main()
