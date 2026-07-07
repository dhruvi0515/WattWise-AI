"""
WattWise AI v2 - Main Application Routes
==========================================
All user-facing pages and REST API endpoints are defined here.
Every AI task is delegated to the AgentOrchestrator.
No route constructs prompts or calls IBM watsonx.ai directly.

Route Groups
------------
Pages   : /, /chat, /upload, /analysis, /reports, /recommendations,
          /simulator, /settings
API     : /api/chat, /api/investigate, /api/recommendations, /api/simulate,
          /api/upload, /api/quick-insights, /api/settings, /api/analysis-data,
          /api/reset
Reports : /reports/<case_id>, /reports/<case_id>/pdf
"""

import os
import logging

from datetime import datetime
from flask import (
    Blueprint, render_template, request, session,
    redirect, url_for, flash, current_app, make_response,
)
import pandas as pd

from services.agent_orchestrator import AgentOrchestrator
from services.energy_analyzer    import EnergyAnalyzer
from services.session_memory     import SessionMemory
from services.scenario_simulator import ScenarioSimulator
from utils.helpers import (
    allowed_file, generate_unique_filename, badge_class, safe_json_dumps,
    sanitize_text, coerce_float, coerce_int, error_response, success_response,
    is_safe_float,
)
from config import ELECTRICITY_RATE, AGENT_INSTRUCTIONS, APP_NAME, APP_VERSION

logger = logging.getLogger(__name__)

main = Blueprint("main", __name__)


# ─────────────────────────────────────────────────────────────────────────────
# Singletons — one instance shared across requests in a worker process
# ─────────────────────────────────────────────────────────────────────────────

_orchestrator: AgentOrchestrator = None
_scenario = ScenarioSimulator()


def get_orchestrator() -> AgentOrchestrator:
    """Return the shared AgentOrchestrator, initialising it on first call."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = AgentOrchestrator()
    return _orchestrator


# ─────────────────────────────────────────────────────────────────────────────
# Session helpers
# ─────────────────────────────────────────────────────────────────────────────

def get_memory() -> SessionMemory:
    """Return a SessionMemory view of the current Flask session."""
    return SessionMemory()


def get_analysis() -> dict:
    """
    Return the cached, enriched analysis dict from the session.
    Builds a fresh demo analysis on first access.
    """
    if "analysis" not in session:
        try:
            analyzer = EnergyAnalyzer(electricity_rate=_get_rate())
            raw = analyzer.run_full_analysis()
            session["analysis"] = get_orchestrator().enrich_analysis(raw)
        except Exception as exc:
            logger.error("Failed to initialise demo analysis: %s", exc)
            session["analysis"] = {}
    return session["analysis"]


def _get_rate() -> float:
    """Return the user's configured electricity rate from the session."""
    return coerce_float(session.get("electricity_rate"), default=ELECTRICITY_RATE)


def _save_report(report: dict) -> None:
    """Prepend a report to the session history, keeping the most recent 30."""
    reports = session.get("reports", [])
    reports.insert(0, report)
    session["reports"] = reports[:30]


# ─────────────────────────────────────────────────────────────────────────────
# Page Routes
# ─────────────────────────────────────────────────────────────────────────────

@main.route("/")
def dashboard():
    return render_template(
        "dashboard.html",
        analysis    = get_analysis(),
        ai_insights = session.get("quick_insights", ""),
        badge_class = badge_class,
    )


@main.route("/chat")
def chat():
    return render_template(
        "chat.html",
        ai_ready     = get_orchestrator().is_ready,
        conversation = session.get("conversation", []),
        user_profile = get_memory().get_profile(),
    )


@main.route("/upload")
def upload():
    return render_template("upload.html")


@main.route("/analysis")
def analysis():
    a = get_analysis()
    return render_template(
        "analysis.html",
        analysis      = a,
        analysis_json = safe_json_dumps(a),
    )


@main.route("/reports")
def reports():
    return render_template(
        "reports.html",
        reports = session.get("reports", []),
    )


