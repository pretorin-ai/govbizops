"""Shared fixtures for govbizops tests"""

import json
import os
import pytest
from unittest.mock import patch


@pytest.fixture
def mock_env(monkeypatch):
    """Patch common environment variables."""
    monkeypatch.setenv("SAM_GOV_API_KEY", "test-api-key-123")
    monkeypatch.setenv("SLACK_WEBHOOK_URL", "https://hooks.slack.com/services/T/B/X")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-openai-key")
    monkeypatch.setenv("CRM_API_KEY", "crm_test_key")
    monkeypatch.setenv("CRM_URL", "http://localhost:8000")


@pytest.fixture
def sample_opportunity():
    """Return a realistic SAM.gov opportunity dict."""
    return {
        "noticeId": "abc123def456",
        "title": "IT Support Services for Agency X",
        "solicitationNumber": "SOL-2025-001",
        "type": "Solicitation",
        "postedDate": "2025-01-15",
        "responseDeadLine": "2025-02-15T17:00:00-05:00",
        "naicsCode": "541511",
        "pscCode": "D310",
        "uiLink": "https://sam.gov/opp/abc123def456abc123def456abc12345/view",
        "description": "https://api.sam.gov/opportunities/v1/noticedesc?noticeid=abc123",
        "organizationName": "Department of Testing",
        "officeAddress": "123 Test St, Washington DC",
        "pointOfContact": [{"name": "John Doe", "email": "john@test.gov"}],
        "typeOfSetAside": "Small Business",
        "typeOfContract": "Firm Fixed Price",
    }


@pytest.fixture
def sample_opportunities_store(sample_opportunity):
    """Return stored format {noticeId: {collected_date, data}}."""
    return {
        sample_opportunity["noticeId"]: {
            "collected_date": "2025-01-16T10:00:00",
            "data": sample_opportunity,
        }
    }


@pytest.fixture
def tmp_json_file(tmp_path, sample_opportunities_store):
    """Create a temp JSON file with sample opportunity data."""
    fp = tmp_path / "opportunities.json"
    fp.write_text(json.dumps(sample_opportunities_store, indent=2))
    return fp


@pytest.fixture
def flask_test_client():
    """Flask test client from simple_viewer.app."""
    from govbizops.simple_viewer import app

    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client
