"""Tests for scripts/test_slack.py"""

import pytest
from unittest.mock import patch, MagicMock
import importlib
import sys


@pytest.fixture
def test_slack_module():
    """Import the test_slack script as a module."""
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "test_slack_script", "scripts/test_slack.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestTestSlackWebhook:
    def test_no_url(self, test_slack_module, monkeypatch, capsys):
        monkeypatch.delenv("SLACK_WEBHOOK_URL", raising=False)
        result = test_slack_module.test_slack_webhook()
        assert result is False
        captured = capsys.readouterr()
        assert "not found" in captured.out.lower() or "ERROR" in captured.out

    def test_success_200(self, test_slack_module, monkeypatch, capsys):
        monkeypatch.setenv("SLACK_WEBHOOK_URL", "https://hooks.slack.com/test")
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        with patch("requests.post", return_value=mock_resp):
            result = test_slack_module.test_slack_webhook()
        assert result is True
        captured = capsys.readouterr()
        assert "SUCCESS" in captured.out

    def test_error_status(self, test_slack_module, monkeypatch, capsys):
        monkeypatch.setenv("SLACK_WEBHOOK_URL", "https://hooks.slack.com/test")
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.text = "error"
        with patch("requests.post", return_value=mock_resp):
            result = test_slack_module.test_slack_webhook()
        assert result is False

    def test_timeout(self, test_slack_module, monkeypatch, capsys):
        import requests as req_mod

        monkeypatch.setenv("SLACK_WEBHOOK_URL", "https://hooks.slack.com/test")
        with patch(
            "requests.post", side_effect=req_mod.exceptions.Timeout("timed out")
        ):
            result = test_slack_module.test_slack_webhook()
        assert result is False
        captured = capsys.readouterr()
        assert "timed out" in captured.out.lower() or "Timeout" in captured.out

    def test_request_exception(self, test_slack_module, monkeypatch, capsys):
        import requests as req_mod

        monkeypatch.setenv("SLACK_WEBHOOK_URL", "https://hooks.slack.com/test")
        with patch(
            "requests.post",
            side_effect=req_mod.exceptions.ConnectionError("conn refused"),
        ):
            result = test_slack_module.test_slack_webhook()
        assert result is False

    def test_generic_exception(self, test_slack_module, monkeypatch, capsys):
        monkeypatch.setenv("SLACK_WEBHOOK_URL", "https://hooks.slack.com/test")
        with patch("requests.post", side_effect=RuntimeError("unexpected")):
            result = test_slack_module.test_slack_webhook()
        assert result is False
        captured = capsys.readouterr()
        assert "unexpected" in captured.out.lower() or "ERROR" in captured.out
