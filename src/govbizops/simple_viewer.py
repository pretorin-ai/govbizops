"""
Simple viewer for opportunities stored in the database.
"""

from flask import Flask, render_template, jsonify, request
from markupsafe import escape
import os
from importlib import resources
from dotenv import load_dotenv

from govbizops.sam_scraper import scrape_sam_opportunity
from govbizops.database import Opportunity, get_engine, get_session, init_db

load_dotenv()

# Configure Flask to use the package templates folder
_templates_ref = resources.files("govbizops").joinpath("templates")
template_folder = str(_templates_ref)
app = Flask(__name__, template_folder=template_folder, static_folder=template_folder)

# Database setup — lazily initialized
_SessionFactory = None


def _get_db_session():
    """Get a database session, initializing the engine on first call."""
    global _SessionFactory
    if _SessionFactory is None:
        engine = get_engine()
        init_db(engine)
        _SessionFactory = get_session(engine)
    return _SessionFactory()


@app.route("/")
def index():
    """Display opportunities from the database."""
    try:
        session = _get_db_session()
        results = (
            session.query(Opportunity)
            .order_by(Opportunity.posted_date.desc())
            .all()
        )

        if not results:
            return "<h1>No opportunities</h1><p>Run the collector first.</p>"

        opportunities = []
        for opp in results:
            d = opp.to_dict()
            d["_collected_date"] = opp.collected_date.isoformat() if opp.collected_date else ""
            opportunities.append(d)

        return render_template(
            "simple_viewer.html", opportunities=opportunities, total=len(opportunities)
        )

    except Exception as e:
        return f"<h1>Error</h1><p>Error reading opportunities: {escape(str(e))}</p>"
    finally:
        if "session" in locals():
            session.close()


@app.route("/export/<notice_id>")
def export_opportunity(notice_id):
    """Export a single opportunity as JSON, optionally with scraped description"""
    include_description = request.args.get("description", "false").lower() == "true"

    try:
        session = _get_db_session()
        opp = session.query(Opportunity).filter(Opportunity.notice_id == notice_id).first()

        if opp is None:
            return jsonify({"error": "Opportunity not found"}), 404

        opportunity = opp.to_dict()

        if include_description:
            if not opp.scraped_description:
                url = opp.ui_link
                if url:
                    try:
                        scraped_data = scrape_sam_opportunity(url)

                        if scraped_data and scraped_data.get("success"):
                            description = scraped_data.get("description")
                            if description:
                                opp.scraped_description = description
                                session.commit()
                                opportunity["scraped_description"] = description
                            else:
                                opportunity["scraping_note"] = (
                                    "No description found on page"
                                )
                        else:
                            opportunity["scraping_note"] = "Failed to scrape page"
                    except Exception as e:
                        opportunity["scraping_error"] = str(e)
            else:
                opportunity["scraped_description"] = opp.scraped_description

        return jsonify(opportunity)

    except Exception as e:
        return jsonify({"error": f"Export failed: {str(e)}"}), 500
    finally:
        if "session" in locals():
            session.close()


if __name__ == "__main__":
    print("Simple Viewer Configuration:")
    print("Starting web viewer on http://localhost:5000")
    app.run(debug=True, port=5000)
