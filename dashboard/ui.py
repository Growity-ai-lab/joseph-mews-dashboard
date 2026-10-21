"""Styling and small rendering helpers shared by the dashboard tabs."""
import html

import streamlit as st

HOT, WARM, COLD = "#ef4444", "#f59e0b", "#3b82f6"
GOOD, BAD = "#10b981", "#ef4444"
TEMPERATURE_COLORS = {"Hot": HOT, "Warm": WARM, "Cold": COLD}


def rgba(hex_color, alpha):
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r}, {g}, {b}, {alpha})"


def inject_css(brand):
    p, s, a = brand.primary_color, brand.secondary_color, brand.accent_color
    st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
html, body, [class*="css"], .stMarkdown, button, input {{ font-family: 'Inter', sans-serif; }}
[data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"] {{ display: none; }}
.block-container {{ padding-top: 4.2rem; padding-bottom: 2rem; max-width: 1400px; }}
h3 {{ font-size: 1.15rem !important; margin: .4rem 0 .4rem !important; }}
h4 {{ font-size: 1rem !important; margin: .3rem 0 .3rem !important; }}

.jm-header {{ display: flex; justify-content: space-between; align-items: flex-end; flex-wrap: wrap;
  gap: .75rem; padding-bottom: .8rem; margin-bottom: .8rem; border-bottom: 1px solid rgba(128,128,128,.2); }}
.jm-brand {{ display: flex; align-items: center; gap: .8rem; }}
.jm-brand img {{ height: 42px; }}
.jm-name {{ font-size: 1.85rem; font-weight: 700; letter-spacing: .5px; line-height: 1.35; padding: .15em 0 .05em;
  background: linear-gradient(135deg, {a} 0%, {rgba(a, .75)} 100%);
  -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; }}
.jm-tagline {{ font-size: .9rem; opacity: .7; }}
.jm-meta {{ text-align: right; font-size: .8rem; opacity: .8; line-height: 1.6; }}
.jm-badge {{ display: inline-block; padding: .1rem .55rem; border-radius: 999px; font-size: .7rem;
  font-weight: 600; background: {rgba(p, .14)}; color: {p}; }}
.jm-badge.demo {{ background: {rgba(a, .18)}; color: #b7791f; }}

.jm-kpi {{ border: 1px solid rgba(128,128,128,.22); border-radius: 12px; padding: .8rem 1rem;
  background: rgba(128,128,128,.05); height: 100%; }}
.jm-kpi-label {{ font-size: .68rem; text-transform: uppercase; letter-spacing: .6px; opacity: .7; }}
.jm-kpi-value {{ font-size: 1.55rem; font-weight: 700; margin-top: .15rem; }}
.jm-kpi-note {{ font-size: .75rem; opacity: .7; }}

.jm-flow {{ display: flex; flex-wrap: wrap; align-items: center; gap: .4rem; margin: .4rem 0 .8rem; }}
.jm-step {{ flex: 1 1 110px; border-radius: 10px; padding: .55rem .85rem; color: white; text-align: center; min-width: 110px;
  background: linear-gradient(135deg, {rgba(p, .95)} 0%, {rgba(s, .95)} 100%); }}
.jm-step.final {{ background: linear-gradient(135deg, #10b981 0%, #0ea5a4 100%); }}
.jm-step-label {{ font-size: .62rem; text-transform: uppercase; letter-spacing: .5px; opacity: .9; }}
.jm-step-value {{ font-size: 1.25rem; font-weight: 700; }}
.jm-status {{ flex: 1 1 130px; border: 1px solid; border-radius: 10px; padding: .6rem .85rem; }}
.jm-status-value {{ font-size: 1.5rem; font-weight: 700; line-height: 1.2; }}
.jm-status-note {{ font-size: .72rem; opacity: .7; margin-bottom: .35rem; }}
.jm-status-bar {{ height: 4px; border-radius: 2px; background: rgba(128,128,128,.2); overflow: hidden; }}
.jm-status-bar div {{ height: 100%; border-radius: 2px; }}
.jm-arrow {{ font-size: .75rem; font-weight: 700; color: {p}; text-align: center; min-width: 46px; }}

.jm-insight {{ border-left: 4px solid {p}; background: {rgba(p, .07)}; border-radius: 10px;
  padding: .7rem 1rem; margin: .2rem 0 1rem; font-size: .92rem; line-height: 1.55; }}
.jm-insight b {{ color: {p}; }}

.jm-temp {{ border-radius: 12px; padding: .8rem 1rem; text-align: center; border: 1px solid rgba(128,128,128,.2); }}
.jm-temp-label {{ font-size: .68rem; text-transform: uppercase; letter-spacing: .6px; font-weight: 600; }}
.jm-temp-value {{ font-size: 1.6rem; font-weight: 700; }}
.jm-temp-note {{ font-size: .75rem; opacity: .8; }}

.jm-footer {{ text-align: center; font-size: .78rem; opacity: .6; margin-top: 2rem; padding-top: 1rem;
  border-top: 1px solid rgba(128,128,128,.2); }}
</style>
""", unsafe_allow_html=True)


def esc(text):
    return html.escape(str(text))


def header(brand, period_label, loaded_at, source):
    logo = f'<img src="{esc(brand.logo_url)}" alt="">' if brand.logo_url else ""
    badge = ('<span class="jm-badge demo">Demo data</span>' if source == "demo"
             else '<span class="jm-badge">Live · Google Sheets</span>')
    st.markdown(f"""
<div class="jm-header">
  <div class="jm-brand">{logo}<div>
    <div class="jm-name">{esc(brand.name)}</div>
    <div class="jm-tagline">{esc(brand.tagline)}</div>
  </div></div>
  <div class="jm-meta">{badge}<br>
    Reporting period: <b>{esc(period_label)}</b><br>
    Updated {loaded_at:%d %b %Y, %H:%M}
  </div>
</div>""", unsafe_allow_html=True)


def kpi(label, value, note=""):
    st.markdown(f"""<div class="jm-kpi"><div class="jm-kpi-label">{esc(label)}</div>
<div class="jm-kpi-value">{esc(value)}</div><div class="jm-kpi-note">{esc(note)}</div></div>""",
                unsafe_allow_html=True)


def flow(steps, final=None):
    """Horizontal stage chips. steps: [(label, value, conversion % to the next chip or None), ...]."""
    parts = []
    for i, (label, value, rate) in enumerate(steps):
        parts.append(f'<div class="jm-step"><div class="jm-step-label">{esc(label)}</div>'
                     f'<div class="jm-step-value">{value:,}</div></div>')
        if i < len(steps) - 1 or final:
            parts.append(f'<div class="jm-arrow">→<br>{rate:.0f}%</div>' if rate is not None
                         else '<div class="jm-arrow">→</div>')
    if final:
        label, value = final
        parts.append(f'<div class="jm-step final"><div class="jm-step-label">{esc(label)}</div>'
                     f'<div class="jm-step-value">{esc(value)}</div></div>')
    st.markdown(f'<div class="jm-flow">{"".join(parts)}</div>', unsafe_allow_html=True)


def status_row(items, total):
    """Row of tinted status cards: [(label, count, color), ...] with each count's share of `total`."""
    cards = "".join(
        f'<div class="jm-status" style="border-color:{rgba(color, .55)};background:{rgba(color, .10)}">'
        f'<div class="jm-step-label">{esc(label)}</div>'
        f'<div class="jm-status-value" style="color:{color}">{count:,}</div>'
        f'<div class="jm-status-note">{count / total * 100:.0f}% of leads</div>'
        f'<div class="jm-status-bar"><div style="width:{count / total * 100:.1f}%;background:{color}"></div></div>'
        f'</div>' for label, count, color in items)
    st.markdown(f'<div class="jm-flow">{cards}</div>', unsafe_allow_html=True)


def insight(text, title="AI insight"):
    if text:
        st.markdown(f'<div class="jm-insight"><b>{esc(title)}</b> · {esc(text)}</div>', unsafe_allow_html=True)


def temperature_card(label, count, share, note, color):
    st.markdown(f"""<div class="jm-temp" style="background:{rgba(color, .08)}">
<div class="jm-temp-label" style="color:{color}">{esc(label)}</div>
<div class="jm-temp-value" style="color:{color}">{esc(count)}</div>
<div class="jm-temp-note">{esc(share)}</div><div class="jm-temp-note">{esc(note)}</div></div>""",
                unsafe_allow_html=True)


def chart(fig, key, height=300, legend=True, time_series=False):
    fig.update_layout(
        height=height,
        margin=dict(l=8, r=8, t=36, b=8),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif", size=12),
        title_font=dict(size=13),
        showlegend=legend,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode="x unified" if time_series else "closest",
    )
    st.plotly_chart(fig, key=key, width="stretch", config={"displayModeBar": False})


def footer(brand, year):
    st.markdown(f"""<div class="jm-footer">GDPR compliant · aggregated metrics and pseudonymous lead IDs only<br>
{esc(brand.name)} © {year} · All rights reserved</div>""", unsafe_allow_html=True)
