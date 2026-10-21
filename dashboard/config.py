"""White-label configuration.

Every client-facing detail (name, colours, currency, targets) comes from
brand.json and/or environment variables, so the same dashboard can be shown
in demos for different lead-generation clients without code changes.
"""
import json
import os
from dataclasses import dataclass, field, fields
from pathlib import Path


@dataclass(frozen=True)
class Brand:
    name: str = "Joseph Mews"
    tagline: str = "Lead Funnel Dashboard"
    industry: str = "luxury real estate"
    primary_color: str = "#667eea"
    secondary_color: str = "#764ba2"
    accent_color: str = "#F4B23E"
    logo_url: str = ""
    currency: str = "£"
    lead_id_prefix: str = "JM"
    # Targets shown on the Funnel tab, in percent
    targets: dict = field(default_factory=lambda: {
        "Qualification Rate": 30.0,
        "Viewing → Offer": 40.0,
        "Close Rate": 2.5,
    })
    # Lead temperature rules. Phrases are matched against the Last Message of open leads, ignoring case and
    # accents. Hot: stage Qualified or later, or a hot phrase. Warm: a Contacted lead with a warm phrase.
    # Everything else (New, no answer, unreachable, no recorded outcome) is Cold.
    lead_rules: dict = field(default_factory=lambda: {
        "hot_phrases": ["tuna arayacak"],
        "warm_phrases": ["bilgi", "tarih", "tekrar", "randevu"],
        "cold_phrases": ["cevap vermiyor", "ulasilamadi", "ulasilamiyor", "ulasamadik"],
    })


ENV_OVERRIDES = {
    "name": "BRAND_NAME",
    "tagline": "BRAND_TAGLINE",
    "industry": "BRAND_INDUSTRY",
    "primary_color": "BRAND_PRIMARY_COLOR",
    "secondary_color": "BRAND_SECONDARY_COLOR",
    "accent_color": "BRAND_ACCENT_COLOR",
    "logo_url": "BRAND_LOGO_URL",
    "currency": "BRAND_CURRENCY",
    "lead_id_prefix": "BRAND_LEAD_ID_PREFIX",
}


def load_brand() -> Brand:
    """brand.json (or the file named by BRAND_CONFIG) first, then env var overrides."""
    values = {}
    config_path = Path(os.getenv("BRAND_CONFIG", "brand.json"))
    if config_path.is_file():
        with config_path.open(encoding="utf-8") as f:
            raw = json.load(f)
        known = {f.name for f in fields(Brand)}
        values.update({k: v for k, v in raw.items() if k in known})

    for attr, env_name in ENV_OVERRIDES.items():
        if os.getenv(env_name):
            values[attr] = os.getenv(env_name)

    return Brand(**values)
