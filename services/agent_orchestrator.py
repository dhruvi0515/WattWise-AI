"""
WattWise AI - Agent Orchestrator
====================================
Central coordinator for all agentic AI workflows.

Workflow:
  User Query
      → Intent Detection
      → Data Analysis Agent    (enrich analysis)
      → Context Builder        (structured evidence)
      → Investigation Agent    (evidence ranking, causes, confidence)
      → Recommendation Agent   (prioritised, explainable recs)
      → IBM watsonx.ai         (reasoning + narrative)
      → Report Agent           (final document assembly)
      → Response Formatter     (structured output for routes)

No route calls watsonx.ai directly. All AI calls go through here.
"""

import re
from typing import Dict, Any, Optional

from services.energy_analyzer    import EnergyAnalyzer
from services.watsonx_service    import WatsonxService
from services.context_builder    import ContextBuilder
from services.session_memory     import SessionMemory
from services.agents             import (
    DataAnalysisAgent,
    InvestigationAgent,
    RecommendationAgent,
    ReportAgent,
)


# ---------------------------------------------------------------------------
# Intent taxonomy
# ---------------------------------------------------------------------------
INTENT_PATTERNS = {
    "investigate": [
        r"\bwhy\b", r"\bcause\b", r"\breason\b", r"\binvestigat",
        r"high bill", r"increased", r"spike", r"expensive",
        r"what.s wrong", r"too much", r"help me understand",
    ],
    "scenario": [
        r"\bwhat if\b", r"\bif i\b", r"\bif I reduce\b", r"\bif I switch\b",
        r"\bwhat happens if\b", r"\bsimulat", r"\bwhat would happen",
    ],
    "recommend": [
        r"\btips?\b", r"\bsave\b", r"\breaduce\b", r"\bimprove\b",
        r"\bsuggest", r"\badvice\b", r"\bbest way\b", r"\bhow can i\b",
        r"\bhow to\b", r"\boptimis", r"\boptimiz",
    ],
    "question": [
        r"\bwhich\b", r"\bwhat\b", r"\bhow much\b", r"\bhow many\b",
        r"\bwhen\b", r"\bshow me\b", r"\btell me\b", r"\bexplain\b",
    ],
}


