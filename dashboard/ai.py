"""Claude-powered features: section insights, executive report, chat and lead scoring."""
import json
import os

import streamlit as st

try:
    import anthropic
    SDK_AVAILABLE = True
except ImportError:
    SDK_AVAILABLE = False

MODEL = os.getenv("CLAUDE_MODEL", "claude-opus-5-5")
# If a safety classifier declines a request, the API re-runs it on Anthropic's
# recommended fallback model instead of returning a refusal.
FALLBACK_BETA = "server-side-fallback-2026-07-01"

INSIGHT_SECTIONS = ["overview", "funnel", "scoring", "channels", "trends", "forecast"]


class AIError(Exception):
    """A user-facing error from a Claude request."""


def is_configured():
    return SDK_AVAILABLE and bool(os.getenv("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_AUTH_TOKEN"))


@st.cache_resource(show_spinner=False)
def _client():
    return anthropic.Anthropic(timeout=180.0, max_retries=2)


def _request(system, messages, max_tokens, effort, schema=None):
    output_config = {"effort": effort}
    if schema:
        output_config["format"] = {"type": "json_schema", "schema": schema}
    return {
        "model": MODEL,
        "max_tokens": max_tokens,
        "system": system,
        "messages": messages,
        "output_config": output_config,
        "betas": [FALLBACK_BETA],
        "fallbacks": "default",
    }


def _friendly(error):
    if isinstance(error, anthropic.AuthenticationError):
        return "The Anthropic API key was rejected. Check ANTHROPIC_API_KEY."
    if isinstance(error, anthropic.RateLimitError):
        return "Claude is rate limited right now. Please try again in a minute."
    if isinstance(error, anthropic.APIConnectionError):
        return "Could not reach the Claude API. Check the network connection."
    if isinstance(error, anthropic.APIStatusError):
        return f"Claude API error ({error.status_code}): {error.message}"
    return f"Unexpected error from Claude: {error}"


def _check_stop(message):
    if message.stop_reason == "refusal":
        raise AIError("Claude declined this request. Try rephrasing it.")
    if message.stop_reason == "max_tokens":
        raise AIError("Claude's response was cut off before it finished. Please try again.")


def _json_call(system, prompt, schema, max_tokens, effort):
    try:
        with _client().beta.messages.stream(**_request(
                system, [{"role": "user", "content": prompt}], max_tokens, effort, schema)) as stream:
            message = stream.get_final_message()
    except anthropic.AnthropicError as e:
        raise AIError(_friendly(e)) from e
    _check_stop(message)
    text = next((b.text for b in message.content if b.type == "text"), "")
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise AIError("Claude returned an unexpected format. Please try again.") from e


def _text_stream(system, messages, max_tokens, effort):
    """Yield response text as it streams; raises AIError on failure."""
    try:
        with _client().beta.messages.stream(**_request(system, messages, max_tokens, effort)) as stream:
            yield from stream.text_stream
            message = stream.get_final_message()
    except anthropic.AnthropicError as e:
        raise AIError(_friendly(e)) from e
    if message.stop_reason == "refusal":
        yield "\n\n_Claude declined to answer this. Try rephrasing the question._"
    elif message.stop_reason == "max_tokens":
        yield "\n\n_(Response truncated.)_"


def _data_block(context):
    return f"<dashboard_data>\n{json.dumps(context, indent=1, default=str)}\n</dashboard_data>"


def generate_insights(brand, context):
    system = (
        f"You are the revenue analyst for {brand.name}, a {brand.industry} business. You write the short "
        "commentary shown under each section of their lead-funnel dashboard, read by the sales and marketing "
        "team. Ground every statement in the numbers provided: cite the figures that matter and say what they "
        "mean for the team and what to do. If a section has no data, say so in one sentence instead of guessing.\n\n"
        "Sections: overview (headline performance for the period), funnel (stage-by-stage conversion; call "
        "rates under 30% weak, 30-70% average, above 70% strong), scoring (lead quality and the Hot/Warm/Cold "
        "mix), channels (WhatsApp and lead sources), trends (direction over time), forecast (what the current "
        "rates imply and where improvement pays most). Each section is 2-3 sentences of plain text, no markdown. "
        "'actions' are the three highest-impact things to do this week, most important first, one sentence each."
    )
    schema = {
        "type": "object",
        "properties": {
            **{name: {"type": "string"} for name in INSIGHT_SECTIONS},
            "actions": {"type": "array", "items": {"type": "string"}},
        },
        "required": INSIGHT_SECTIONS + ["actions"],
        "additionalProperties": False,
    }
    return _json_call(system, _data_block(context), schema, max_tokens=6000, effort="low")


def stream_report(brand, context, today):
    system = (
        f"You write the executive lead-funnel report for the leadership team of {brand.name}, a "
        f"{brand.industry} business. Today is {today:%d %B %Y}. The report is downloaded and forwarded by "
        "email, so it must stand on its own: a title naming the reporting period, a short headline summary, "
        "then funnel performance, lead quality, channels, risks, and recommended next steps. Use the figures "
        f"from the data (currency {brand.currency}) and keep it to about one page of Markdown."
    )
    messages = [{"role": "user", "content": _data_block(context) + "\n\nWrite the report."}]
    return _text_stream(system, messages, max_tokens=8000, effort="medium")


def stream_chat(brand, context, history):
    system = (
        f"You answer questions about the lead-funnel dashboard of {brand.name}, a {brand.industry} business, "
        "for its sales and marketing team. Answer from the data below, quoting the relevant numbers. If the "
        "data can't answer the question, say so and name the data that would. Keep answers short and use "
        "Markdown only where it helps (a short list or table).\n\n" + _data_block(context)
    )
    messages = [{"role": m["role"], "content": m["content"]} for m in history]
    return _text_stream(system, messages, max_tokens=8000, effort="medium")


def score_leads(brand, leads, today):
    """Return {lead_id: {temperature, score, reason, next_action}} for the given lead records."""
    system = (
        f"You qualify inbound leads for {brand.name}, a {brand.industry} business. Today is {today:%d %B %Y}. "
        "For each lead, judge purchase intent from its funnel stage, how recently we were in contact, its "
        "budget band and, above all, what the lead last wrote to us. Hot = likely to transact in the next few "
        "weeks; Warm = genuinely interested but needs nurturing; Cold = low intent or gone quiet. Give a score "
        "from 0 to 100 consistent with the temperature. 'reason' is one short sentence citing the evidence; "
        "'next_action' is one concrete step for the agent. Return every lead you are given, using its lead_id."
    )
    schema = {
        "type": "object",
        "properties": {
            "leads": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "lead_id": {"type": "string"},
                        "temperature": {"type": "string", "enum": ["Hot", "Warm", "Cold"]},
                        "score": {"type": "integer"},
                        "reason": {"type": "string"},
                        "next_action": {"type": "string"},
                    },
                    "required": ["lead_id", "temperature", "score", "reason", "next_action"],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["leads"],
        "additionalProperties": False,
    }
    prompt = "<leads>\n" + "\n".join(json.dumps(lead, default=str) for lead in leads) + "\n</leads>"
    result = _json_call(system, prompt, schema, max_tokens=16000, effort="low")
    return {item["lead_id"]: item for item in result.get("leads", [])}
