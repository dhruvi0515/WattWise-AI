"""
WattWise AI - Shared Utility Helpers
=====================================
Pure helper functions with no side effects.
These functions are imported across routes, services, and templates.
"""

import os
import re
import uuid
import json
import html
from datetime import datetime
from typing import Any

from werkzeug.utils import secure_filename

from config import ALLOWED_EXTENSIONS


# ─────────────────────────────────────────────────────────────────────────────
# File helpers
# ─────────────────────────────────────────────────────────────────────────────

def allowed_file(filename: str) -> bool:
    """Return True when the file extension is in ALLOWED_EXTENSIONS."""
    if not filename or "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[1].lower()
    return ext in ALLOWED_EXTENSIONS


def generate_unique_filename(original: str) -> str:
    """Return a collision-safe, sanitised filename with a short UUID suffix."""
    if "." in original:
        base, ext = original.rsplit(".", 1)
        ext = ext.lower()
    else:
        base, ext = original, "csv"
    safe_base = secure_filename(base) or "upload"
    return f"{safe_base}_{uuid.uuid4().hex[:8]}.{ext}"


# ─────────────────────────────────────────────────────────────────────────────
# Formatting helpers
# ─────────────────────────────────────────────────────────────────────────────

def format_currency(amount: float, symbol: str = "$") -> str:
    """Return a formatted currency string: $1,234.56"""
    try:
        return f"{symbol}{float(amount):,.2f}"
    except (TypeError, ValueError):
        return f"{symbol}0.00"


def format_kwh(value: float) -> str:
    """Return a formatted kWh string: 1,234.56 kWh"""
    try:
        return f"{float(value):,.2f} kWh"
    except (TypeError, ValueError):
        return "0.00 kWh"


def badge_class(flag: str) -> str:
    """Map a severity flag to the correct Bootstrap colour class."""
    return {
        "high":     "danger",
        "moderate": "warning",
        "normal":   "success",
        "info":     "info",
    }.get(str(flag).lower(), "secondary")


# ─────────────────────────────────────────────────────────────────────────────
# JSON helpers
# ─────────────────────────────────────────────────────────────────────────────

def _json_serial(obj: Any) -> str:
    """Extended JSON encoder: handles datetime objects."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serialisable")


def safe_json_dumps(data: Any) -> str:
    """Serialise data to JSON safely, handling datetime objects."""
    return json.dumps(data, default=_json_serial)


# ─────────────────────────────────────────────────────────────────────────────
# Security / sanitisation helpers
# ─────────────────────────────────────────────────────────────────────────────

# Characters allowed in free-text user inputs (whitelist approach)
_SAFE_TEXT_RE = re.compile(r"[^\w\s\-\.,?!@#()/°%'\"\n]", re.UNICODE)


def sanitize_text(value: str, max_length: int = 500) -> str:
    """
    Strip potentially harmful characters from a user-supplied string.
    Keeps alphanumerics, common punctuation, and whitespace.
    """
    if not isinstance(value, str):
        return ""
    # HTML-escape first, then strip unusual chars, then truncate
    cleaned = html.escape(value.strip())
    cleaned = _SAFE_TEXT_RE.sub("", cleaned)
    return cleaned[:max_length]


def sanitize_filename_input(value: str) -> str:
    """Sanitise a user-supplied filename for safe storage."""
    return secure_filename(str(value))[:100]


def is_safe_float(value: Any, min_val: float = 0.0, max_val: float = 1e9) -> bool:
    """Return True when value can be converted to a float within [min_val, max_val]."""
    try:
        v = float(value)
        return min_val <= v <= max_val
    except (TypeError, ValueError):
        return False


def coerce_float(value: Any, default: float = 0.0) -> float:
    """Convert value to float, returning default on failure."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def coerce_int(value: Any, default: int = 0, min_val: int = 0, max_val: int = 10_000) -> int:
    """Convert value to a bounded int, returning default on failure."""
    try:
        v = int(value)
        return max(min_val, min(max_val, v))
    except (TypeError, ValueError):
        return default


# ─────────────────────────────────────────────────────────────────────────────
# API response helpers
# ─────────────────────────────────────────────────────────────────────────────

def error_response(message: str, code: int = 400) -> tuple:
    """Produce a consistent JSON error response tuple for Flask routes."""
    from flask import jsonify
    return jsonify({"status": "error", "message": message}), code


def success_response(data: dict) -> Any:
    """Produce a consistent JSON success response for Flask routes."""
    from flask import jsonify
    return jsonify({"status": "ok", **data})