@main.route("/reports/<case_id>")
def report_detail(case_id):
    # Sanitise path parameter to prevent injection
    safe_id = sanitize_text(case_id, max_length=40)
    rpts    = session.get("reports", [])
    report  = next((r for r in rpts if r.get("case_id") == safe_id), None)
    if not report:
        flash("Report not found. It may have expired with your session.", "warning")
        return redirect(url_for("main.reports"))
    return render_template(
        "report_detail.html",
        report      = report,
        badge_class = badge_class,
    )


@main.route("/recommendations")
def recommendations():
    return render_template(
        "recommendations.html",
        rec_data = session.get("recommendations"),
        analysis = get_analysis(),
        ai_ready = get_orchestrator().is_ready,
    )


@main.route("/simulator")
def simulator():
    return render_template(
        "simulator.html",
        analysis = get_analysis(),
        ai_ready = get_orchestrator().is_ready,
    )


@main.route("/settings")
def settings():
    return render_template(
        "settings.html",
        app_version         = APP_VERSION,
        agent_instructions  = AGENT_INSTRUCTIONS,
        current_rate        = _get_rate(),
        current_currency    = session.get("currency", AGENT_INSTRUCTIONS["currency_symbol"]),
        ai_ready            = get_orchestrator().is_ready,
        user_profile        = get_memory().get_profile(),
    )


# ─────────────────────────────────────────────────────────────────────────────
# API: Chat — full orchestrated conversation
# ─────────────────────────────────────────────────────────────────────────────

@main.route("/api/chat", methods=["POST"])
def api_chat():
    try:
        data    = request.get_json(force=True) or {}
        message = sanitize_text(data.get("message", ""), max_length=500)
        if not message:
            return error_response("Message cannot be empty.")

        result = get_orchestrator().handle_message(
            message          = message,
            raw_analysis     = get_analysis(),
            memory           = get_memory(),
            electricity_rate = _get_rate(),
        )

        session["analysis"] = result["analysis"]

        report_id = None
        if result.get("report"):
            _save_report(result["report"])
            report_id = result["report"]["case_id"]

        return success_response({
            "response":  result["ai_response"],
            "intent":    result["intent"],
            "report_id": report_id,
        })

    except Exception as exc:
        logger.exception("Chat endpoint error: %s", exc)
        return error_response("The AI service encountered an error. Please try again.", 500)


# ─────────────────────────────────────────────────────────────────────────────
# API: Investigate — explicit investigation trigger
# ─────────────────────────────────────────────────────────────────────────────

@main.route("/api/investigate", methods=["POST"])
def api_investigate():
    try:
        data     = request.get_json(force=True) or {}
        question = sanitize_text(
            data.get("question", "Why is my electricity bill high?"),
            max_length=300,
        )
        result = get_orchestrator().run_investigation(
            question     = question,
            raw_analysis = get_analysis(),
            memory       = get_memory(),
        )
        session["analysis"] = result["analysis"]
        _save_report(result["report"])
        return success_response({"report": result["report"]})

    except Exception as exc:
        logger.exception("Investigation endpoint error: %s", exc)
        return error_response("Investigation could not be completed. Please try again.", 500)


# ─────────────────────────────────────────────────────────────────────────────
# API: Recommendations
# ─────────────────────────────────────────────────────────────────────────────

@main.route("/api/recommendations", methods=["POST"])
def api_recommendations():
    try:
        result = get_orchestrator().run_recommendations(
            raw_analysis = get_analysis(),
            memory       = get_memory(),
        )
        session["analysis"] = result["analysis"]
        session["recommendations"] = {
            "text":          result["ai_text"],
            "structured":    result["structured_recs"],
            "generated":     datetime.now().strftime("%Y-%m-%d %H:%M"),
            "analysis_kwh":  result["analysis"].get("total_monthly_kwh"),
            "analysis_cost": result["analysis"].get("total_monthly_cost"),
            "energy_score":  result["analysis"].get("energy_score"),
        }
        return success_response({
            "recommendations": result["ai_text"],
            "structured":      result["structured_recs"],
        })

    except Exception as exc:
        logger.exception("Recommendations endpoint error: %s", exc)
        return error_response("Recommendations could not be generated. Please try again.", 500)


# ─────────────────────────────────────────────────────────────────────────────
# API: Scenario simulation
# ─────────────────────────────────────────────────────────────────────────────

