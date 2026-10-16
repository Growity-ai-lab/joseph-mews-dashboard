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
    pipeline = data.lead_pipeline(bundle.leads)
    if pipeline:
        lost = data.outcome_reasons(bundle.leads, "Lost")
        ctx["lead_sheet"] = {"leads_by_current_stage": pipeline["by_stage"],
                             "recency_measured_as_of": data.latest_activity(bundle.leads, today).isoformat(),
                             "lost_reasons": lost.to_dict() if lost is not None else {}}
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


SHORT_STAGE = {"Total Leads": "Leads", "Qualified Leads": "Qualified", "Viewings Scheduled": "Viewings booked",
               "Viewings Completed": "Viewings done", "Offers Made": "Offers", "Offers Accepted": "Accepted",
               "Closed Sales": "Closed"}


def render_overview(metrics, prev, totals, temp, spend, pipeline):
    total, qualified = metrics["Total Leads"], metrics["Qualified Leads"]
    closed, viewings = metrics["Closed Sales"], metrics["Viewings Completed"]
    active = data.active_stages(metrics)
    prev = prev or {}

    avg = f"{total / len(totals):.1f}/day · " if totals is not None and len(totals) else ""
    kpis = [("Leads", f"{total:,}", avg + change_note(total, prev.get("Total Leads"))),
            ("Qualified", f"{data.pct(qualified, total):.1f}%", f"{qualified:,} leads")]
    if "Closed Sales" in active:
        kpis += [("Viewings", f"{viewings:,}", f"{data.pct(viewings, qualified):.0f}% of qualified"),
                 ("Closed sales", f"{closed:,}", change_note(closed, prev.get("Closed Sales"))
                  or f"{data.pct(closed, total):.1f}% close rate"),
                 ("Close rate", f"{data.pct(closed, total):.2f}%", f"target {brand.targets.get('Close Rate', 0)}%")]
    elif pipeline:
        stages = pipeline["by_stage"]
        lost, new = stages.get("Lost", 0), stages.get("New", 0)
        kpis += [("Contacted", f"{pipeline['total'] - new:,}", f"{data.pct(pipeline['total'] - new, total):.0f}% of leads"),
                 ("Lost", f"{lost:,}", f"{data.pct(lost, total):.0f}% of leads"),
                 ("Still open", f"{total - lost:,}", f"{data.pct(total - lost, total):.0f}% of leads")]
    if spend:
        kpis.append(("Cost per lead", f"{brand.currency}{spend / total:,.0f}" if total else "–",
                     f"{brand.currency}{spend / closed:,.0f} per sale" if closed else ""))
    else:
        kpis.append(("Lead quality", f"{temp['quality_score']:.2f} / 3", "weighted Hot/Warm/Cold"))
    for col, (label, value, note) in zip(st.columns(len(kpis)), kpis):
        with col:
            ui.kpi(label, value, note)

    st.markdown("#### Funnel at a glance")
    chips = [(SHORT_STAGE[stage], metrics[stage],
              data.pct(metrics[active[i + 1]], metrics[stage]) if i + 1 < len(active) else None)
             for i, stage in enumerate(active)]
    last = active[-1]
    ui.flow(chips, final=("Close rate", f"{data.pct(closed, total):.1f}%") if last == "Closed Sales"
            else (f"{SHORT_STAGE[last]} rate", f"{data.pct(metrics[last], total):.1f}%"))
    section_insight("overview")

    st.markdown("#### Priority actions")
    cached = st.session_state.get("insights")
    if cached and cached["key"] == st.session_state.get("context_key"):
        for i, action in enumerate(cached["data"].get("actions", [])[:3], 1):
            st.markdown(f"**{i}.** {action}")
    else:
        st.caption("Generate AI insights (top right) to get this week's three highest-impact actions.")


def render_targets(metrics):
    active = data.active_stages(metrics)
    actuals = {"Qualification Rate": data.pct(metrics["Qualified Leads"], metrics["Total Leads"])}
    if "Offers Made" in active:
        actuals["Viewing → Offer"] = data.pct(metrics["Offers Made"], metrics["Viewings Completed"])
    if "Closed Sales" in active:
        actuals["Close Rate"] = data.pct(metrics["Closed Sales"], metrics["Total Leads"])
    lines = []
    for name, target in brand.targets.items():
        value = actuals.get(name)
        if value is not None:
            lines.append(f"{'✅' if value >= float(target) else '⚠️'} **{name}**: {value:.1f}% (target {target}%)")
    if lines:
        st.markdown("#### Targets")
        st.markdown("\n\n".join(lines))


