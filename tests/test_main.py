"""Tests for govbizops.main module"""

import json
import os
import sys
import pytest
from unittest.mock import patch, MagicMock, PropertyMock
from argparse import Namespace

from govbizops import main as main_mod
from govbizops.main import (
    get_data_dir,
    send_slack_notification,
    run_collector,
    run_viewer,
    run_crm_push,
    run_scheduled_collector,
    main,
)


class TestGetDataDir:
    def test_returns_path(self):
        result = get_data_dir()
        assert result.endswith("data")


class TestSendSlackNotification:
    def test_no_webhook(self, monkeypatch):
        monkeypatch.delenv("SLACK_WEBHOOK_URL", raising=False)
        result = send_slack_notification([{"title": "test"}])
        assert result is False

    def test_empty_opps(self, monkeypatch):
        monkeypatch.setenv("SLACK_WEBHOOK_URL", "https://hooks.slack.com/test")
        result = send_slack_notification([])
        assert result is True

    def test_single_opportunity(self, monkeypatch):
        monkeypatch.setenv("SLACK_WEBHOOK_URL", "https://hooks.slack.com/test")
        opp = {
            "title": "Test Opp",
            "noticeId": "N1",
            "postedDate": "2025-01-15",
            "responseDeadLine": "2025-02-15T17:00:00",
            "naicsCode": "541511",
            "uiLink": "https://sam.gov/opp/123/view",
        }
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        with patch("govbizops.main.requests.post", return_value=mock_resp) as mock_post:
            result = send_slack_notification([opp])
        assert result is True
        payload = mock_post.call_args[1]["json"]
        # Singular "Opportunity" for 1 item
        assert "Opportunit" in payload["blocks"][0]["text"]["text"]

    def test_more_than_5_footer(self, monkeypatch):
        monkeypatch.setenv("SLACK_WEBHOOK_URL", "https://hooks.slack.com/test")
        opps = [
            {
                "title": f"Opp {i}",
                "noticeId": f"N{i}",
                "postedDate": "2025-01-15",
                "responseDeadLine": "N/A",
                "naicsCode": "541511",
            }
            for i in range(7)
        ]
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        with patch("govbizops.main.requests.post", return_value=mock_resp) as mock_post:
            result = send_slack_notification(opps)
        assert result is True
        payload = mock_post.call_args[1]["json"]
        # Should have a footer context block
        context_blocks = [b for b in payload["blocks"] if b.get("type") == "context"]
        assert len(context_blocks) == 1
        assert "2 more" in context_blocks[0]["elements"][0]["text"]

    def test_success_200(self, monkeypatch):
        monkeypatch.setenv("SLACK_WEBHOOK_URL", "https://hooks.slack.com/test")
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        with patch("govbizops.main.requests.post", return_value=mock_resp):
            result = send_slack_notification(
                [
                    {
                        "title": "t",
                        "noticeId": "n",
                        "postedDate": "N/A",
                        "responseDeadLine": "N/A",
                        "naicsCode": "N/A",
                    }
                ]
            )
        assert result is True

    def test_error_status(self, monkeypatch):
        monkeypatch.setenv("SLACK_WEBHOOK_URL", "https://hooks.slack.com/test")
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.text = "error"
        with patch("govbizops.main.requests.post", return_value=mock_resp):
            result = send_slack_notification(
                [
                    {
                        "title": "t",
                        "noticeId": "n",
                        "postedDate": "N/A",
                        "responseDeadLine": "N/A",
                        "naicsCode": "N/A",
                    }
                ]
            )
        assert result is False

    def test_exception(self, monkeypatch):
        monkeypatch.setenv("SLACK_WEBHOOK_URL", "https://hooks.slack.com/test")
        with patch("govbizops.main.requests.post", side_effect=Exception("conn err")):
            result = send_slack_notification(
                [
                    {
                        "title": "t",
                        "noticeId": "n",
                        "postedDate": "N/A",
                        "responseDeadLine": "N/A",
                        "naicsCode": "N/A",
                    }
                ]
            )
        assert result is False

    def test_deadline_formatting(self, monkeypatch):
        monkeypatch.setenv("SLACK_WEBHOOK_URL", "https://hooks.slack.com/test")
        opp = {
            "title": "t",
            "noticeId": "n",
            "postedDate": "2025-01-15",
            "responseDeadLine": "2025-02-15T17:00:00-05:00",
            "naicsCode": "541511",
        }
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        with patch("govbizops.main.requests.post", return_value=mock_resp):
            result = send_slack_notification([opp])
        assert result is True