@main.route("/api/simulate", methods=["POST"])
def api_simulate():
    try:
        data  = request.get_json(force=True) or {}
        query = sanitize_text(data.get("query", ""), max_length=300)
        if not query:
            return error_response("No scenario query provided.")

        parsed       = _scenario.parse_scenario(query)
        analysis     = get_analysis()
        analyzer     = EnergyAnalyzer(electricity_rate=_get_rate())
        scenario_data = analyzer.simulate_scenario(
            appliance        = parsed["appliance"],
            change_hours     = parsed["change_hours"],
            current_analysis = analysis,
        )
        description = _scenario.build_scenario_description(parsed)
        result = get_orchestrator().run_scenario(
            query         = description,
            raw_analysis  = analysis,
            scenario_data = scenario_data,
            memory        = get_memory(),
        )
        return success_response({
            "scenario":     parsed,
            "impact":       scenario_data,
            "ai_reasoning": result["ai_reasoning"],
            "description":  description,
        })

    except Exception as exc:
        logger.exception("Simulation endpoint error: %s", exc)
        return error_response("Simulation could not be completed. Please try again.", 500)


# ─────────────────────────────────────────────────────────────────────────────
# API: CSV / Excel upload
# ─────────────────────────────────────────────────────────────────────────────

@main.route("/api/upload", methods=["POST"])
def api_upload():
    if "file" not in request.files:
        return error_response("No file was included in the request.")

    f = request.files["file"]
    if not f or not f.filename:
        return error_response("No file selected.")
    if not allowed_file(f.filename):
        return error_response(
            "Unsupported file type. Please upload a CSV or Excel (.xlsx) file."
        )

    try:
        fname    = generate_unique_filename(f.filename)
        filepath = os.path.join(current_app.config["UPLOAD_FOLDER"], fname)
        f.save(filepath)

        ext = fname.rsplit(".", 1)[1].lower()
        df  = pd.read_csv(filepath) if ext == "csv" else pd.read_excel(filepath)

        if df.empty:
            return error_response(
                "The uploaded file appears to be empty. Please check the file and try again."
            )
        if len(df) > 100_000:
            return error_response(
                "The file contains too many rows (max 100,000). Please upload a smaller dataset."
            )

        # Clean data: fill missing values, drop duplicates
        df = df.fillna(df.median(numeric_only=True)).fillna(df.mode().iloc[0])
        df = df.drop_duplicates()

        analyzer = EnergyAnalyzer(df=df, electricity_rate=_get_rate())
        raw      = analyzer.run_full_analysis()
        analysis = get_orchestrator().enrich_analysis(raw)
        stats    = get_orchestrator().validate_csv_stats(df, analysis)

        session["analysis"] = analysis
        session.pop("quick_insights", None)

        return success_response({
            "message":  f"Successfully analysed {stats['rows']:,} rows.",
            "analysis": analysis,
            "stats":    stats,
        })

    except pd.errors.ParserError:
        return error_response(
            "Could not parse the file. Please ensure it is a valid CSV or Excel file."
        )
    except Exception as exc:
        logger.exception("Upload processing error: %s", exc)
        return error_response(
            "An error occurred while processing the file. "
            "Please check the file format and try again."
        , 500)


# ─────────────────────────────────────────────────────────────────────────────
# API: Dashboard quick insights
# ─────────────────────────────────────────────────────────────────────────────

@main.route("/api/quick-insights", methods=["POST"])
def api_quick_insights():
    try:
        insights = get_orchestrator().quick_insights(get_analysis())
        session["quick_insights"] = insights
        return success_response({"insights": insights})
    except Exception as exc:
        logger.exception("Quick insights error: %s", exc)
        return error_response("Could not generate insights. Please try again.", 500)


# ─────────────────────────────────────────────────────────────────────────────
# API: Settings update
# ─────────────────────────────────────────────────────────────────────────────