class AgentOrchestrator:
    """
    Single entry point for all AI-powered operations.
    Routes each request through the appropriate agent pipeline.
    """

    def __init__(self):
        self.wx      = WatsonxService()
        self.ctx     = ContextBuilder()
        self.data_a  = DataAnalysisAgent()
        self.inv_a   = InvestigationAgent()
        self.rec_a   = RecommendationAgent()
        self.rep_a   = ReportAgent()

    @property
    def is_ready(self) -> bool:
        return self.wx.is_ready

    # ====================================================================
    # Intent Detection
    # ====================================================================
    def detect_intent(self, text: str) -> str:
        """
        Classify user query into one of: investigate | scenario | recommend | question
        Defaults to 'question'.
        """
        tl = text.lower()
        for intent, patterns in INTENT_PATTERNS.items():
            for pat in patterns:
                if re.search(pat, tl):
                    return intent
        return "question"

    # ====================================================================
    # Main pipeline: handle any user message
    # ====================================================================
    def handle_message(
        self,
        message:        str,
        raw_analysis:   Dict[str, Any],
        memory:         SessionMemory,
        electricity_rate: float,
    ) -> Dict[str, Any]:
        """
        Full orchestration pipeline for chat messages.
        Returns a structured response dict consumed by the route layer.
        """
        # 1. Enrich analysis
        analysis = self.data_a.enrich(raw_analysis.copy())

        # 2. Detect intent
        intent = self.detect_intent(message)

        # 3. Extract profile hints from message
        memory.extract_and_store_hints(message)
        user_profile = memory.build_context_dict()

        # 4. Build structured context (never raw CSV)
        context_text = self.ctx.build(
            analysis       = analysis,
            user_question  = message,
            session_memory = user_profile,
        )

        # 5. Route through specialist pipeline
        report     = None
        structured_recs = []
        investigation   = {}

        if intent == "investigate":
            investigation     = self.inv_a.analyse(analysis)
            structured_recs   = self.rec_a.generate(analysis)
            ai_narrative      = self.wx.investigate(message, context_text)
            report            = self.rep_a.assemble(
                user_question   = message,
                analysis        = analysis,
                investigation   = investigation,
                recommendations = structured_recs,
                ai_narrative    = ai_narrative,
                session_memory  = user_profile,
            )
            ai_response = ai_narrative

        elif intent == "scenario":
            ai_response = self.wx.simulate_scenario(message, {}, context_text)

        elif intent == "recommend":
            structured_recs   = self.rec_a.generate(analysis)
            ai_response       = self.wx.generate_recommendations(context_text)

        else:  # question / fallback
            history     = memory.get_recent_history(3)
            ai_response = self.wx.chat(message, context_text, history)

        # 6. Store message in memory
        memory.add_message("user",      message)
        memory.add_message("assistant", ai_response)

        return {
            "intent":            intent,
            "ai_response":       ai_response,
            "report":            report,
            "investigation":     investigation,
            "structured_recs":   structured_recs,
            "analysis":          analysis,
            "context_snapshot":  context_text[:400] + "…",
        }

    # ====================================================================
    # Explicit investigation (from button / route)
    # ====================================================================
    def run_investigation(
        self,
        question:      str,
        raw_analysis:  Dict[str, Any],
        memory:        SessionMemory,
    ) -> Dict[str, Any]:
        """Full investigation pipeline, always produces a report."""
        analysis      = self.data_a.enrich(raw_analysis.copy())
        user_profile  = memory.build_context_dict()
        context_text  = self.ctx.build(
            analysis       = analysis,
            user_question  = question,
            session_memory = user_profile,
        )
        investigation   = self.inv_a.analyse(analysis)
        structured_recs = self.rec_a.generate(analysis)
        ai_narrative    = self.wx.investigate(question, context_text)
        report          = self.rep_a.assemble(
            user_question   = question,
            analysis        = analysis,
            investigation   = investigation,
            recommendations = structured_recs,
            ai_narrative    = ai_narrative,
            session_memory  = user_profile,
        )
        return {"report": report, "analysis": analysis}

    # ====================================================================
    # Recommendations only
    # ====================================================================
    def run_recommendations(
        self,
        raw_analysis: Dict[str, Any],
        memory:       SessionMemory,
    ) -> Dict[str, Any]:
        analysis       = self.data_a.enrich(raw_analysis.copy())
        user_profile   = memory.build_context_dict()
        context_text   = self.ctx.build(analysis, session_memory=user_profile)
        structured_recs = self.rec_a.generate(analysis)
        ai_text        = self.wx.generate_recommendations(context_text)
        return {
            "structured_recs": structured_recs,
            "ai_text":         ai_text,
            "analysis":        analysis,
        }

    # ====================================================================
    # Scenario simulation
    # ====================================================================
    def run_scenario(
        self,
        query:        str,
        raw_analysis: Dict[str, Any],
        scenario_data: Dict[str, Any],
        memory:       SessionMemory,
    ) -> Dict[str, Any]:
        analysis      = self.data_a.enrich(raw_analysis.copy())
        user_profile  = memory.build_context_dict()
        context_text  = self.ctx.build(analysis, session_memory=user_profile)
        ai_reasoning  = self.wx.simulate_scenario(query, scenario_data, context_text)
        return {"ai_reasoning": ai_reasoning, "analysis": analysis}

    # ====================================================================
    # Dashboard quick insights
    # ====================================================================
    def quick_insights(self, raw_analysis: Dict[str, Any]) -> str:
        analysis     = self.data_a.enrich(raw_analysis.copy())
        brief_ctx    = self.ctx.build_brief(analysis)
        return self.wx.generate_quick_insights(brief_ctx)

    # ====================================================================
    # Enrich analysis only (no AI call — for dashboard metrics)
    # ====================================================================
    def enrich_analysis(self, raw_analysis: Dict[str, Any]) -> Dict[str, Any]:
        return self.data_a.enrich(raw_analysis.copy())

    # ====================================================================
    # CSV validation helper
    # ====================================================================
    @staticmethod
    def validate_csv_stats(df, analysis: Dict) -> Dict[str, Any]:
        """Produce upload statistics and validation feedback."""
        import pandas as pd
        rows    = len(df)
        cols    = list(df.columns)
        missing = int(df.isnull().sum().sum())
        dup     = int(df.duplicated().sum())
        warnings = []

        if missing > 0:
            pct = round(missing / (rows * max(len(cols), 1)) * 100, 1)
            warnings.append(f"{missing} missing values detected ({pct}% of cells). Filled with column median/mode.")
        if dup > 0:
            warnings.append(f"{dup} duplicate rows removed automatically.")
        if rows < 5:
            warnings.append("Very few rows — results may not be representative.")
        if analysis.get("data_source") == "demo" or not analysis.get("appliances"):
            warnings.append("Column names not fully recognised. Partial analysis performed.")

        return {
            "rows":            rows,
            "columns":         cols,
            "missing_values":  missing,
            "duplicate_rows":  dup,
            "warnings":        warnings,
            "quality_score":   max(0, 100 - missing - dup * 2 - (10 if rows < 5 else 0)),
        }