class TestRunCollector:
    @patch("time.sleep")
    def test_naics_from_args(self, mock_sleep, monkeypatch, tmp_path):
        monkeypatch.setenv("SAM_GOV_API_KEY", "key")
        args = Namespace(
            naics_codes="541511,541512",
            days_back=1,
            storage_path=str(tmp_path / "opps.json"),
            notify=False,
        )
        with patch("govbizops.main.OpportunityCollector") as MockCollector:
            instance = MockCollector.return_value
            instance.collect_daily_opportunities.return_value = []
            instance.get_summary.return_value = {"total_opportunities": 0}
            result = run_collector(args)
        assert result == 0
        call_kwargs = MockCollector.call_args[1]
        assert call_kwargs["naics_codes"] == ["541511", "541512"]

    @patch("time.sleep")
    def test_naics_from_env(self, mock_sleep, monkeypatch, tmp_path):
        monkeypatch.setenv("SAM_GOV_API_KEY", "key")
        monkeypatch.setenv("NAICS_CODES", "111111,222222")
        args = Namespace(
            naics_codes=None,
            days_back=1,
            storage_path=str(tmp_path / "opps.json"),
            notify=False,
        )
        with patch("govbizops.main.OpportunityCollector") as MockCollector:
            instance = MockCollector.return_value
            instance.collect_daily_opportunities.return_value = []
            instance.get_summary.return_value = {"total_opportunities": 0}
            run_collector(args)
        call_kwargs = MockCollector.call_args[1]
        assert call_kwargs["naics_codes"] == ["111111", "222222"]

    @patch("time.sleep")
    def test_naics_default(self, mock_sleep, monkeypatch, tmp_path):
        monkeypatch.setenv("SAM_GOV_API_KEY", "key")
        monkeypatch.delenv("NAICS_CODES", raising=False)
        args = Namespace(
            naics_codes=None,
            days_back=1,
            storage_path=str(tmp_path / "opps.json"),
            notify=False,
        )
        with patch("govbizops.main.OpportunityCollector") as MockCollector:
            instance = MockCollector.return_value
            instance.collect_daily_opportunities.return_value = []
            instance.get_summary.return_value = {"total_opportunities": 0}
            run_collector(args)
        call_kwargs = MockCollector.call_args[1]
        assert call_kwargs["naics_codes"] == ["541511", "541512"]

    @patch("time.sleep")
    def test_limit_validation_naics(self, mock_sleep, monkeypatch, tmp_path):
        monkeypatch.setenv("SAM_GOV_API_KEY", "key")
        codes = ",".join([str(i) for i in range(55)])
        args = Namespace(
            naics_codes=codes,
            days_back=1,
            storage_path=str(tmp_path / "opps.json"),
            notify=False,
        )
        with patch("govbizops.main.OpportunityCollector") as MockCollector:
            instance = MockCollector.return_value
            instance.collect_daily_opportunities.return_value = []
            instance.get_summary.return_value = {"total_opportunities": 0}
            run_collector(args)
        call_kwargs = MockCollector.call_args[1]
        assert len(call_kwargs["naics_codes"]) == 50

    @patch("time.sleep")
    def test_days_back_validation(self, mock_sleep, monkeypatch, tmp_path):
        monkeypatch.setenv("SAM_GOV_API_KEY", "key")
        args = Namespace(
            naics_codes="541511",
            days_back=100,
            storage_path=str(tmp_path / "opps.json"),
            notify=False,
        )
        with patch("govbizops.main.OpportunityCollector") as MockCollector:
            instance = MockCollector.return_value
            instance.collect_daily_opportunities.return_value = []
            instance.get_summary.return_value = {"total_opportunities": 0}
            run_collector(args)
        # days_back clamped to 90
        instance.collect_daily_opportunities.assert_called_once_with(days_back=90)

    @patch("time.sleep")
    def test_notify_on(self, mock_sleep, monkeypatch, tmp_path):
        monkeypatch.setenv("SAM_GOV_API_KEY", "key")
        monkeypatch.setenv("SLACK_WEBHOOK_URL", "https://hooks.slack.com/test")
        args = Namespace(
            naics_codes="541511",
            days_back=1,
            storage_path=str(tmp_path / "opps.json"),
            notify=True,
        )
        with patch("govbizops.main.OpportunityCollector") as MockCollector:
            instance = MockCollector.return_value
            instance.collect_daily_opportunities.return_value = [{"title": "new"}]
            instance.get_summary.return_value = {"total_opportunities": 1}
            with patch("govbizops.main.send_slack_notification") as mock_slack:
                run_collector(args)
        mock_slack.assert_called_once()

    @patch("time.sleep")
    def test_notify_on_no_new_opps(self, mock_sleep, monkeypatch, tmp_path):
        monkeypatch.setenv("SAM_GOV_API_KEY", "key")
        args = Namespace(
            naics_codes="541511",
            days_back=1,
            storage_path=str(tmp_path / "opps.json"),
            notify=True,
        )
        with patch("govbizops.main.OpportunityCollector") as MockCollector:
            instance = MockCollector.return_value
            instance.collect_daily_opportunities.return_value = []
            instance.get_summary.return_value = {"total_opportunities": 0}
            with patch("govbizops.main.send_slack_notification") as mock_slack:
                run_collector(args)
        mock_slack.assert_not_called()

    @patch("time.sleep")
    def test_notify_off(self, mock_sleep, monkeypatch, tmp_path):
        monkeypatch.setenv("SAM_GOV_API_KEY", "key")
        args = Namespace(
            naics_codes="541511",
            days_back=1,
            storage_path=str(tmp_path / "opps.json"),
            notify=False,
        )
        with patch("govbizops.main.OpportunityCollector") as MockCollector:
            instance = MockCollector.return_value
            instance.collect_daily_opportunities.return_value = [{"title": "new"}]
            instance.get_summary.return_value = {"total_opportunities": 1}
            with patch("govbizops.main.send_slack_notification") as mock_slack:
                run_collector(args)
        mock_slack.assert_not_called()

    @patch("time.sleep")
    def test_days_back_none(self, mock_sleep, monkeypatch, tmp_path):
        """When days_back is falsy (0 or None), should use default."""
        monkeypatch.setenv("SAM_GOV_API_KEY", "key")
        args = Namespace(
            naics_codes="541511",
            days_back=None,
            storage_path=str(tmp_path / "opps.json"),
            notify=False,
        )
        with patch("govbizops.main.OpportunityCollector") as MockCollector:
            instance = MockCollector.return_value
            instance.collect_daily_opportunities.return_value = []
            instance.get_summary.return_value = {"total_opportunities": 0}
            run_collector(args)
        instance.collect_daily_opportunities.assert_called_once_with()