def render_funnel(metrics, steps, leads):
    active = data.active_stages(metrics)
    section_insight("funnel")
    left, right = st.columns([3, 2])
    with left:
        fig = go.Figure(go.Funnel(
            y=active, x=[metrics[s] for s in active],
            textinfo="value+percent initial",
            marker={"color": [brand.primary_color, brand.secondary_color, "#9f7aea", "#4facfe",
                              "#00b8d9", "#38b2ac", ui.GOOD][:len(active)]},
            connector={"line": {"color": "rgba(128,128,128,.4)", "dash": "dot"}},
        ))
        ui.chart(fig, "funnel", height=max(200, 70 * len(active)), legend=False)
    with right:
        colors = [ui.BAD if s["rate"] < 30 else ui.WARM if s["rate"] < 70 else ui.GOOD for s in steps]
        fig = go.Figure(go.Bar(
            x=[s["rate"] for s in steps], y=[s["stage"] for s in steps], orientation="h",
            marker_color=colors, text=[f"{s['rate']:.0f}%" for s in steps], textposition="outside",
            hovertemplate="%{y}: %{x:.1f}%<extra></extra>",
        ))
        fig.update_layout(title="Step conversion (red < 30% · amber 30–70% · green > 70%)",
                          xaxis=dict(range=[0, 110], title=None), yaxis=dict(autorange="reversed"))
        ui.chart(fig, "step_rates", height=max(200, 70 * len(active)), legend=False)

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
    render_lead_outcomes(leads, active)


def reason_chart(reasons, title, key, color):
    top = reasons.head(8).sort_values()
    fig = go.Figure(go.Bar(x=top.values, y=top.index, orientation="h", marker_color=color,
                           text=top.values, textposition="outside"))
    fig.update_layout(title=title, xaxis=dict(title=None), yaxis=dict(title=None))
    ui.chart(fig, key, height=max(220, 44 * len(top) + 80), legend=False)


def render_lead_outcomes(leads, active):
    """Where leads are now and why they were lost, from the lead-level sheet."""
    pipeline = data.lead_pipeline(leads)
    if not pipeline:
        return
    st.divider()
    st.markdown("### Where leads are now")
    if len(active) < len(data.FUNNEL_STAGES):
        st.caption("The sheet only tracks the early stages of the pipeline, so the funnel above stops at "
                   f"**{active[-1]}**. Later stages appear automatically once leads reach them.")
    stages = pipeline["by_stage"]
    colors = {"Lost": ui.BAD, "Closed": ui.GOOD}
    fig = go.Figure(go.Bar(x=list(stages), y=list(stages.values()), text=list(stages.values()),
                           textposition="outside",
                           marker_color=[colors.get(st_, brand.primary_color) for st_ in stages]))
    fig.update_layout(title="Leads by current stage", yaxis=dict(title=None))
    left, right = st.columns(2)
    with left:
        ui.chart(fig, "lead_stage_mix", height=320, legend=False)
    lost = data.outcome_reasons(leads, "Lost")
    with right:
        if lost is not None:
            reason_chart(lost, "Why leads were lost", "lost_reasons", ui.BAD)
    contacted = data.outcome_reasons(leads, "Contacted")
    if contacted is not None:
        reason_chart(contacted, "Latest outcome of contacted leads", "contacted_reasons", brand.primary_color)


