"""Tests for simple_viewer Flask routes"""

import json
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime

from govbizops.database import Opportunity


@pytest.fixture
def client(db_session):
    """Flask test client with mocked DB session."""
    from govbizops.simple_viewer import app

    app.config["TESTING"] = True

    with patch("govbizops.simple_viewer._get_db_session", return_value=db_session):
        with app.test_client() as c:
            yield c


class TestIndex:
    def test_no_opportunities(self, client):
        response = client.get("/")
        assert response.status_code == 200
        assert b"No opportunities" in response.data

    def test_with_opportunities(self, client, db_session):
        opp = Opportunity(
            notice_id="abc123",
            title="Test Opp",
            posted_date="2025-01-15",
            collected_date=datetime(2025, 1, 15, 10, 0, 0),
        )
        db_session.add(opp)
        db_session.commit()

        with patch("govbizops.simple_viewer.render_template") as mock_rt:
            mock_rt.return_value = "rendered"
            response = client.get("/")
        assert response.status_code == 200
        mock_rt.assert_called_once()


class TestExportOpportunity:
    def test_notice_id_not_found(self, client):
        response = client.get("/export/nonexistent")
        assert response.status_code == 404

    def test_without_description(self, client, db_session):
        opp = Opportunity(notice_id="abc123", title="Test")
        db_session.add(opp)
        db_session.commit()

        response = client.get("/export/abc123")
        assert response.status_code == 200
        result = json.loads(response.data)
        assert result["noticeId"] == "abc123"

    def test_with_description_scrape_success(self, client, db_session):
        opp = Opportunity(
            notice_id="abc123",
            ui_link="https://sam.gov/opp/123/view",
        )
        db_session.add(opp)
        db_session.commit()

        with patch(
            "govbizops.simple_viewer.scrape_sam_opportunity",
            return_value={"success": True, "description": "Scraped desc"},
        ):
            response = client.get("/export/abc123?description=true")
        assert response.status_code == 200
        result = json.loads(response.data)
        assert result["scraped_description"] == "Scraped desc"

    def test_with_description_scrape_fail(self, client, db_session):
        opp = Opportunity(
            notice_id="abc123",
            ui_link="https://sam.gov/opp/123/view",
        )
        db_session.add(opp)
        db_session.commit()

        with patch(
            "govbizops.simple_viewer.scrape_sam_opportunity",
            return_value={"success": False, "description": None},
        ):
            response = client.get("/export/abc123?description=true")
        assert response.status_code == 200
        result = json.loads(response.data)
        assert result.get("scraping_note") == "Failed to scrape page"

    def test_with_description_scrape_exception(self, client, db_session):
        opp = Opportunity(
            notice_id="abc123",
            ui_link="https://sam.gov/opp/123/view",
        )
        db_session.add(opp)
        db_session.commit()

        with patch(
            "govbizops.simple_viewer.scrape_sam_opportunity",
            side_effect=RuntimeError("browser crash"),
        ):
            response = client.get("/export/abc123?description=true")
        assert response.status_code == 200
        result = json.loads(response.data)
        assert "browser crash" in result.get("scraping_error", "")

    def test_with_description_cache_hit(self, client, db_session):
        opp = Opportunity(
            notice_id="abc123",
            scraped_description="Cached description",
        )
        db_session.add(opp)
        db_session.commit()

        response = client.get("/export/abc123?description=true")
        assert response.status_code == 200
        result = json.loads(response.data)
        assert result["scraped_description"] == "Cached description"

    def test_scrape_success_no_description(self, client, db_session):
        opp = Opportunity(
            notice_id="abc123",
            ui_link="https://sam.gov/opp/123/view",
        )
        db_session.add(opp)
        db_session.commit()

        with patch(
            "govbizops.simple_viewer.scrape_sam_opportunity",
            return_value={"success": True, "description": None},
        ):
            response = client.get("/export/abc123?description=true")
        assert response.status_code == 200
        result = json.loads(response.data)
        assert result.get("scraping_note") == "No description found on page"