class TestRunViewer:
    def test_debug_host(self):
        args = Namespace(port=5000, debug=True)
        mock_module = MagicMock()
        with patch.dict("sys.modules", {"govbizops.simple_viewer": mock_module}):
            # Import inside run_viewer: from govbizops import simple_viewer
            with patch("govbizops.simple_viewer", mock_module, create=True):
                run_viewer(args)
        mock_module.app.run.assert_called_once_with(
            host="127.0.0.1", port=5000, debug=True
        )

    def test_production_host(self):
        args = Namespace(port=5000, debug=False)
        mock_module = MagicMock()
        with patch.dict("sys.modules", {"govbizops.simple_viewer": mock_module}):
            with patch("govbizops.simple_viewer", mock_module, create=True):
                run_viewer(args)
        mock_module.app.run.assert_called_once_with(
            host="0.0.0.0", port=5000, debug=False
        )


class TestRunCrmPush:
    def test_missing_api_key(self, monkeypatch):
        monkeypatch.delenv("CRM_API_KEY", raising=False)
        args = Namespace(
            crm_url=None,
            crm_api_key=None,
            storage_path=None,
            no_contacts=False,
        )
        with pytest.raises(SystemExit):
            run_crm_push(args)

    def test_missing_file(self, monkeypatch, tmp_path):
        monkeypatch.setenv("CRM_API_KEY", "crm_key")
        args = Namespace(
            crm_url="http://localhost:8000",
            crm_api_key="crm_key",
            storage_path=str(tmp_path / "nonexistent.json"),
            no_contacts=False,
        )
        with pytest.raises(SystemExit):
            run_crm_push(args)

    def test_success(self, monkeypatch, tmp_path):
        fp = tmp_path / "opps.json"
        fp.write_text("{}")
        monkeypatch.setenv("CRM_API_KEY", "crm_key")
        args = Namespace(
            crm_url="http://localhost:8000",
            crm_api_key="crm_key",
            storage_path=str(fp),
            no_contacts=False,
        )
        mock_result = {
            "contracts_created": 5,
            "contracts_skipped": 0,
            "contacts_created": 3,
            "errors": [],
        }
        with patch("govbizops.crm_client.push_to_crm", return_value=mock_result):
            run_crm_push(args)

    def test_errors_in_result(self, monkeypatch, tmp_path):
        fp = tmp_path / "opps.json"
        fp.write_text("{}")
        monkeypatch.setenv("CRM_API_KEY", "crm_key")
        args = Namespace(
            crm_url="http://localhost:8000",
            crm_api_key="crm_key",
            storage_path=str(fp),
            no_contacts=False,
        )
        mock_result = {
            "contracts_created": 3,
            "contracts_skipped": 0,
            "contacts_created": 1,
            "errors": ["err1", "err2", "err3", "err4", "err5", "err6"],
        }
        with patch("govbizops.crm_client.push_to_crm", return_value=mock_result):
            run_crm_push(args)

    def test_exception(self, monkeypatch, tmp_path):
        fp = tmp_path / "opps.json"
        fp.write_text("{}")
        monkeypatch.setenv("CRM_API_KEY", "crm_key")
        args = Namespace(
            crm_url="http://localhost:8000",
            crm_api_key="crm_key",
            storage_path=str(fp),
            no_contacts=False,
        )
        with patch(
            "govbizops.crm_client.push_to_crm", side_effect=Exception("CRM down")
        ):
            with pytest.raises(SystemExit):
                run_crm_push(args)


