"""
WattWise AI - Specialized AI Agents
Each agent has a single responsibility and produces structured output.
Agents do NOT call each other — the AgentOrchestrator coordinates them.

Agents:
  DataAnalysisAgent       – wrap EnergyAnalyzer results into typed output
  InvestigationAgent      – classify evidence, rank causes, score confidence
  RecommendationAgent     – produce prioritised, explainable recommendations
  ReportAgent             – assemble the final Investigation Report document
"""

import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional


# ============================================================================
# DATA ANALYSIS AGENT
# ============================================================================
class DataAnalysisAgent:
    """
    Responsibility: post-process raw EnergyAnalyzer output into
    a typed, enriched analysis dict.  Adds energy score, efficiency
    rating, CO2 estimate, and potential-savings metric.
    """

    # kg CO2 per kWh (US EPA average grid emission factor)
    CO2_PER_KWH = 0.386
    NATIONAL_AVERAGE_KWH = 900

    def enrich(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Add computed fields that downstream agents and templates consume."""
        kwh   = analysis.get("total_monthly_kwh", 0)
        cost  = analysis.get("total_monthly_cost", 0)
        rate  = analysis.get("electricity_rate", 0.12)

        analysis["monthly_co2_kg"]       = round(kwh * self.CO2_PER_KWH, 2)
        analysis["annual_co2_kg"]        = round(kwh * 12 * self.CO2_PER_KWH, 2)
        analysis["annual_cost"]          = round(cost * 12, 2)
        analysis["vs_national_avg_kwh"]  = round(kwh - self.NATIONAL_AVERAGE_KWH, 2)
        analysis["energy_score"]         = self._compute_score(kwh)
        analysis["efficiency_rating"]    = self._efficiency_rating(kwh)
        analysis["potential_savings_pct"]= self._potential_savings_pct(kwh)
        analysis["potential_savings_cost"]= round(cost * (analysis["potential_savings_pct"] / 100), 2)
        analysis["highest_cost_appliance"]= self._highest_cost_appliance(analysis)

        # Rank appliances by kWh
        apps = analysis.get("appliances", [])
        for a in apps:
            a["pct_of_total"] = round(
                (a.get("monthly_kwh", 0) / max(kwh, 1)) * 100, 1
            )
            a["co2_kg"] = round(a.get("monthly_kwh", 0) * self.CO2_PER_KWH, 2)
        apps_sorted = sorted(apps, key=lambda x: x.get("monthly_kwh", 0), reverse=True)
        analysis["appliances"] = apps_sorted
        analysis["top_3_appliances"] = apps_sorted[:3]

        return analysis

    # ------------------------------------------------------------------
    def _compute_score(self, kwh: float) -> int:
        """
        Score 0–100. Higher = more efficient.
        Below 600 kWh → excellent (90+); above 1400 kWh → poor (<30).
        """
        if kwh <= 400:   return 98
        if kwh <= 600:   return 90
        if kwh <= 800:   return 78
        if kwh <= 900:   return 70
        if kwh <= 1100:  return 58
        if kwh <= 1300:  return 44
        if kwh <= 1500:  return 32
        return 20

    def _efficiency_rating(self, kwh: float) -> str:
        score = self._compute_score(kwh)
        if score >= 85: return "Excellent"
        if score >= 70: return "Good"
        if score >= 55: return "Average"
        if score >= 40: return "Below Average"
        return "Poor"

    @staticmethod
    def _potential_savings_pct(kwh: float) -> int:
        """Conservative potential savings %."""
        if kwh <= 600:  return 8
        if kwh <= 900:  return 15
        if kwh <= 1200: return 22
        return 28

    @staticmethod
    def _highest_cost_appliance(analysis: Dict) -> str:
        apps = analysis.get("appliances", [])
        if not apps:
            return analysis.get("top_appliance", "N/A")
        top = max(apps, key=lambda a: a.get("monthly_cost", 0))
        return top.get("appliance", "N/A")


# ============================================================================
# INVESTIGATION AGENT
# ============================================================================
class InvestigationAgent:
    """
    Responsibility: Rank evidence items by severity, infer primary and
    secondary causes, and compute an overall confidence score.
    """

    def analyse(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Return an investigation payload: evidence, causes, confidence."""
        evidence   = self._build_evidence(analysis)
        causes     = self._infer_causes(analysis, evidence)
        confidence = self._score_confidence(analysis, evidence)
        return {
            "evidence_items": evidence,
            "primary_cause":  causes["primary"],
            "secondary_causes": causes["secondary"],
            "confidence_level": confidence["level"],
            "confidence_score": confidence["score"],
            "confidence_reason": confidence["reason"],
        }

    # ------------------------------------------------------------------
    def _build_evidence(self, analysis: Dict) -> List[Dict]:
        """Create a ranked list of evidence items with flags and confidence."""
        evidence = []
        kwh  = analysis.get("total_monthly_kwh", 0)
        cost = analysis.get("total_monthly_cost", 0)
        cur  = analysis.get("currency", "$")

        # 1. Total consumption vs national avg
        nat_avg  = 900
        above_pct = round(((kwh - nat_avg) / nat_avg) * 100, 1)
        ev_flag   = "high" if kwh > nat_avg * 1.1 else ("moderate" if kwh > nat_avg * 0.9 else "normal")
        evidence.append({
            "label":      "Total Monthly Consumption",
            "value":      f"{kwh} kWh",
            "flag":       ev_flag,
            "confidence": 1.0,
            "detail":     (f"{above_pct}% above national average"
                           if kwh > nat_avg else
                           f"{abs(above_pct)}% below national average"),
            "icon":       "bi-lightning-charge-fill",
        })

        # 2. Estimated bill
        bill_flag = "high" if cost > 150 else ("moderate" if cost > 80 else "normal")
        evidence.append({
            "label":      "Estimated Monthly Bill",
            "value":      f"{cur}{cost}",
            "flag":       bill_flag,
            "confidence": 1.0,
            "detail":     f"Annualised: {cur}{round(cost * 12, 2)}",
            "icon":       "bi-receipt",
        })

        # 3. Top consuming appliance
        apps = analysis.get("appliances", [])
        if apps:
            top = apps[0]
            pct = top.get("pct_of_total", 0)
            evidence.append({
                "label":      f"Top Consumer: {top.get('appliance')}",
                "value":      f"{top.get('monthly_kwh')} kWh ({pct}%)",
                "flag":       "high" if pct > 30 else "moderate",
                "confidence": 0.95,
                "detail":     f"Costs {cur}{top.get('monthly_cost', 0):.2f}/month",
                "icon":       "bi-plug-fill",
            })

        # 4. Peak hour
        peak_h  = analysis.get("peak_hour", 19)
        peak_ev = "high" if 17 <= peak_h <= 22 else "normal"
        evidence.append({
            "label":      "Peak Usage Hour",
            "value":      analysis.get("peak_hour_label", "N/A"),
            "flag":       peak_ev,
            "confidence": 0.9,
            "detail":     ("Falls within peak tariff window (5–10 PM)"
                           if peak_ev == "high" else "Off-peak timing"),
            "icon":       "bi-clock-fill",
        })

        # 5. Energy score
        score  = analysis.get("energy_score", 0)
        s_flag = "normal" if score >= 70 else ("moderate" if score >= 50 else "high")
        evidence.append({
            "label":      "Energy Efficiency Score",
            "value":      f"{score}/100 — {analysis.get('efficiency_rating', 'N/A')}",
            "flag":       s_flag,
            "confidence": 0.85,
            "detail":     self._score_detail(score),
            "icon":       "bi-award-fill",
        })

        # 6. AC check
        ac = next((a for a in apps
                   if "air condition" in a.get("appliance", "").lower()), None)
        if ac and ac.get("monthly_kwh", 0) > 200:
            evidence.append({
                "label":      "AC Usage",
                "value":      f"{ac.get('monthly_kwh')} kWh/mo",
                "flag":       "high",
                "confidence": 0.9,
                "detail":     "AC usage is a major cost driver",
                "icon":       "bi-thermometer-sun",
            })

        # 7. Water heater check
        wh = next((a for a in apps
                   if "water heat" in a.get("appliance", "").lower() or
                   "geyser" in a.get("appliance", "").lower()), None)
        if wh and wh.get("monthly_kwh", 0) > 80:
            evidence.append({
                "label":      "Water Heating",
                "value":      f"{wh.get('monthly_kwh')} kWh/mo",
                "flag":       "moderate",
                "confidence": 0.85,
                "detail":     "Significant heating load detected",
                "icon":       "bi-droplet-fill",
            })

        # Sort: high → moderate → normal
        order = {"high": 0, "moderate": 1, "normal": 2}
        return sorted(evidence, key=lambda e: order.get(e["flag"], 3))

    def _infer_causes(self, analysis: Dict, evidence: List) -> Dict:
        apps  = analysis.get("appliances", [])
        kwh   = analysis.get("total_monthly_kwh", 0)
        peak  = analysis.get("peak_hour", 19)

        primary = "Undetermined — insufficient data"
        secondary = []

        if apps:
            top = apps[0]
            pct = top.get("pct_of_total", 0)
            primary = (
                f"{top.get('appliance')} is the primary driver, accounting for "
                f"{pct}% of total monthly consumption ({top.get('monthly_kwh')} kWh)."
            )

        if 17 <= peak <= 22:
            secondary.append(
                f"Peak usage at {analysis.get('peak_hour_label')} coincides with "
                "high-tariff evening hours, inflating per-unit costs."
            )
        if kwh > 900:
            secondary.append(
                f"Overall consumption of {kwh} kWh exceeds the national average "
                "(900 kWh/month), indicating multiple high-draw devices or extended "
                "operating hours."
            )
        if analysis.get("energy_score", 100) < 55:
            secondary.append(
                "Low efficiency score suggests an older appliance fleet or lack of "
                "energy management practices."
            )

        return {"primary": primary, "secondary": secondary}

    def _score_confidence(self, analysis: Dict, evidence: List) -> Dict:
        score  = 0.40
        reasons = []

        if analysis.get("data_source") == "csv":
            score += 0.20; reasons.append("Real CSV data provided")
        if len(analysis.get("appliances", [])) >= 5:
            score += 0.15; reasons.append("Detailed appliance breakdown available")
        if analysis.get("monthly_trend"):
            score += 0.10; reasons.append("Multi-month trend data available")
        if analysis.get("hourly_usage"):
            score += 0.10; reasons.append("Hourly usage profile available")
        if len(evidence) >= 5:
            score += 0.05; reasons.append("Multiple evidence points collected")

        score = min(score, 1.0)
        level = "High" if score >= 0.80 else ("Medium" if score >= 0.60 else "Low")
        return {
            "level":  level,
            "score":  round(score, 2),
            "reason": "; ".join(reasons) if reasons else "Based on available demo data.",
        }

    @staticmethod
    def _score_detail(score: int) -> str:
        if score >= 85: return "Excellent efficiency — household is well optimised"
        if score >= 70: return "Good efficiency — minor improvements possible"
        if score >= 55: return "Average — several optimisation opportunities exist"
        if score >= 40: return "Below average — significant savings potential"
        return "Poor efficiency — immediate action recommended"


# ============================================================================
# RECOMMENDATION AGENT
# ============================================================================
class RecommendationAgent:
    """
    Responsibility: Generate structured, prioritised, explainable
    recommendations from analysis data.  Each recommendation includes
    XAI fields: why, expected benefit, savings estimate, difficulty.
    """

    def generate(self, analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Return a list of structured recommendation dicts, sorted by priority."""
        recs  = []
        apps  = analysis.get("appliances", [])
        kwh   = analysis.get("total_monthly_kwh", 0)
        cost  = analysis.get("total_monthly_cost", 0)
        cur   = analysis.get("currency", "$")
        rate  = analysis.get("electricity_rate", 0.12)
        peak  = analysis.get("peak_hour", 19)
        score = analysis.get("energy_score", 70)

        def add(title, why, benefit, monthly_kwh_save, difficulty, priority, time_req, icon):
            monthly_cost_save = round(monthly_kwh_save * rate, 2)
            annual_cost_save  = round(monthly_cost_save * 12, 2)
            co2_save          = round(monthly_kwh_save * 0.386, 2)
            recs.append({
                "title":              title,
                "why":                why,
                "expected_benefit":   benefit,
                "estimated_monthly_kwh_saving":  round(monthly_kwh_save, 2),
                "estimated_monthly_cost_saving": monthly_cost_save,
                "estimated_annual_cost_saving":  annual_cost_save,
                "estimated_co2_saving_kg":       co2_save,
                "difficulty":         difficulty,
                "priority":           priority,
                "time_required":      time_req,
                "icon":               icon,
                "currency":           cur,
            })

        # --- AC recommendation ---
        ac = next((a for a in apps if "air condition" in a.get("appliance","").lower()), None)
        if ac and ac.get("monthly_kwh", 0) > 150:
            pct = ac.get("pct_of_total", 0)
            add(
                title      = "Optimise Air Conditioner Schedule",
                why        = (f"Your AC consumes {ac.get('monthly_kwh')} kWh/month "
                              f"({pct}% of your total bill). This is the single largest "
                              f"contributor to your energy costs."),
                benefit    = ("Reducing AC runtime by 2 hours/day or raising the set-point "
                              "by 1°C can yield 6–10% energy savings."),
                monthly_kwh_save = ac.get("monthly_kwh", 0) * 0.10,
                difficulty = "Easy",
                priority   = "High",
                time_req   = "Immediate",
                icon       = "bi-thermometer-sun",
            )

        # --- Peak hour shifting ---
        if 17 <= peak <= 22:
            add(
                title      = "Shift Heavy Loads to Off-Peak Hours",
                why        = (f"Your peak usage at {analysis.get('peak_hour_label')} "
                              "falls within the most expensive tariff window (5–10 PM). "
                              "High-draw appliances used during this window cost more per kWh."),
                benefit    = ("Running washing machines, dishwashers, and EV chargers before "
                              "5 PM or after 10 PM can reduce effective cost by 10–15%."),
                monthly_kwh_save = kwh * 0.08,
                difficulty = "Easy",
                priority   = "High",
                time_req   = "1–2 days",
                icon       = "bi-clock-history",
            )

        # --- Water heater ---
        wh = next((a for a in apps if "water heat" in a.get("appliance","").lower()), None)
        if wh and wh.get("monthly_kwh", 0) > 80:
            add(
                title      = "Lower Water Heater Set-Point",
                why        = (f"Water heating contributes {wh.get('monthly_kwh')} kWh/month. "
                              "Most water heaters are set higher than necessary."),
                benefit    = ("Reducing the set-point from 60°C to 49°C saves "
                              "up to 10% on water heating costs with no comfort impact."),
                monthly_kwh_save = wh.get("monthly_kwh", 0) * 0.10,
                difficulty = "Easy",
                priority   = "Medium",
                time_req   = "15 minutes",
                icon       = "bi-droplet-fill",
            )

        # --- Low efficiency score ---
        if score < 60:
            add(
                title      = "Replace Oldest Appliances with Energy-Star Models",
                why        = (f"Your efficiency score of {score}/100 suggests older appliances. "
                              "Pre-2010 appliances often use 30–50% more energy than modern equivalents."),
                benefit    = ("Replacing the top 2 oldest appliances with A+++ rated models "
                              "can reduce consumption by 15–20%."),
                monthly_kwh_save = kwh * 0.15,
                difficulty = "Hard",
                priority   = "Medium",
                time_req   = "1–3 months",
                icon       = "bi-arrow-repeat",
            )

        # --- Lighting ---
        lights = next((a for a in apps if "light" in a.get("appliance","").lower()), None)
        if lights:
            add(
                title      = "Switch All Bulbs to LED",
                why        = (f"Lighting uses {lights.get('monthly_kwh')} kWh/month. "
                              "Incandescent/halogen bulbs waste ~90% of energy as heat."),
                benefit    = ("LED bulbs use 75–80% less energy and last 15× longer. "
                              "Payback period is typically under 6 months."),
                monthly_kwh_save = lights.get("monthly_kwh", 0) * 0.75,
                difficulty = "Easy",
                priority   = "Medium",
                time_req   = "1 day",
                icon       = "bi-lightbulb-fill",
            )

        # --- Refrigerator ---
        fridge = next((a for a in apps if "refrigerator" in a.get("appliance","").lower()), None)
        if fridge and fridge.get("monthly_kwh", 0) > 50:
            add(
                title      = "Optimise Refrigerator Settings",
                why        = ("The refrigerator runs 24/7 and is always consuming power. "
                              "Incorrect temperature settings or poor door seals waste energy constantly."),
                benefit    = ("Set fridge to 3–4°C and freezer to -18°C. "
                              "Check door seals. Clean condenser coils annually. "
                              "Saves up to 15% of refrigerator energy."),
                monthly_kwh_save = fridge.get("monthly_kwh", 0) * 0.12,
                difficulty = "Easy",
                priority   = "Low",
                time_req   = "30 minutes",
                icon       = "bi-snow2",
            )

        # --- Standby power ---
        add(
            title      = "Eliminate Standby Power (Vampire Load)",
            why        = ("Appliances left on standby — TVs, chargers, gaming consoles — "
                          "collectively consume 5–10% of a home's electricity with zero benefit."),
            benefit    = ("Using smart power strips or unplugging devices when not in use "
                          "eliminates this hidden cost entirely."),
            monthly_kwh_save = kwh * 0.06,
            difficulty = "Easy",
            priority   = "Low",
            time_req   = "1 hour",
            icon       = "bi-plug",
        )

        # Sort by priority: High first
        order = {"High": 0, "Medium": 1, "Low": 2}
        return sorted(recs, key=lambda r: order.get(r.get("priority", "Low"), 3))[:6]


# ============================================================================
# REPORT AGENT
# ============================================================================
class ReportAgent:
    """
    Responsibility: Assemble the final, complete Investigation Report
    by combining all agent outputs + AI narrative into one document.
    """

    def assemble(
        self,
        user_question:     str,
        analysis:          Dict[str, Any],
        investigation:     Dict[str, Any],
        recommendations:   List[Dict[str, Any]],
        ai_narrative:      str,
        session_memory:    Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """Build and return a complete report dict."""
        case_id   = self._generate_case_id()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        savings   = self._estimate_savings(analysis)

        report = {
            # --- Identity ---
            "case_id":           case_id,
            "timestamp":         timestamp,
            "generated_by":      "WattWise AI Agent Orchestrator",
            "user_question":     user_question,

            # --- Summary ---
            "investigation_summary": self._build_summary(analysis, investigation),
            "final_conclusion":      self._build_conclusion(analysis, investigation),

            # --- Evidence ---
            "evidence_collected": investigation.get("evidence_items", []),
            "primary_cause":      investigation.get("primary_cause", ""),
            "secondary_causes":   investigation.get("secondary_causes", []),

            # --- Confidence ---
            "confidence_level":   investigation.get("confidence_level", "Low"),
            "confidence_score":   investigation.get("confidence_score", 0.0),
            "confidence_reason":  investigation.get("confidence_reason", ""),

            # --- AI output ---
            "ai_narrative":      ai_narrative,

            # --- Structured recommendations ---
            "structured_recommendations": recommendations,
            "recommendations":   [r["title"] for r in recommendations],

            # --- Savings ---
            "estimated_monthly_savings": savings,
            "potential_savings_cost":   analysis.get("potential_savings_cost", 0),

            # --- Metrics ---
            "data_source":        analysis.get("data_source", "demo"),
            "total_monthly_kwh":  analysis.get("total_monthly_kwh"),
            "total_monthly_cost": analysis.get("total_monthly_cost"),
            "annual_cost":        analysis.get("annual_cost"),
            "energy_score":       analysis.get("energy_score"),
            "efficiency_rating":  analysis.get("efficiency_rating"),
            "monthly_co2_kg":     analysis.get("monthly_co2_kg"),
            "top_appliance":      analysis.get("top_appliance"),
            "peak_hour_label":    analysis.get("peak_hour_label"),
            "currency":           analysis.get("currency", "$"),

            # --- User context ---
            "user_profile":  session_memory or {},
        }
        return report

    # ------------------------------------------------------------------
    @staticmethod
    def _generate_case_id() -> str:
        short = uuid.uuid4().hex.upper()[:10]
        return f"WW-{datetime.now().strftime('%Y%m%d')}-{short}"

    @staticmethod
    def _build_summary(analysis: Dict, investigation: Dict) -> str:
        src   = "uploaded CSV data" if analysis.get("data_source") == "csv" else "demo dataset"
        kwh   = analysis.get("total_monthly_kwh", 0)
        cost  = analysis.get("total_monthly_cost", 0)
        cur   = analysis.get("currency", "$")
        top   = analysis.get("top_appliance", "unknown")
        peak  = analysis.get("peak_hour_label", "N/A")
        score = analysis.get("energy_score", 0)
        return (
            f"Investigation based on {src}. The household consumes {kwh} kWh/month "
            f"(estimated bill: {cur}{cost}). Energy Score: {score}/100. "
            f"Primary consumer: {top}. Peak usage at {peak}."
        )

    @staticmethod
    def _build_conclusion(analysis: Dict, investigation: Dict) -> str:
        conf  = investigation.get("confidence_level", "Low")
        score = analysis.get("energy_score", 0)
        kwh   = analysis.get("total_monthly_kwh", 0)
        cur   = analysis.get("currency", "$")
        savings = analysis.get("potential_savings_cost", 0)
        return (
            f"With {conf.lower()} confidence, this investigation concludes that "
            f"the household's energy consumption of {kwh} kWh/month "
            f"(efficiency score: {score}/100) presents an estimated "
            f"monthly savings potential of {cur}{savings}. "
            f"The primary cause has been identified and "
            f"{len(investigation.get('secondary_causes', []))} secondary contributing "
            f"factors were detected. "
            f"Immediate implementation of High-priority recommendations is advised."
        )

    @staticmethod
    def _estimate_savings(analysis: Dict) -> Dict:
        cost = analysis.get("total_monthly_cost", 0)
        cur  = analysis.get("currency", "$")
        low  = round(cost * 0.15, 2)
        high = round(cost * 0.28, 2)
        return {
            "low":  f"{cur}{low}",
            "high": f"{cur}{high}",
            "note": "Conservative–optimistic range if top recommendations are implemented.",
        }
