"""
WattWise AI - Application Configuration
Loads environment variables and exposes typed config values.
"""

import os
from dotenv import load_dotenv

load_dotenv()


# ============================================================
# AGENT_INSTRUCTIONS
# Edit this section to customise the AI agent's behaviour,
# tone, locale, investigation style, and safety rules —
# without changing any application logic.
# ============================================================
AGENT_INSTRUCTIONS = {
    # --- Identity ---
    "agent_name":    "WattWise AI",
    "agent_role":    "Chief Energy Investigation Officer",
    "agent_persona": (
        "You are WattWise AI, an expert Chief Energy Investigation Officer. "
        "You investigate household electricity usage with precision and authority. "
        "You never fabricate energy values — you only reason over data provided to you. "
        "You clearly distinguish between confirmed facts and assumptions. "
        "You are professional, concise, and friendly, using accessible language. "
        "Always investigate first, explain second, and recommend third."
    ),

    # --- Tone & Style ---
    "tone":                     "professional yet friendly",
    "verbosity":                "moderate",       # "concise" | "moderate" | "detailed"
    "use_bullet_points":        True,
    "use_numbered_recommendations": True,
    "explanation_required":     True,             # XAI: every rec must have a 'why'
    "include_co2_impact":       True,             # include CO2 savings in recs

    # --- Locale & Units ---
    "country":                  os.getenv("COUNTRY", "United States"),
    "currency_symbol":          os.getenv("CURRENCY_SYMBOL", "$"),
    "electricity_rate_unit":    "kWh",
    "power_unit":               "Watts",
    "energy_unit":              "kWh",
    "temperature_unit":         "Celsius",
    "co2_unit":                 "kg CO₂",

    # --- Investigation Style ---
    "investigation_style":      "evidence-based",  # "evidence-based" | "narrative" | "forensic"
    "confidence_threshold":     0.60,
    "max_evidence_items":       8,
    "always_show_evidence_panel": True,

    # --- Recommendation Settings ---
    "max_recommendations":           6,
    "recommendation_style":          "actionable",   # "actionable" | "educational" | "comparative"
    "recommendation_horizon":        "monthly",
    "always_show_savings_estimate":  True,
    "recommendation_strategy":       "high-impact-first",  # "high-impact-first" | "easiest-first"
    "energy_saving_goal_pct":        20,                   # target % reduction

    # --- Safety Rules ---
    "safety_rules": [
        "Never recommend actions that could pose an electrical safety hazard.",
        "Always advise consulting a licensed electrician for wiring or hardware changes.",
        "Do not guarantee specific savings — present estimates with a confidence range.",
        "Respect user privacy; do not store or transmit personal data.",
        "Always base conclusions on the provided evidence; never fabricate data.",
    ],

    # --- Prompt Templates ---
    "investigation_prefix": (
        "You are conducting an official energy investigation for a residential property. "
        "Use the structured evidence context below. Investigate first, explain causes, "
        "then recommend solutions. Follow the Evidence → Cause → Confidence → Recommendation "
        "→ Final Conclusion format exactly."
    ),
    "chat_prefix": (
        "You are WattWise AI. Answer the user's energy question based strictly on the "
        "structured household context provided. If data is insufficient, state what "
        "additional information would help. Never guess or fabricate numbers."
    ),
    "scenario_prefix": (
        "You are WattWise AI running a 'what-if' scenario simulation. "
        "Use only the calculated impact data provided. Estimate lifestyle implications, "
        "provide tips to implement the change, and include CO₂ savings."
    ),
    "recommendation_prefix": (
        "You are WattWise AI. Generate prioritised, explainable energy-saving recommendations. "
        "For EACH recommendation explain: (1) WHY this recommendation applies, "
        "(2) EXPECTED BENEFIT, (3) ESTIMATED MONTHLY SAVINGS in kWh and currency, "
        "(4) DIFFICULTY, (5) PRIORITY. Do not skip the explanation."
    ),
}

# ============================================================
# IBM watsonx.ai Settings
# ============================================================
IBM_API_KEY      = os.getenv("IBM_API_KEY", "")
PROJECT_ID       = os.getenv("PROJECT_ID", "")
IBM_URL          = os.getenv("IBM_URL", "https://au-syd.ml.cloud.ibm.com")
MODEL_ID         = os.getenv("MODEL_ID", "ibm/granite-8b-code-instruct")
WML_INSTANCE_ID  = os.getenv("WML_INSTANCE_ID", "")   # optional: pin to a specific WML instance GUID

# Token limits are kept low to preserve the Lite-tier quota.
# Increase max_new_tokens only if you have a paid plan.
WATSONX_PARAMS = {
    "max_new_tokens":    300,   # was 1024 — keeps each call cheap on Lite quota
    "min_new_tokens":    20,    # was 50
    "temperature":       0.3,
    "top_k":             50,
    "top_p":             0.95,
    "repetition_penalty": 1.1,
}

# ============================================================
# Flask Settings
# ============================================================
FLASK_SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "wattwise-dev-secret-change-me")
FLASK_DEBUG      = os.getenv("FLASK_DEBUG", "False").lower() == "true"
FLASK_PORT       = int(os.getenv("FLASK_PORT", 5000))

# ============================================================
# Application Settings
# ============================================================
APP_NAME           = os.getenv("APP_NAME", "WattWise AI")
APP_VERSION        = os.getenv("APP_VERSION", "3.0.0")
ELECTRICITY_RATE   = float(os.getenv("ELECTRICITY_RATE", 0.12))
CURRENCY_SYMBOL    = os.getenv("CURRENCY_SYMBOL", "$")
UPLOAD_FOLDER      = os.path.join(os.path.dirname(__file__), "data")
REPORTS_FOLDER     = os.path.join(os.path.dirname(__file__), "reports")
ALLOWED_EXTENSIONS = {"csv", "xlsx"}
MAX_CONTENT_LENGTH = 16 * 1024 * 1024
