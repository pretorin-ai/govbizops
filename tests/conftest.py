"""Shared fixtures for govbizops tests"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from govbizops.database import Base, Opportunity


@pytest.fixture
def mock_env(monkeypatch):
    """Patch common environment variables."""
    monkeypatch.setenv("SAM_GOV_API_KEY", "test-api-key-123")
    monkeypatch.setenv("SLACK_WEBHOOK_URL", "https://hooks.slack.com/services/T/B/X")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-openai-key")
    monkeypatch.setenv("CRM_API_KEY", "crm_test_key")
    monkeypatch.setenv("CRM_URL", "http://localhost:8000")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")


@pytest.fixture
def db_session():
    """Create an in-memory SQLite database session for tests."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


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
def sample_opportunity_row(db_session, sample_opportunity):
    """Insert a sample opportunity into the DB and return the row."""
    opp = Opportunity.from_api_response(sample_opportunity)
    db_session.add(opp)
    db_session.commit()
    return opp


@pytest.fixture
def flask_test_client():
    """Flask test client from simple_viewer.app."""
    from govbizops.simple_viewer import app

    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client
