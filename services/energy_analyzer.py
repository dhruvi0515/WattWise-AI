"""
WattWise AI - Energy Analysis Engine
Performs all deterministic Python/Pandas calculations.
Results are structured and passed to IBM watsonx.ai for reasoning.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import ELECTRICITY_RATE, AGENT_INSTRUCTIONS


# ---------------------------------------------------------------------------
# Built-in demo dataset (used when no CSV is uploaded)
# ---------------------------------------------------------------------------
DEMO_APPLIANCES = [
    {"appliance": "Air Conditioner",   "watts": 1500, "hours_per_day": 8,  "days_per_month": 30},
    {"appliance": "Water Heater",      "watts": 2000, "hours_per_day": 2,  "days_per_month": 30},
    {"appliance": "Refrigerator",      "watts": 150,  "hours_per_day": 24, "days_per_month": 30},
    {"appliance": "Washing Machine",   "watts": 500,  "hours_per_day": 1,  "days_per_month": 20},
    {"appliance": "Television",        "watts": 120,  "hours_per_day": 5,  "days_per_month": 30},
    {"appliance": "Laptop",            "watts": 65,   "hours_per_day": 6,  "days_per_month": 30},
    {"appliance": "Lighting",          "watts": 200,  "hours_per_day": 6,  "days_per_month": 30},
    {"appliance": "Microwave",         "watts": 1000, "hours_per_day": 0.5,"days_per_month": 30},
    {"appliance": "Dishwasher",        "watts": 1200, "hours_per_day": 0.5,"days_per_month": 25},
    {"appliance": "Electric Oven",     "watts": 2400, "hours_per_day": 0.5,"days_per_month": 20},
]

DEMO_HOURLY_USAGE = {
    0: 0.3, 1: 0.2, 2: 0.2, 3: 0.2, 4: 0.3, 5: 0.5,
    6: 1.2, 7: 1.8, 8: 1.5, 9: 1.0, 10: 0.9, 11: 0.8,
    12: 1.1, 13: 1.0, 14: 0.9, 15: 0.8, 16: 1.0, 17: 1.4,
    18: 2.0, 19: 2.5, 20: 2.8, 21: 2.4, 22: 1.8, 23: 1.0,
}


class EnergyAnalyzer:
    """
    Core engine for all deterministic energy calculations.
    Accepts either an uploaded DataFrame or falls back to demo data.
    """

    def __init__(self, df: Optional[pd.DataFrame] = None,
                 electricity_rate: float = ELECTRICITY_RATE):
        self.rate = electricity_rate
        self.df = df
        self.currency = AGENT_INSTRUCTIONS["currency_symbol"]

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------
    def run_full_analysis(self) -> Dict[str, Any]:
        """
        Run all analytical calculations and return a structured summary dict.
        This summary is consumed by the AI investigation workflow.
        """
        if self.df is not None:
            return self._analyse_csv()
        return self._analyse_demo()

    # ------------------------------------------------------------------
    # Demo-data analysis
    # ------------------------------------------------------------------
    def _analyse_demo(self) -> Dict[str, Any]:
        appliances_df = pd.DataFrame(DEMO_APPLIANCES)

        # kWh per month per appliance
        appliances_df["monthly_kwh"] = (
            appliances_df["watts"] / 1000
            * appliances_df["hours_per_day"]
            * appliances_df["days_per_month"]
        )
        appliances_df["monthly_cost"] = appliances_df["monthly_kwh"] * self.rate

        total_kwh  = round(appliances_df["monthly_kwh"].sum(), 2)
        total_cost = round(appliances_df["monthly_cost"].sum(), 2)
        top_appliance = appliances_df.loc[
            appliances_df["monthly_kwh"].idxmax(), "appliance"
        ]

        # Peak hour analysis
        peak_hour    = max(DEMO_HOURLY_USAGE, key=DEMO_HOURLY_USAGE.get)
        hourly_costs = {h: round(v * self.rate, 4)
                        for h, v in DEMO_HOURLY_USAGE.items()}

        # Monthly trend simulation (last 6 months)
        monthly_trend = self._simulate_monthly_trend(total_kwh)

        # Daily average
        daily_avg_kwh = round(total_kwh / 30, 2)

        return {
            "data_source":       "demo",
            "total_monthly_kwh": total_kwh,
            "total_monthly_cost": total_cost,
            "daily_avg_kwh":     daily_avg_kwh,
            "electricity_rate":  self.rate,
            "currency":          self.currency,
            "top_appliance":     top_appliance,
            "peak_hour":         peak_hour,
            "peak_hour_label":   self._format_hour(peak_hour),
            "appliances": appliances_df[[
                "appliance", "watts", "hours_per_day",
                "days_per_month", "monthly_kwh", "monthly_cost"
            ]].to_dict(orient="records"),
            "hourly_usage":      DEMO_HOURLY_USAGE,
            "hourly_costs":      hourly_costs,
            "monthly_trend":     monthly_trend,
            "top_3_appliances":  appliances_df.nlargest(3, "monthly_kwh")[
                ["appliance", "monthly_kwh", "monthly_cost"]
            ].to_dict(orient="records"),
            "analysis_timestamp": datetime.now().isoformat(),
        }

    # ------------------------------------------------------------------
    # CSV-based analysis
    # ------------------------------------------------------------------
    def _analyse_csv(self) -> Dict[str, Any]:
        df = self.df.copy()
        df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")

        # ---------- detect column schema ----------
        kwh_col       = self._find_column(df, ["kwh", "energy", "consumption", "usage"])
        appliance_col = self._find_column(df, ["appliance", "device", "name", "equipment"])
        date_col      = self._find_column(df, ["date", "timestamp", "time", "datetime"])
        hour_col      = self._find_column(df, ["hour", "hr", "time_of_day"])
        cost_col      = self._find_column(df, ["cost", "bill", "charge", "amount"])
        watts_col     = self._find_column(df, ["watts", "watt", "power", "wattage"])

        # ---------- derive kWh if missing ----------
        if kwh_col is None and watts_col is not None:
            hours_col = self._find_column(df, ["hours", "duration", "hrs"])
            h = df[hours_col] if hours_col else 1
            df["_kwh"] = (df[watts_col] / 1000) * h
            kwh_col = "_kwh"

        if kwh_col is None:
            # Cannot compute; fall back to demo
            result = self._analyse_demo()
            result["warning"] = "CSV did not contain recognisable energy columns. Demo data shown."
            return result

        # ---------- totals ----------
        total_kwh  = round(float(df[kwh_col].sum()), 2)
        total_cost = (
            round(float(df[cost_col].sum()), 2)
            if cost_col
            else round(total_kwh * self.rate, 2)
        )
        daily_avg_kwh = round(total_kwh / max(len(df), 1), 2)

        # ---------- appliance breakdown ----------
        appliance_summary = []
        top_appliance     = "Unknown"
        if appliance_col:
            grp = df.groupby(appliance_col)[kwh_col].sum().reset_index()
            grp.columns = ["appliance", "monthly_kwh"]
            grp["monthly_cost"] = (grp["monthly_kwh"] * self.rate).round(2)
            grp["monthly_kwh"]  = grp["monthly_kwh"].round(2)
            grp = grp.sort_values("monthly_kwh", ascending=False)
            appliance_summary = grp.to_dict(orient="records")
            if len(grp):
                top_appliance = grp.iloc[0]["appliance"]

        # ---------- hourly usage ----------
        hourly_usage = dict(DEMO_HOURLY_USAGE)
        if hour_col:
            hgrp = df.groupby(hour_col)[kwh_col].sum()
            hourly_usage = {int(k): round(float(v), 3) for k, v in hgrp.items()}

        peak_hour = max(hourly_usage, key=hourly_usage.get) if hourly_usage else 19

        # ---------- daily trend ----------
        monthly_trend = []
        if date_col:
            df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
            df = df.dropna(subset=[date_col])
            df["_month"] = df[date_col].dt.to_period("M")
            mgrp = df.groupby("_month")[kwh_col].sum().reset_index()
            mgrp.columns = ["month", "kwh"]
            monthly_trend = [
                {"month": str(r["month"]), "kwh": round(float(r["kwh"]), 2)}
                for _, r in mgrp.iterrows()
            ]

        if not monthly_trend:
            monthly_trend = self._simulate_monthly_trend(total_kwh)

        top3 = appliance_summary[:3] if appliance_summary else []

        return {
            "data_source":        "csv",
            "total_monthly_kwh":  total_kwh,
            "total_monthly_cost": total_cost,
            "daily_avg_kwh":      daily_avg_kwh,
            "electricity_rate":   self.rate,
            "currency":           self.currency,
            "top_appliance":      top_appliance,
            "peak_hour":          peak_hour,
            "peak_hour_label":    self._format_hour(peak_hour),
            "appliances":         appliance_summary,
            "hourly_usage":       hourly_usage,
            "hourly_costs":       {h: round(v * self.rate, 4)
                                   for h, v in hourly_usage.items()},
            "monthly_trend":      monthly_trend,
            "top_3_appliances":   top3,
            "analysis_timestamp": datetime.now().isoformat(),
            "rows_analysed":      len(df),
            "columns_detected":   {
                "kwh": kwh_col, "appliance": appliance_col,
                "date": date_col, "hour": hour_col,
            },
        }

    # ------------------------------------------------------------------
    # Scenario simulation (deterministic part)
    # ------------------------------------------------------------------
    def simulate_scenario(self, appliance: str, change_hours: float,
                           current_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Estimate energy / cost impact of reducing/increasing appliance usage.
        Returns structured data for the AI to reason over.
        """
        appliances = current_analysis.get("appliances", [])
        match = next((a for a in appliances
                      if a.get("appliance", "").lower() == appliance.lower()), None)

        if match is None:
            # Estimate generically
            avg_watts = 1000
            monthly_kwh_saved = (avg_watts / 1000) * abs(change_hours) * 30
        else:
            watts = match.get("watts", 1000)
            monthly_kwh_saved = (watts / 1000) * abs(change_hours) * 30

        monthly_cost_saved  = round(monthly_kwh_saved * self.rate, 2)
        annual_kwh_saved    = round(monthly_kwh_saved * 12, 2)
        annual_cost_saved   = round(monthly_cost_saved * 12, 2)
        pct_saving          = round(
            (monthly_kwh_saved / max(current_analysis.get("total_monthly_kwh", 1), 1)) * 100, 1
        )

        return {
            "appliance":            appliance,
            "change_hours":         change_hours,
            "direction":            "reduction" if change_hours > 0 else "increase",
            "monthly_kwh_change":   round(monthly_kwh_saved, 2),
            "monthly_cost_change":  monthly_cost_saved,
            "annual_kwh_change":    annual_kwh_saved,
            "annual_cost_change":   annual_cost_saved,
            "percentage_saving":    pct_saving,
            "current_monthly_kwh":  current_analysis.get("total_monthly_kwh"),
            "new_monthly_kwh":      round(
                current_analysis.get("total_monthly_kwh", 0) - monthly_kwh_saved, 2
            ),
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _find_column(df: pd.DataFrame, candidates: List[str]) -> Optional[str]:
        """Case-insensitive fuzzy column search."""
        for col in df.columns:
            for candidate in candidates:
                if candidate in col.lower():
                    return col
        return None

    @staticmethod
    def _format_hour(hour: int) -> str:
        suffix = "AM" if hour < 12 else "PM"
        h      = hour if hour <= 12 else hour - 12
        h      = 12 if h == 0 else h
        return f"{h}:00 {suffix}"

    @staticmethod
    def _simulate_monthly_trend(base_kwh: float) -> List[Dict]:
        """Generate last-6-months trend data with realistic variance."""
        trend = []
        now   = datetime.now()
        for i in range(5, -1, -1):
            month = (now - timedelta(days=i * 30)).strftime("%b %Y")
            noise = np.random.uniform(-0.12, 0.12)
            trend.append({
                "month": month,
                "kwh":   round(base_kwh * (1 + noise), 2),
            })
        return trend

    # ------------------------------------------------------------------
    # Formatting helpers (used by templates / routes)
    # ------------------------------------------------------------------
    def format_summary_for_ai(self, analysis: Dict[str, Any]) -> str:
        """
        Convert analysis dict into a human-readable evidence block
        that can be embedded in a watsonx.ai prompt.
        """
        lines = [
            "=== HOUSEHOLD ENERGY EVIDENCE REPORT ===",
            f"Data Source      : {analysis.get('data_source', 'unknown').upper()}",
            f"Analysis Date    : {analysis.get('analysis_timestamp', 'N/A')}",
            f"Total Monthly Use: {analysis.get('total_monthly_kwh')} kWh",
            f"Estimated Bill   : {analysis.get('currency')}{analysis.get('total_monthly_cost')}",
            f"Daily Average    : {analysis.get('daily_avg_kwh')} kWh",
            f"Electricity Rate : {analysis.get('currency')}{analysis.get('electricity_rate')} / kWh",
            f"Peak Usage Hour  : {analysis.get('peak_hour_label')}",
            f"Top Consumer     : {analysis.get('top_appliance')}",
            "",
            "--- TOP 3 APPLIANCES BY CONSUMPTION ---",
        ]
        for a in analysis.get("top_3_appliances", []):
            lines.append(
                f"  • {a.get('appliance')}: "
                f"{a.get('monthly_kwh')} kWh / month "
                f"({analysis.get('currency')}{a.get('monthly_cost')})"
            )
        lines.append("")
        lines.append("--- FULL APPLIANCE BREAKDOWN ---")
        for a in analysis.get("appliances", []):
            lines.append(
                f"  {a.get('appliance')}: "
                f"{a.get('monthly_kwh')} kWh/month, "
                f"{analysis.get('currency')}{a.get('monthly_cost')}/month"
            )
        return "\n".join(lines)
