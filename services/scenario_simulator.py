"""
WattWise AI - Scenario Simulator Service
Parses natural-language 'what-if' questions and orchestrates the
deterministic calculation + AI reasoning pipeline.
"""

import re
from typing import Dict, Any, Tuple, Optional


# ---------------------------------------------------------------------------
# Known appliance synonyms for fuzzy matching
# ---------------------------------------------------------------------------
APPLIANCE_ALIASES = {
    "ac":              "Air Conditioner",
    "air conditioning":"Air Conditioner",
    "air conditioner": "Air Conditioner",
    "a/c":             "Air Conditioner",
    "heater":          "Water Heater",
    "water heater":    "Water Heater",
    "geyser":          "Water Heater",
    "fridge":          "Refrigerator",
    "refrigerator":    "Refrigerator",
    "washer":          "Washing Machine",
    "washing machine": "Washing Machine",
    "laundry":         "Washing Machine",
    "tv":              "Television",
    "television":      "Television",
    "lights":          "Lighting",
    "lighting":        "Lighting",
    "laptop":          "Laptop",
    "computer":        "Laptop",
    "microwave":       "Microwave",
    "oven":            "Electric Oven",
    "dishwasher":      "Dishwasher",
}

# Number word → digit
NUMBER_WORDS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "half": 0.5,
}


class ScenarioSimulator:
    """
    Parses free-text 'what-if' queries into structured scenario parameters,
    then delegates to EnergyAnalyzer (deterministic) and WatsonxService (reasoning).
    """

    # ------------------------------------------------------------------
    # Parse a free-text scenario query
    # ------------------------------------------------------------------
    def parse_scenario(self, query: str) -> Dict[str, Any]:
        """
        Extract appliance, hours change, and direction from a natural-language query.
        Returns a structured dict for downstream processing.
        """
        q_lower = query.lower()

        appliance = self._extract_appliance(q_lower)
        hours     = self._extract_hours(q_lower)
        direction = self._extract_direction(q_lower)

        # Treat direction "increase" as negative saving
        change_hours = hours if direction == "reduce" else -hours

        return {
            "raw_query":    query,
            "appliance":    appliance or "Air Conditioner",
            "change_hours": change_hours,
            "direction":    direction,
            "hours":        hours,
            "parsed":       appliance is not None and hours > 0,
        }

    # ------------------------------------------------------------------
    # Private parsers
    # ------------------------------------------------------------------
    def _extract_appliance(self, text: str) -> Optional[str]:
        for alias, canonical in APPLIANCE_ALIASES.items():
            if alias in text:
                return canonical
        return None

    def _extract_hours(self, text: str) -> float:
        # Match "2 hours", "2.5 hours", "30 minutes"
        m = re.search(r"(\d+(?:\.\d+)?)\s*hours?", text)
        if m:
            return float(m.group(1))
        m = re.search(r"(\d+)\s*minutes?", text)
        if m:
            return round(int(m.group(1)) / 60, 2)
        for word, val in NUMBER_WORDS.items():
            if word in text and "hour" in text:
                return float(val)
        return 1.0   # default: 1 hour

    @staticmethod
    def _extract_direction(text: str) -> str:
        reduce_words  = ["reduc", "cut", "lower", "decreas", "less", "turn off", "stop", "limit"]
        increase_words = ["increas", "more", "add", "extra", "longer", "extend"]
        for w in reduce_words:
            if w in text:
                return "reduce"
        for w in increase_words:
            if w in text:
                return "increase"
        return "reduce"   # safe default

    # ------------------------------------------------------------------
    # Build a human-readable scenario description for the AI prompt
    # ------------------------------------------------------------------
    @staticmethod
    def build_scenario_description(parsed: Dict[str, Any]) -> str:
        direction = parsed.get("direction", "reduce")
        appliance = parsed.get("appliance", "appliance")
        hours     = abs(parsed.get("change_hours", 1))
        verb      = "reduce" if direction == "reduce" else "increase"
        return (
            f"What if I {verb} {appliance} usage by "
            f"{hours} hour{'s' if hours != 1 else ''} per day?"
        )
