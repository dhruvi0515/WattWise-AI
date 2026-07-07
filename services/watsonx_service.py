"""
WattWise AI - IBM watsonx.ai Service  (v2.1 — improved prompts)
================================================================
Manages authentication, prompt construction, and text generation.

Design contract
---------------
* This class NEVER receives raw DataFrames or CSV rows.
* All evidence arrives as a structured text summary from ContextBuilder.
* Every public method returns a plain string (the AI's text).
* On failure the service returns a user-friendly fallback — never an exception.
"""

import logging
from typing import Dict, Any, Optional

from config import (
    IBM_API_KEY, PROJECT_ID, IBM_URL, MODEL_ID,
    WATSONX_PARAMS, AGENT_INSTRUCTIONS, WML_INSTANCE_ID,
)

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Optional SDK import — graceful degradation if not installed
# ─────────────────────────────────────────────────────────────────────────────
try:
    from ibm_watsonx_ai import APIClient, Credentials
    from ibm_watsonx_ai.foundation_models import ModelInference
    from ibm_watsonx_ai.metanames import GenTextParamsMetaNames as GenParams
    _SDK_AVAILABLE = True
except ImportError:
    _SDK_AVAILABLE = False
    logger.warning("ibm-watsonx-ai SDK not installed — AI responses disabled.")