def render_scoring(temp, scored, ai_scored, as_of, today):
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
    if as_of != today:
        st.caption(f"Recency is measured as of **{as_of:%d %b %Y}**, the latest activity in the Leads sheet, "
                   f"so months-old leads are not all marked Cold. Today is {today:%d %b %Y}.")

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

    st.markdown("#### Open leads by stage")
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
                                                "data": ai.score_leads(brand, lead_records(scored), as_of)}
                    st.rerun()
                except ai.AIError as e:
                    st.error(str(e))

    by_stage = (scored.groupby(["Stage", "Temperature"]).size().unstack(fill_value=0)
                .reindex(columns=["Hot", "Warm", "Cold"], fill_value=0))
    order = [st_ for st_ in list(data.STAGE_POINTS) if st_ in by_stage.index]
    by_stage = by_stage.loc[order]
    fig = go.Figure()
    for label, color in (("Hot", ui.HOT), ("Warm", ui.WARM), ("Cold", ui.COLD)):
        fig.add_bar(x=by_stage.index, y=by_stage[label], name=label, marker_color=color)
    fig.update_layout(barmode="stack", title="Hot, Warm and Cold leads at each stage")
    ui.chart(fig, "scoring_by_stage", height=340)

    if "Source" in scored.columns and scored["Source"].notna().any():
        by_source = (scored.groupby(["Source", "Temperature"]).size().unstack(fill_value=0)
                     .reindex(columns=["Hot", "Warm", "Cold"], fill_value=0))
        by_source["Hot share"] = (by_source["Hot"] / by_source.sum(axis=1) * 100).round(0)
        st.markdown("#### Lead temperature by source")
        st.dataframe(by_source.sort_values("Hot share", ascending=False).reset_index(), hide_index=True,
                     width="stretch",
                     column_config={"Hot share": st.column_config.NumberColumn("Hot share", format="%d%%")})


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
            shown = sources.drop(columns=[c for c in ("Closed", "Close %", "Spend", "Cost / Lead", "Hot leads")
                                          if c in sources.columns and not sources[c].fillna(0).any()])
            if shown["Quality Score"].nunique() <= 1:
                shown = shown.drop(columns="Quality Score")
            st.dataframe(
                shown, hide_index=True, width="stretch",
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


def render_trends(totals, scored):
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
        if scored is not None and "Date" in scored.columns and scored["Date"].notna().any():
            # Real data: today's temperature of the open leads, grouped by the week they arrived.
            weekly = (scored.assign(Week=scored["Date"].dt.to_period("W").dt.start_time)
                      .groupby(["Week", "Temperature"]).size().unstack(fill_value=0)
                      .reindex(columns=["Hot", "Warm", "Cold"], fill_value=0))
            for label, color in (("Hot", ui.HOT), ("Warm", ui.WARM), ("Cold", ui.COLD)):
                fig.add_bar(x=weekly.index, y=weekly[label], name=label, marker_color=color)
            fig.update_layout(barmode="stack", title="Open leads today, by the week they arrived")
            note = ("Each bar is the leads that arrived that week and are still open, coloured by their "
                    "current temperature. Older weeks with mostly Cold leads show where leads go quiet.")
        else:
            for label, color in (("Cold", ui.COLD), ("Warm", ui.WARM), ("Hot", ui.HOT)):
                fig.add_scatter(x=temps["Date"], y=temps[label], name=label, stackgroup="one",
                                line=dict(width=0.5, color=color))
            fig.update_layout(title="Estimated lead mix over time")
            note = ("Estimate: each day's funnel counts are split into Hot, Warm and Cold by rule "
                    "(see Lead Scoring). Add a Leads worksheet to see real per-lead data here.")
        ui.chart(fig, "trend_temperature", time_series=scored is None)
        st.caption(note)
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
        for warning in bundle.notes:
            st.warning(warning)

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
    pipeline = data.lead_pipeline(bundle.leads)
    as_of = data.latest_activity(bundle.leads, today)
    scored = data.score_leads(bundle.leads, as_of)
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

    tabs = st.tabs(["Overview", "Funnel", "Lead Scoring", "Channels", "Trends", "Ask AI"])
    with tabs[0]:
        render_overview(metrics, prev, totals, temp, spend, pipeline)
    with tabs[1]:
        render_funnel(metrics, steps, bundle.leads)
    with tabs[2]:
        render_scoring(temp, scored, ai_scored, as_of, today)
    with tabs[3]:
        render_channels(whatsapp_df, whatsapp, sources)
    with tabs[4]:
        render_trends(totals, scored)
    with tabs[5]:
        render_chat(context)

    ui.footer(brand, datetime.now().year)


main()
