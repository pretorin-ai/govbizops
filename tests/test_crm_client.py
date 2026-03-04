"""Tests for CRMClient and push_to_crm"""

import json
import pytest
from unittest.mock import patch, MagicMock

from govbizops.crm_client import CRMClient, push_to_crm
from govbizops.database import Opportunity


class TestCRMClientInit:
    def test_url_trailing_slash_stripped(self):
        client = CRMClient("http://localhost:8000/", "key123")
        assert client.base_url == "http://localhost:8000"

    def test_headers_set(self):
        client = CRMClient("http://localhost:8000", "key123")
        assert client.session.headers["Authorization"] == "Bearer key123"


class TestLogin:
    def test_success(self):
        client = CRMClient("http://localhost:8000", "key")
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        with patch.object(client.session, "get", return_value=mock_resp):
            assert client.login() is True

    def test_auth_failure(self):
        client = CRMClient("http://localhost:8000", "bad-key")
        with patch.object(
            client.session, "get", side_effect=Exception("401 Unauthorized")
        ):
            assert client.login() is False


class TestImportOpportunities:
    def test_login_fail(self):
        client = CRMClient("http://localhost:8000", "key")
        with patch.object(client, "login", return_value=False):
            with pytest.raises(Exception, match="Failed to authenticate"):
                client.import_opportunities([{"noticeId": "1"}])

    def test_success(self):
        client = CRMClient("http://localhost:8000", "key")
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "contracts_created": 2,
            "contracts_skipped": 0,
            "contacts_created": 1,
            "errors": [],
        }
        mock_resp.raise_for_status.return_value = None
        with patch.object(client, "login", return_value=True):
            with patch.object(client.session, "post", return_value=mock_resp):
                result = client.import_opportunities(
                    [{"noticeId": "1", "title": "Test"}]
                )
        assert result["contracts_created"] == 2

    def test_errors_in_response(self):
        client = CRMClient("http://localhost:8000", "key")
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "contracts_created": 1,
            "contracts_skipped": 0,
            "contacts_created": 0,
            "errors": ["dup entry"],
        }
        mock_resp.raise_for_status.return_value = None
        with patch.object(client, "login", return_value=True):
            with patch.object(client.session, "post", return_value=mock_resp):
                result = client.import_opportunities([{"noticeId": "1"}])
        assert len(result["errors"]) == 1

    def test_post_exception(self):
        client = CRMClient("http://localhost:8000", "key")
        with patch.object(client, "login", return_value=True):
            with patch.object(
                client.session, "post", side_effect=Exception("connection refused")
            ):
                with pytest.raises(Exception, match="connection refused"):
                    client.import_opportunities([{"noticeId": "1"}])


class TestPushCollectedOpportunities:
    def test_success(self, db_session):
        client = CRMClient("http://localhost:8000", "key")
        db_session.add(Opportunity(notice_id="id1", title="Test"))
        db_session.commit()

        expected = {
            "contracts_created": 1,
            "contracts_skipped": 0,
            "contacts_created": 0,
        }
        with patch.object(client, "import_opportunities", return_value=expected):
            result = client.push_collected_opportunities(db_session)
        assert result["contracts_created"] == 1

    def test_empty_db(self, db_session):
        client = CRMClient("http://localhost:8000", "key")
        expected = {
            "contracts_created": 0,
            "contracts_skipped": 0,
            "contacts_created": 0,
        }
        with patch.object(client, "import_opportunities", return_value=expected):
            result = client.push_collected_opportunities(db_session)
        assert result["contracts_created"] == 0


class TestPushToCrm:
    def test_convenience_function(self, db_session):
        db_session.add(Opportunity(notice_id="id1"))
        db_session.commit()

        expected = {
            "contracts_created": 1,
            "contracts_skipped": 0,
            "contacts_created": 0,
        }
        with patch(
            "govbizops.crm_client.CRMClient.push_collected_opportunities",
            return_value=expected,
        ):
            result = push_to_crm("http://localhost:8000", "key", db_session)
        assert result["contracts_created"] == 1
