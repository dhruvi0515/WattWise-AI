"""
WattWise AI - Session Memory Service
Maintains conversation context, user profile, and preferences
across the session to personalise AI responses.
"""

from typing import Dict, Any, Optional
from flask import session


class SessionMemory:
    """
    Provides a clean interface to read/write user profile and
    conversation context from the Flask session store.
    All data lives in the Flask session — no external DB required.
    """

    PROFILE_KEY      = "user_profile"
    CONVERSATION_KEY = "conversation"
    PREFS_KEY        = "user_preferences"

    # ------------------------------------------------------------------
    # User Profile
    # ------------------------------------------------------------------
    def get_profile(self) -> Dict[str, Any]:
        return session.get(self.PROFILE_KEY, {})

    def update_profile(self, **kwargs) -> None:
        profile = self.get_profile()
        profile.update({k: v for k, v in kwargs.items() if v is not None})
        session[self.PROFILE_KEY] = profile

    def set_location(self, location: str) -> None:
        self.update_profile(location=location)

    def set_family_size(self, size: int) -> None:
        self.update_profile(family_size=size)

    def set_home_type(self, home_type: str) -> None:
        self.update_profile(home_type=home_type)

    # ------------------------------------------------------------------
    # Conversation history
    # ------------------------------------------------------------------
    def get_conversation(self) -> list:
        return session.get(self.CONVERSATION_KEY, [])

    def add_message(self, role: str, content: str) -> None:
        conv = self.get_conversation()
        conv.append({"role": role, "content": content})
        session[self.CONVERSATION_KEY] = conv[-40:]   # last 20 exchanges

    def clear_conversation(self) -> None:
        session.pop(self.CONVERSATION_KEY, None)

    def get_recent_history(self, n_exchanges: int = 3) -> list:
        """Return the last n exchanges (n user + n assistant messages)."""
        return self.get_conversation()[-(n_exchanges * 2):]

    # ------------------------------------------------------------------
    # User preferences
    # ------------------------------------------------------------------
    def get_preferences(self) -> Dict[str, Any]:
        return session.get(self.PREFS_KEY, {})

    def set_preference(self, key: str, value: Any) -> None:
        prefs = self.get_preferences()
        prefs[key] = value
        session[self.PREFS_KEY] = prefs

    # ------------------------------------------------------------------
    # Summary for context builder
    # ------------------------------------------------------------------
    def build_context_dict(self) -> Dict[str, Any]:
        """Merge profile + preferences into one flat dict for ContextBuilder."""
        data = {}
        data.update(self.get_profile())
        data.update(self.get_preferences())
        return data

    # ------------------------------------------------------------------
    # Extract profile hints from natural language (simple heuristics)
    # ------------------------------------------------------------------
    def extract_and_store_hints(self, text: str) -> None:
        """
        Scan user text for profile hints and auto-store them.
        Example: "I live in Texas" → location = Texas
        """
        tl = text.lower()

        # Family size hints
        for phrase, size in [
            ("live alone", 1), ("just me", 1), ("family of 2", 2), ("family of 3", 3),
            ("family of 4", 4), ("family of 5", 5), ("4 people", 4), ("3 people", 3),
        ]:
            if phrase in tl:
                self.set_family_size(size)

        # Home type hints
        for phrase, htype in [
            ("apartment", "Apartment"), ("flat", "Apartment"),
            ("house", "House"), ("bungalow", "Bungalow"),
            ("townhouse", "Townhouse"), ("villa", "Villa"),
        ]:
            if phrase in tl:
                self.set_home_type(htype)
