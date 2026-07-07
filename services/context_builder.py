"""
WattWise AI - Context Builder
Constructs structured, token-efficient evidence contexts
that are sent to IBM watsonx.ai instead of raw CSV data.

Design principle: Python calculates → Context Builder packages →
watsonx.ai reasons. The AI never sees raw data.
"""

from datetime import datetime
from typing import Dict, Any, Optional


class ContextBuilder:
    """
    Transforms raw analysis dicts + session memory into a concise,
    structured text block suitable for embedding in an AI prompt.
    """

    # Approximate national average (kWh/month) used for comparison
    NATIONAL_AVERAGE_KWH = 900

    def build(
        self,
        analysis: Dict[str, Any],
        user_question: str = "",
        session_memory: Optional[Dict] = None,
        weather: Optional[str] = None,
    ) -> str:
        """
        Return a structured evidence string for injection into a watsonx.ai prompt.
        Never passes raw DataFrames or CSV rows – only calculated summaries.
        """
        ctx = []
        ctx.append("=" * 60)
        ctx.append("HOUSEHOLD ENERGY INVESTIGATION CONTEXT")
        ctx.append(f"Generated : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        ctx.append(f"Data Src  : {analysis.get('data_source', 'demo').upper()}")
        ctx.append("=" * 60)

        # ---- Core metrics ----
        kwh    = analysis.get("total_monthly_kwh", 0)
        cost   = analysis.get("total_monthly_cost", 0)
        cur    = analysis.get("currency", "$")
        rate   = analysis.get("electricity_rate", 0.12)
        daily  = analysis.get("daily_avg_kwh", 0)
        peak   = analysis.get("peak_hour_label", "N/A")
        top_a  = analysis.get("top_appliance", "N/A")
        score  = analysis.get("energy_score", 0)
        rating = analysis.get("efficiency_rating", "N/A")
        co2    = analysis.get("monthly_co2_kg", 0)

        ctx.append("")
        ctx.append("SECTION 1 — CONSUMPTION METRICS")
        ctx.append(f"  Total Monthly Consumption : {kwh} kWh")
        ctx.append(f"  Estimated Monthly Bill    : {cur}{cost}")
        ctx.append(f"  Daily Average             : {daily} kWh/day")
        ctx.append(f"  Electricity Rate          : {cur}{rate}/kWh")
        ctx.append(f"  vs National Average       : {kwh} vs {self.NATIONAL_AVERAGE_KWH} kWh "
                   f"({'ABOVE' if kwh > self.NATIONAL_AVERAGE_KWH else 'BELOW'} avg by "
                   f"{abs(round(kwh - self.NATIONAL_AVERAGE_KWH, 1))} kWh)")
        ctx.append(f"  Energy Score              : {score}/100 — {rating}")
        ctx.append(f"  Monthly CO₂ Estimate      : {co2} kg")

        # ---- Peak usage ----
        ctx.append("")
        ctx.append("SECTION 2 — PEAK USAGE ANALYSIS")
        ctx.append(f"  Peak Hour                 : {peak}")
        ctx.append(f"  Highest Consumer          : {top_a}")

        hourly = analysis.get("hourly_usage", {})
        if hourly:
            peak_h = max(hourly, key=hourly.get)
            off_h  = min(hourly, key=hourly.get)
            ctx.append(f"  Peak Hour kWh             : {hourly.get(peak_h, 0)} kWh")
            ctx.append(f"  Off-peak Hour kWh         : {hourly.get(off_h, 0)} kWh")

        # ---- Top appliances ----
        ctx.append("")
        ctx.append("SECTION 3 — TOP CONSUMING APPLIANCES")
        for i, a in enumerate(analysis.get("top_3_appliances", []), 1):
            pct = round((a.get("monthly_kwh", 0) / max(kwh, 1)) * 100, 1)
            ctx.append(f"  {i}. {a.get('appliance'):<22} "
                       f"{a.get('monthly_kwh')} kWh/mo  "
                       f"({cur}{a.get('monthly_cost', 0):.2f})  "
                       f"[{pct}% of total]")

        # ---- Monthly trend ----
        trend = analysis.get("monthly_trend", [])
        if len(trend) >= 2:
            ctx.append("")
            ctx.append("SECTION 4 — MONTHLY TREND")
            prev = trend[-2].get("kwh", 0)
            curr = trend[-1].get("kwh", 0)
            change = round(curr - prev, 2)
            pct_ch = round((change / max(prev, 1)) * 100, 1)
            direction = "INCREASED" if change > 0 else "DECREASED"
            ctx.append(f"  {trend[-2].get('month')} → {trend[-1].get('month')}: "
                       f"{direction} by {abs(change)} kWh ({abs(pct_ch)}%)")
            for t in trend:
                ctx.append(f"  {t.get('month'):<12}: {t.get('kwh')} kWh")

        # ---- Tariff / rate info ----
        ctx.append("")
        ctx.append("SECTION 5 — TARIFF & COST BREAKDOWN")
        ctx.append(f"  Electricity Rate          : {cur}{rate}/kWh")
        ctx.append(f"  Estimated Annual Bill     : {cur}{round(cost * 12, 2)}")
        ctx.append(f"  Daily Cost                : {cur}{round(cost / 30, 2)}")

        # ---- Weather (optional) ----
        if weather:
            ctx.append("")
            ctx.append("SECTION 6 — WEATHER CONTEXT")
            ctx.append(f"  {weather}")

        # ---- Session memory / user profile ----
        if session_memory:
            ctx.append("")
            ctx.append("SECTION 7 — USER PROFILE")
            for k, v in session_memory.items():
                if v and k not in ("conversation",):
                    ctx.append(f"  {k.replace('_', ' ').title():<24}: {v}")

        # ---- User question ----
        if user_question:
            ctx.append("")
            ctx.append("USER QUESTION")
            ctx.append(f"  {user_question}")

        ctx.append("=" * 60)
        return "\n".join(ctx)

    # ------------------------------------------------------------------
    # Lightweight summary variant (for quick insights / dashboard)
    # ------------------------------------------------------------------
    def build_brief(self, analysis: Dict[str, Any]) -> str:
        """One-page summary for dashboard quick insights."""
        kwh  = analysis.get("total_monthly_kwh", 0)
        cost = analysis.get("total_monthly_cost", 0)
        cur  = analysis.get("currency", "$")
        top  = analysis.get("top_appliance", "N/A")
        peak = analysis.get("peak_hour_label", "N/A")
        score = analysis.get("energy_score", 0)
        return (
            f"Monthly: {kwh} kWh | Bill: {cur}{cost} | "
            f"Top Consumer: {top} | Peak: {peak} | "
            f"Score: {score}/100"
        )
