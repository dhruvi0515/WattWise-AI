"""
WattWise AI - Investigation Report Service
Builds structured JSON investigation reports that combine
deterministic analysis with AI-generated reasoning.
"""

import uuid, json
from datetime import datetime
from typing import Dict, Any, List


class InvestigationService:
    """
    Composes a professional Investigation Report from:
      - energy analysis data  (deterministic, from EnergyAnalyzer)
      - AI reasoning text     (from WatsonxService)
    """

    # ------------------------------------------------------------------
    # Main report builder
    # ------------------------------------------------------------------
    def build_report(
        self,
        user_question: str,
        analysis:      Dict[str, Any],
        ai_narrative:  str,
    ) -> Dict[str, Any]:
        """
        Return a structured report dict ready for JSON serialisation
        and template rendering.
        """
        case_id      = self._generate_case_id()
        timestamp    = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        evidence     = self._collect_evidence(analysis)
        causes       = self._infer_causes(analysis)
        confidence   = self._determine_confidence(analysis)
        savings      = self._estimate_savings(analysis)

        report = {
            "case_id":           case_id,
            "timestamp":         timestamp,
            "user_question":     user_question,
            "investigation_summary": self._build_summary(analysis),
            "evidence_collected":    evidence,
            "primary_cause":         causes["primary"],
            "secondary_causes":      causes["secondary"],
            "confidence_level":      confidence["level"],
            "confidence_score":      confidence["score"],
            "confidence_reason":     confidence["reason"],
            "ai_narrative":          ai_narrative,
            "recommendations":       self._extract_recommendations(ai_narrative),
            "estimated_monthly_savings": savings,
            "data_source":           analysis.get("data_source", "unknown"),
            "total_monthly_kwh":     analysis.get("total_monthly_kwh"),
            "total_monthly_cost":    analysis.get("total_monthly_cost"),
            "top_appliance":         analysis.get("top_appliance"),
            "peak_hour_label":       analysis.get("peak_hour_label"),
            "currency":              analysis.get("currency", "$"),
        }
        return report

    # ------------------------------------------------------------------
    # Evidence collection
    # ------------------------------------------------------------------
    def _collect_evidence(self, analysis: Dict[str, Any]) -> List[Dict]:
        evidence = []
        kwh   = analysis.get("total_monthly_kwh", 0)
        cost  = analysis.get("total_monthly_cost", 0)
        rate  = analysis.get("electricity_rate", 0.12)
        cur   = analysis.get("currency", "$")

        evidence.append({
            "type":  "Total Consumption",
            "value": f"{kwh} kWh/month",
            "flag":  "high" if kwh > 900 else ("moderate" if kwh > 500 else "normal"),
        })
        evidence.append({
            "type":  "Estimated Bill",
            "value": f"{cur}{cost}/month",
            "flag":  "high" if cost > 150 else ("moderate" if cost > 80 else "normal"),
        })
        evidence.append({
            "type":  "Daily Average",
            "value": f"{analysis.get('daily_avg_kwh', 0)} kWh/day",
            "flag":  "normal",
        })
        evidence.append({
            "type":  "Peak Usage Hour",
            "value": analysis.get("peak_hour_label", "N/A"),
            "flag":  "info",
        })
        evidence.append({
            "type":  "Top Consuming Appliance",
            "value": analysis.get("top_appliance", "N/A"),
            "flag":  "high",
        })

        for a in analysis.get("top_3_appliances", []):
            pct = round((a.get("monthly_kwh", 0) / max(kwh, 1)) * 100, 1)
            evidence.append({
                "type":  f"Appliance — {a.get('appliance')}",
                "value": f"{a.get('monthly_kwh')} kWh/month ({pct}% of total)",
                "flag":  "high" if pct > 30 else "moderate",
            })
        return evidence

    # ------------------------------------------------------------------
    # Cause inference (rule-based)
    # ------------------------------------------------------------------
    def _infer_causes(self, analysis: Dict[str, Any]) -> Dict:
        appliances  = analysis.get("appliances", [])
        total_kwh   = analysis.get("total_monthly_kwh", 0)
        peak_hour   = analysis.get("peak_hour", 19)

        primary     = "Undetermined — insufficient data"
        secondary   = []

        if appliances:
            top = max(appliances, key=lambda a: a.get("monthly_kwh", 0))
            pct = round((top.get("monthly_kwh", 0) / max(total_kwh, 1)) * 100, 1)
            primary = (
                f"{top.get('appliance')} accounts for {pct}% of total monthly "
                f"consumption ({top.get('monthly_kwh')} kWh)"
            )

        if peak_hour in range(17, 22):
            secondary.append(
                f"Peak usage falls in the 5–10 PM evening window "
                f"({analysis.get('peak_hour_label')}), coinciding with peak tariff periods."
            )

        if total_kwh > 900:
            secondary.append(
                "Overall consumption exceeds the national average (~900 kWh/month) "
                "suggesting multiple high-draw appliances or extended usage hours."
            )

        ac = next((a for a in appliances
                   if "air condition" in a.get("appliance", "").lower()
                   or "ac" == a.get("appliance", "").lower()), None)
        if ac and ac.get("monthly_kwh", 0) > 200:
            secondary.append(
                f"Air conditioning alone consumes {ac.get('monthly_kwh')} kWh/month — "
                "consider thermostat scheduling or a more efficient unit."
            )

        wh = next((a for a in appliances
                   if "water heat" in a.get("appliance", "").lower()), None)
        if wh and wh.get("monthly_kwh", 0) > 100:
            secondary.append(
                f"Water heating contributes {wh.get('monthly_kwh')} kWh/month. "
                "Lowering the heater set-point or adding insulation could reduce this."
            )

        return {"primary": primary, "secondary": secondary}

    # ------------------------------------------------------------------
    # Confidence scoring (rule-based)
    # ------------------------------------------------------------------
    @staticmethod
    def _determine_confidence(analysis: Dict[str, Any]) -> Dict:
        score  = 0.5
        reason = []
        if analysis.get("data_source") == "csv":
            score += 0.2
            reason.append("User-uploaded CSV data used.")
        if analysis.get("appliances"):
            score += 0.1
            reason.append("Appliance-level breakdown available.")
        if analysis.get("monthly_trend"):
            score += 0.1
            reason.append("Multi-month trend data available.")
        if analysis.get("hourly_usage"):
            score += 0.1
            reason.append("Hourly usage profile available.")
        score = min(score, 1.0)
        level = "High" if score >= 0.8 else ("Medium" if score >= 0.6 else "Low")
        return {
            "level":  level,
            "score":  round(score, 2),
            "reason": "; ".join(reason) if reason else "Based on available data.",
        }

    # ------------------------------------------------------------------
    # Savings estimate (conservative heuristic)
    # ------------------------------------------------------------------
    @staticmethod
    def _estimate_savings(analysis: Dict[str, Any]) -> Dict:
        total_cost = analysis.get("total_monthly_cost", 0)
        cur        = analysis.get("currency", "$")
        # Conservative 15–25% savings assumption
        low  = round(total_cost * 0.15, 2)
        high = round(total_cost * 0.25, 2)
        return {
            "low":  f"{cur}{low}",
            "high": f"{cur}{high}",
            "note": "Estimated savings if top recommendations are implemented.",
        }

    # ------------------------------------------------------------------
    # Extract bullet recommendations from AI narrative
    # ------------------------------------------------------------------
    @staticmethod
    def _extract_recommendations(narrative: str) -> List[str]:
        recs  = []
        lines = narrative.split("\n")
        for line in lines:
            stripped = line.strip()
            if stripped and (
                stripped[0].isdigit()
                or stripped.startswith("•")
                or stripped.startswith("-")
                or stripped.lower().startswith("recommendation")
            ):
                clean = stripped.lstrip("0123456789.-•) ").strip()
                if len(clean) > 20:
                    recs.append(clean)
        return recs[:5] if recs else [
            "Review top consuming appliances and reduce idle usage.",
            "Shift high-load tasks to off-peak hours (before 5 PM or after 10 PM).",
            "Consider a smart thermostat for climate control optimisation.",
        ]

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _generate_case_id() -> str:
        short = str(uuid.uuid4()).replace("-", "").upper()[:10]
        return f"WW-{datetime.now().strftime('%Y%m%d')}-{short}"

    @staticmethod
    def _build_summary(analysis: Dict[str, Any]) -> str:
        src   = "uploaded CSV data" if analysis.get("data_source") == "csv" else "demo dataset"
        kwh   = analysis.get("total_monthly_kwh", 0)
        cost  = analysis.get("total_monthly_cost", 0)
        cur   = analysis.get("currency", "$")
        top   = analysis.get("top_appliance", "unknown appliance")
        peak  = analysis.get("peak_hour_label", "N/A")
        return (
            f"Investigation conducted on {src}. Household consumes {kwh} kWh per month "
            f"(estimated bill: {cur}{cost}). The highest consuming appliance is {top}. "
            f"Peak usage occurs at {peak}."
        )