class WatsonxService:
    """
    Thin wrapper around the IBM watsonx.ai ModelInference API.

    Public interface
    ----------------
    is_ready                → bool
    generate(prompt)        → str
    investigate(...)        → str
    chat(...)               → str
    generate_recommendations(...)   → str
    simulate_scenario(...)          → str
    generate_quick_insights(...)    → str
    """

    def __init__(self) -> None:
        self._model: Optional[Any] = None
        self._ready = False
        self._connect()

    # ─────────────────────────────────────────────────────────────────────
    # Initialisation
    # ─────────────────────────────────────────────────────────────────────

    def _connect(self) -> None:
        """Attempt to connect to IBM watsonx.ai.  Failures are non-fatal."""
        if not _SDK_AVAILABLE:
            return
        if not IBM_API_KEY or not PROJECT_ID:
            logger.warning(
                "IBM_API_KEY or PROJECT_ID not set — AI responses will use fallback mode."
            )
            return
        try:
            credentials = Credentials(url=IBM_URL, api_key=IBM_API_KEY)
            # If a specific WML instance GUID is set, pin to it so IBM Cloud
            # doesn't accidentally route through a stale/inactive instance.
            client_kwargs = {}
            if WML_INSTANCE_ID:
                client_kwargs["instance_id"] = WML_INSTANCE_ID
            client      = APIClient(credentials, **client_kwargs)
            self._model = ModelInference(
                model_id   = MODEL_ID,
                api_client = client,
                project_id = PROJECT_ID,
                params     = {
                    GenParams.MAX_NEW_TOKENS    : WATSONX_PARAMS["max_new_tokens"],
                    GenParams.MIN_NEW_TOKENS    : WATSONX_PARAMS["min_new_tokens"],
                    GenParams.TEMPERATURE       : WATSONX_PARAMS["temperature"],
                    GenParams.TOP_K             : WATSONX_PARAMS["top_k"],
                    GenParams.TOP_P             : WATSONX_PARAMS["top_p"],
                    GenParams.REPETITION_PENALTY: WATSONX_PARAMS["repetition_penalty"],
                },
            )
            self._ready = True
            logger.info("WatsonxService connected — model: %s", MODEL_ID)
        except Exception as exc:
            logger.error("WatsonxService connection failed: %s", exc)

    @property
    def is_ready(self) -> bool:
        """Return True when a live connection to watsonx.ai is established."""
        return self._ready

    # ─────────────────────────────────────────────────────────────────────
    # Core generation
    # ─────────────────────────────────────────────────────────────────────

    def generate(self, prompt: str) -> str:
        """
        Send a prompt to watsonx.ai and return the generated text.
        Returns a friendly fallback string when the service is unavailable.
        """
        if not self._ready or self._model is None:
            return self._fallback_response()
        try:
            response = self._model.generate_text(prompt=prompt)
            text = response.strip() if isinstance(response, str) else str(response)
            return text or self._fallback_response()
        except Exception as exc:
            logger.error("watsonx.ai generation error: %s", exc)
            return (
                "The AI service returned an error. Your energy analysis is still available "
                "using the deterministic calculations below.\n\n"
                f"Technical detail: {str(exc)[:200]}"
            )

    # ─────────────────────────────────────────────────────────────────────
    # Domain methods — each builds a focused prompt and calls generate()
    # ─────────────────────────────────────────────────────────────────────

    def investigate(self, user_question: str, evidence_text: str) -> str:
        """
        Full investigation workflow.
        Returns a structured report narrative grounded in the evidence text.
        """
        ai      = AGENT_INSTRUCTIONS
        safety  = "\n".join(f"  • {r}" for r in ai["safety_rules"])
        rec_n   = ai["max_recommendations"]
        cur     = ai["currency_symbol"]
        country = ai["country"]

        prompt = f"""{ai['agent_persona']}

{ai['investigation_prefix']}

OPERATING RULES:
{safety}

INVESTIGATION PARAMETERS:
  Style    : {ai['investigation_style']}
  Country  : {country}
  Currency : {cur}

USER QUESTION:
{user_question}

ENERGY EVIDENCE (use only these facts — do not invent values):
{evidence_text}

REQUIRED OUTPUT FORMAT:
Use these exact section headings, in order:

## EVIDENCE REVIEW
Summarise the key facts from the energy data in 3–5 bullet points.

## CAUSE ANALYSIS
### Primary Cause
Identify the single most significant driver (one paragraph).
### Secondary Causes
List 2–3 contributing factors as bullet points.

## CONFIDENCE ASSESSMENT
State: Low / Medium / High — and explain in one sentence why.

## RECOMMENDATIONS
Provide exactly {rec_n} numbered recommendations.
For each write:
  • **Title**
  • _Why_: one sentence justification from the evidence
  • _Action_: specific, actionable step
  • _Estimated saving_: monthly kWh and {cur} amount

## FINAL CONCLUSION
One paragraph summarising findings and the projected impact of recommendations.

Keep the response concise and professional. Do NOT fabricate energy values."""
        return self.generate(prompt)

    def chat(
        self,
        user_message: str,
        evidence_text: str,
        conversation_history: list = None,
    ) -> str:
        """
        Conversational response grounded in household energy data.
        Includes recent conversation history for context continuity.
        """
        ai = AGENT_INSTRUCTIONS

        history_block = ""
        if conversation_history:
            lines = []
            for msg in conversation_history[-6:]:
                role = "User" if msg["role"] == "user" else "WattWise AI"
                lines.append(f"{role}: {msg['content'][:300]}")
            if lines:
                history_block = "\nCONVERSATION HISTORY:\n" + "\n".join(lines) + "\n"

        prompt = f"""{ai['agent_persona']}

{ai['chat_prefix']}

HOUSEHOLD ENERGY CONTEXT:
{evidence_text}
{history_block}
USER: {user_message}

Respond helpfully in 80–120 words. Use bullet points where appropriate. Be concise.
Ground every claim in the evidence above. If uncertain, say so clearly.

WattWise AI:"""
        return self.generate(prompt)

    def generate_recommendations(self, evidence_text: str) -> str:
        """
        Generate a prioritised, explainable recommendation list.
        Each recommendation must include a 'why' justification (XAI).
        """
        ai      = AGENT_INSTRUCTIONS
        rec_n   = ai["max_recommendations"]
        cur     = ai["currency_symbol"]
        horizon = ai["recommendation_horizon"]

        prompt = f"""{ai['agent_persona']}

{ai.get('recommendation_prefix', '')}

Based on the household energy evidence below, generate exactly {rec_n}
energy-saving recommendations in **{ai['recommendation_style']}** style,
sorted by priority (High first).

For each recommendation, use this structure:

### [Priority: High/Medium/Low] Recommendation Title

**Why this applies:** One sentence linking this recommendation to the evidence.

**Action:** Specific step the homeowner should take.

**Expected benefit:** Describe the lifestyle or comfort impact.

**Estimated {horizon} saving:**
  - Energy: X kWh
  - Cost  : {cur}X.XX
  - CO₂   : X kg

**Difficulty:** Easy / Medium / Hard
**Time required:** (e.g., "Immediate", "1 week", "1–3 months")

---

ENERGY EVIDENCE:
{evidence_text}

Recommendations (start with the highest priority):"""
        return self.generate(prompt)

    def simulate_scenario(
        self,
        scenario_desc: str,
        scenario_data: Dict[str, Any],
        evidence_text: str,
    ) -> str:
        """
        Reason over a 'what-if' scenario using pre-calculated impact data.
        The AI interprets the numbers — it does not recalculate them.
        """
        ai  = AGENT_INSTRUCTIONS
        cur = ai["currency_symbol"]

        # Build a compact impact summary for the prompt
        appliance   = scenario_data.get("appliance", "the appliance")
        direction   = scenario_data.get("direction", "reduction")
        hours       = abs(scenario_data.get("change_hours", 1))
        kwh_change  = scenario_data.get("monthly_kwh_change", 0)
        cost_change = scenario_data.get("monthly_cost_change", 0)
        annual_save = scenario_data.get("annual_cost_change", 0)
        pct         = scenario_data.get("percentage_saving", 0)

        prompt = f"""{ai['agent_persona']}

{ai['scenario_prefix']}

SCENARIO: {scenario_desc}

CALCULATED IMPACT (these numbers are exact — do not change them):
  Appliance       : {appliance}
  Change          : {direction} by {hours} hour(s)/day
  Monthly kWh     : {kwh_change} kWh {"saved" if direction == "reduction" else "added"}
  Monthly cost    : {cur}{cost_change} {"saved" if direction == "reduction" else "added"}
  Annual saving   : {cur}{annual_save}
  % of total bill : {pct}%

CURRENT HOUSEHOLD CONTEXT:
{evidence_text}

Please provide:

## IMPACT CONFIRMATION
Confirm the energy and cost impact in plain language (1–2 sentences).

## LIFESTYLE IMPLICATIONS
3–4 bullet points describing realistic changes to daily routine.

## IMPLEMENTATION TIPS
3 practical tips to make this change easier to sustain.

## CAVEATS & CONSIDERATIONS
Any important trade-offs, comfort impacts, or conditions to be aware of.

Keep the tone encouraging and practical."""
        return self.generate(prompt)

    def generate_quick_insights(self, evidence_brief: str) -> str:
        """
        Generate exactly 3 short, punchy dashboard insights.
        Uses the brief evidence summary from ContextBuilder.build_brief().
        """
        ai = AGENT_INSTRUCTIONS
        prompt = f"""{ai['agent_persona']}

You are providing a quick energy health check for a homeowner's dashboard.

HOUSEHOLD SNAPSHOT:
{evidence_brief}

Generate exactly 3 short insights (one sentence each).
Each insight should be immediately actionable or surprising.
Format:

**Insight 1:** [sentence]
**Insight 2:** [sentence]
**Insight 3:** [sentence]

Do not add any text before or after these three lines."""
        return self.generate(prompt)

    # ─────────────────────────────────────────────────────────────────────
    # Fallback
    # ─────────────────────────────────────────────────────────────────────

    @staticmethod
    def _fallback_response() -> str:
        return (
            "**AI Service Not Connected**\n\n"
            "IBM watsonx.ai is not configured for this session. "
            "To enable full AI investigation capabilities:\n\n"
            "1. Open the `.env` file in the project root\n"
            "2. Add your `IBM_API_KEY` and `PROJECT_ID`\n"
            "3. Restart the application\n\n"
            "All energy calculations, charts, and structured analysis are still "
            "fully functional and are computed locally by the Python engine."
        )
