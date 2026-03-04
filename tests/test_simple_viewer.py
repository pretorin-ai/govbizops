"""Tests for simple_viewer Flask routes"""

import json
import os
import pytest
from unittest.mock import patch, MagicMock

from govbizops.simple_viewer import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


class TestGetDataDir:
    def test_returns_data_path(self):
        from govbizops.simple_viewer import get_data_dir

        result = get_data_dir()
        assert result.endswith("data")


class TestIndex:
    def test_file_not_found(self, client, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "govbizops.simple_viewer.get_data_dir", lambda: str(tmp_path)
        )
        response = client.get("/")
        assert response.status_code == 200
        assert b"not found" in response.data

    def test_valid_json(self, client, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "govbizops.simple_viewer.get_data_dir", lambda: str(tmp_path)
        )
        data = {
            "abc123": {
                "collected_date": "2025-01-15T10:00:00",
                "data": {
                    "noticeId": "abc123",
                    "title": "Test Opp",
                    "postedDate": "2025-01-15",
                },
            }
        }
        (tmp_path / "opportunities.json").write_text(json.dumps(data))

        with patch("govbizops.simple_viewer.render_template") as mock_rt:
            mock_rt.return_value = "rendered"
            response = client.get("/")
        assert response.status_code == 200
        mock_rt.assert_called_once()

    def test_exception(self, client, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "govbizops.simple_viewer.get_data_dir", lambda: str(tmp_path)
        )
        (tmp_path / "opportunities.json").write_text("not valid json!")
        response = client.get("/")
        assert response.status_code == 200
        assert b"Error" in response.data


class TestExportOpportunity:
    def test_file_not_found(self, client, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "govbizops.simple_viewer.get_data_dir", lambda: str(tmp_path)
        )
        response = client.get("/export/abc123")
        assert response.status_code == 404

    def test_notice_id_not_found(self, client, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "govbizops.simple_viewer.get_data_dir", lambda: str(tmp_path)
        )
        data = {"other_id": {"collected_date": "2025-01-15", "data": {}}}
        (tmp_path / "opportunities.json").write_text(json.dumps(data))
        response = client.get("/export/abc123")
        assert response.status_code == 404

    def test_without_description(self, client, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "govbizops.simple_viewer.get_data_dir", lambda: str(tmp_path)
        )
        data = {
            "abc123": {
                "collected_date": "2025-01-15",
                "data": {"noticeId": "abc123", "title": "Test"},
            }
        }
        (tmp_path / "opportunities.json").write_text(json.dumps(data))
        response = client.get("/export/abc123")
        assert response.status_code == 200
        result = json.loads(response.data)
        assert result["noticeId"] == "abc123"

    def test_with_description_scrape_success(self, client, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "govbizops.simple_viewer.get_data_dir", lambda: str(tmp_path)
        )
        data = {
            "abc123": {
                "collected_date": "2025-01-15",
                "data": {
                    "noticeId": "abc123",
                    "uiLink": "https://sam.gov/opp/123/view",
                },
            }
        }
        (tmp_path / "opportunities.json").write_text(json.dumps(data))

        with patch(
            "govbizops.simple_viewer.scrape_sam_opportunity",
            return_value={"success": True, "description": "Scraped desc"},
        ):
            response = client.get("/export/abc123?description=true")
        assert response.status_code == 200
        result = json.loads(response.data)
        assert result["scraped_description"] == "Scraped desc"

    def test_with_description_scrape_fail(self, client, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "govbizops.simple_viewer.get_data_dir", lambda: str(tmp_path)
        )
        data = {
            "abc123": {
                "collected_date": "2025-01-15",
                "data": {
                    "noticeId": "abc123",
                    "uiLink": "https://sam.gov/opp/123/view",
                },
            }
        }
        (tmp_path / "opportunities.json").write_text(json.dumps(data))

        with patch(
            "govbizops.simple_viewer.scrape_sam_opportunity",
            return_value={"success": False, "description": None},
        ):
            response = client.get("/export/abc123?description=true")
        assert response.status_code == 200
        result = json.loads(response.data)
        assert result.get("scraping_note") == "Failed to scrape page"

    def test_with_description_scrape_exception(self, client, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "govbizops.simple_viewer.get_data_dir", lambda: str(tmp_path)
        )
        data = {
            "abc123": {
                "collected_date": "2025-01-15",
                "data": {
                    "noticeId": "abc123",
                    "uiLink": "https://sam.gov/opp/123/view",
                },
            }
        }
        (tmp_path / "opportunities.json").write_text(json.dumps(data))

        with patch(
            "govbizops.simple_viewer.scrape_sam_opportunity",
            side_effect=RuntimeError("browser crash"),
        ):
            response = client.get("/export/abc123?description=true")
        assert response.status_code == 200
        result = json.loads(response.data)
        assert "browser crash" in result.get("scraping_error", "")

    def test_with_description_cache_hit(self, client, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "govbizops.simple_viewer.get_data_dir", lambda: str(tmp_path)
        )
        data = {
            "abc123": {
                "collected_date": "2025-01-15",
                "data": {"noticeId": "abc123"},
                "scraped_description": "Cached description",
            }
        }
        (tmp_path / "opportunities.json").write_text(json.dumps(data))

        response = client.get("/export/abc123?description=true")
        assert response.status_code == 200
        result = json.loads(response.data)
        assert result["scraped_description"] == "Cached description"

    def test_general_exception(self, client, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "govbizops.simple_viewer.get_data_dir", lambda: str(tmp_path)
        )
        (tmp_path / "opportunities.json").write_text("not json!")
        response = client.get("/export/abc123")
        assert response.status_code == 500

    def test_scrape_success_no_description(self, client, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "govbizops.simple_viewer.get_data_dir", lambda: str(tmp_path)
        )
        data = {
            "abc123": {
                "collected_date": "2025-01-15",
                "data": {
                    "noticeId": "abc123",
                    "uiLink": "https://sam.gov/opp/123/view",
                },
            }
        }
        (tmp_path / "opportunities.json").write_text(json.dumps(data))

        with patch(
            "govbizops.simple_viewer.scrape_sam_opportunity",
            return_value={"success": True, "description": None},
        ):
            response = client.get("/export/abc123?description=true")
        assert response.status_code == 200
        result = json.loads(response.data)
        assert result.get("scraping_note") == "No description found on page"