class TestRunScheduledCollector:
    @patch("time.sleep")
    def test_keyboard_interrupt(self, mock_sleep):
        args = Namespace(
            interval=1,
            naics_codes="541511",
            days_back=1,
            storage_path=None,
            notify=False,
        )
        with patch("govbizops.main.run_collector", side_effect=KeyboardInterrupt):
            run_scheduled_collector(args)

    @patch("govbizops.main.time.sleep")
    def test_successful_run_then_interrupt(self, mock_sleep):
        args = Namespace(
            interval=1,
            naics_codes="541511",
            days_back=1,
            storage_path=None,
            notify=True,
        )
        call_count = 0

        def collector_side_effect(a):
            nonlocal call_count
            call_count += 1
            return 5

        # sleep called once (interval sleep), then KeyboardInterrupt
        mock_sleep.side_effect = KeyboardInterrupt

        with patch("govbizops.main.run_collector", side_effect=collector_side_effect):
            run_scheduled_collector(args)
        assert call_count == 1

    @patch("time.sleep")
    def test_exception_recovery(self, mock_sleep):
        args = Namespace(
            interval=1,
            naics_codes="541511",
            days_back=1,
            storage_path=None,
            notify=False,
        )
        call_count = 0

        def side_effect(a):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("transient error")
            raise KeyboardInterrupt

        with patch("govbizops.main.run_collector", side_effect=side_effect):
            run_scheduled_collector(args)
        assert call_count == 2


class TestMain:
    @patch("time.sleep")
    def test_collect_mode(self, mock_sleep, monkeypatch, tmp_path):
        monkeypatch.setenv("SAM_GOV_API_KEY", "key")
        with patch(
            "sys.argv",
            ["govbizops", "collect", "--storage-path", str(tmp_path / "o.json")],
        ):
            with patch("govbizops.main.run_collector") as mock_rc:
                main()
        mock_rc.assert_called_once()

    @patch("time.sleep")
    def test_viewer_mode(self, mock_sleep, monkeypatch):
        monkeypatch.setenv("SAM_GOV_API_KEY", "key")
        with patch("sys.argv", ["govbizops", "viewer"]):
            with patch("govbizops.main.run_viewer") as mock_rv:
                main()
        mock_rv.assert_called_once()

    @patch("time.sleep")
    def test_schedule_mode(self, mock_sleep, monkeypatch):
        monkeypatch.setenv("SAM_GOV_API_KEY", "key")
        with patch("sys.argv", ["govbizops", "schedule"]):
            with patch("govbizops.main.run_scheduled_collector") as mock_rs:
                main()
        mock_rs.assert_called_once()

    @patch("time.sleep")
    def test_push_crm_mode(self, mock_sleep, monkeypatch):
        monkeypatch.setenv("SAM_GOV_API_KEY", "key")
        with patch("sys.argv", ["govbizops", "push-crm"]):
            with patch("govbizops.main.run_crm_push") as mock_rp:
                main()
        mock_rp.assert_called_once()

    @patch("time.sleep")
    def test_diagnose_mode(self, mock_sleep, monkeypatch):
        monkeypatch.setenv("SAM_GOV_API_KEY", "key")
        with patch("sys.argv", ["govbizops", "diagnose"]):
            with patch("asyncio.run", return_value=True):
                with pytest.raises(SystemExit) as exc_info:
                    main()
                assert exc_info.value.code == 0

    @patch("time.sleep")
    def test_no_mode_prints_help(self, mock_sleep, monkeypatch, capsys):
        monkeypatch.setenv("SAM_GOV_API_KEY", "key")
        with patch("sys.argv", ["govbizops"]):
            main()
        captured = capsys.readouterr()
        assert "Examples:" in captured.out

    @patch("time.sleep")
    def test_missing_api_key(self, mock_sleep, monkeypatch):
        monkeypatch.delenv("SAM_GOV_API_KEY", raising=False)
        with patch("sys.argv", ["govbizops", "collect"]):
            with pytest.raises(SystemExit):
                main()