@main.route("/api/settings", methods=["POST"])
def api_settings():
    try:
        data = request.get_json(force=True) or {}

        # Validate and sanitise electricity rate
        rate_raw = data.get("electricity_rate")
        if rate_raw is not None:
            if not is_safe_float(rate_raw, min_val=0.001, max_val=100):
                return error_response("Invalid electricity rate. Must be between 0.001 and 100.")
            session["electricity_rate"] = coerce_float(rate_raw, default=ELECTRICITY_RATE)

        # Currency symbol
        if data.get("currency") is not None:
            currency = sanitize_text(data["currency"], max_length=5) or "$"
            session["currency"] = currency

        # Update user profile via SessionMemory
        memory = get_memory()
        if data.get("location"):
            memory.set_location(sanitize_text(data["location"], max_length=100))
        if data.get("family_size"):
            memory.set_family_size(coerce_int(data["family_size"], default=0, min_val=1, max_val=20))
        if data.get("home_type"):
            memory.set_home_type(sanitize_text(data["home_type"], max_length=50))

        # New: energy savings goal and AI personality stored in session memory
        if data.get("savings_goal"):
            memory.set_preference("savings_goal",
                                  coerce_int(data["savings_goal"], default=20, min_val=1, max_val=50))
        if data.get("ai_personality"):
            allowed_personalities = {"professional", "friendly", "concise", "detailed"}
            personality = sanitize_text(data["ai_personality"], max_length=20).lower()
            if personality in allowed_personalities:
                memory.set_preference("ai_personality", personality)

        # Invalidate stale analysis when rate changes so it is recomputed
        if rate_raw is not None:
            session.pop("analysis", None)
            session.pop("quick_insights", None)

        return success_response({"message": "Settings saved."})

    except Exception as exc:
        logger.exception("Settings update error: %s", exc)
        return error_response("Could not save settings. Please try again.", 500)


# ─────────────────────────────────────────────────────────────────────────────
# API: Analysis data (used by chart refreshes)
# ─────────────────────────────────────────────────────────────────────────────

@main.route("/api/analysis-data")
def api_analysis_data():
    return success_response({"analysis": get_analysis()})


# ─────────────────────────────────────────────────────────────────────────────
# API: Demo mode — load / reload the built-in demo dataset
# ─────────────────────────────────────────────────────────────────────────────

@main.route("/api/demo", methods=["POST"])
def api_demo():
    """
    Explicitly reload the built-in demo dataset.

    Clears any previously uploaded user data and re-generates the demo
    analysis so users can experience all features without uploading a CSV.
    The demo badge in the topbar will re-appear after this call.
    """
    try:
        # Clear any previously uploaded user analysis
        session.pop("analysis", None)
        session.pop("quick_insights", None)
        session.pop("recommendations", None)

        # Generate a fresh demo analysis
        analyzer = EnergyAnalyzer(electricity_rate=_get_rate())
        raw      = analyzer.run_full_analysis()
        analysis = get_orchestrator().enrich_analysis(raw)
        session["analysis"] = analysis

        return success_response({
            "message":     "Demo mode activated. Showing built-in household energy dataset.",
            "data_source": analysis.get("data_source", "demo"),
            "appliances":  len(analysis.get("appliances", [])),
        })

    except Exception as exc:
        logger.exception("Demo mode error: %s", exc)
        return error_response("Could not load demo dataset. Please try again.", 500)


# ─────────────────────────────────────────────────────────────────────────────
# API: Session reset
# ─────────────────────────────────────────────────────────────────────────────

@main.route("/api/reset", methods=["POST"])
def api_reset():
    session.clear()
    return success_response({"message": "Session reset. All data cleared."})


# ─────────────────────────────────────────────────────────────────────────────
# Report PDF export
# ─────────────────────────────────────────────────────────────────────────────

@main.route("/reports/<case_id>/pdf")
def report_pdf(case_id):
    """Render a print-optimised HTML page that triggers the browser's print dialog."""
    safe_id = sanitize_text(case_id, max_length=40)
    rpts    = session.get("reports", [])
    report  = next((r for r in rpts if r.get("case_id") == safe_id), None)
    if not report:
        flash("Report not found.", "warning")
        return redirect(url_for("main.reports"))

    html = render_template(
        "report_pdf.html",
        report      = report,
        badge_class = badge_class,
        now         = datetime.now().strftime("%Y-%m-%d %H:%M"),
    )
    resp = make_response(html)
    resp.headers["Content-Type"] = "text/html; charset=utf-8"
    return resp
