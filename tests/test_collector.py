"""Tests for OpportunityCollector"""

import json
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
from pathlib import Path

from govbizops.collector import OpportunityCollector


@pytest.fixture
def collector(tmp_path):
    """Create a collector with a temp storage path."""
    with patch("time.sleep"):
        c = OpportunityCollector(
            api_key="test-key",
            naics_codes=["541511"],
            storage_path=str(tmp_path / "opps.json"),
        )
    return c


class TestInit:
    def test_valid_init(self, tmp_path):
        with patch("time.sleep"):
            c = OpportunityCollector(
                api_key="key",
                naics_codes=["541511", "541512"],
                storage_path=str(tmp_path / "opps.json"),
            )
        assert c.naics_codes == ["541511", "541512"]

    def test_too_many_naics(self, tmp_path):
        codes = [str(i) for i in range(51)]
        with pytest.raises(ValueError, match="Maximum 50"):
            OpportunityCollector("key", codes, str(tmp_path / "opps.json"))

    def test_loads_existing_storage(self, tmp_path):
        fp = tmp_path / "opps.json"
        fp.write_text(json.dumps({"id1": {"collected_date": "2025-01-01", "data": {}}}))
        with patch("time.sleep"):
            c = OpportunityCollector("key", ["541511"], str(fp))
        assert "id1" in c.opportunities


class TestLoadOpportunities:
    def test_file_exists_valid(self, tmp_path):
        fp = tmp_path / "opps.json"
        fp.write_text(json.dumps({"a": 1}))
        with patch("time.sleep"):
            c = OpportunityCollector("key", ["541511"], str(fp))
        assert c.opportunities == {"a": 1}

    def test_file_exists_invalid_json(self, tmp_path):
        fp = tmp_path / "opps.json"
        fp.write_text("not json!")
        with patch("time.sleep"):
            c = OpportunityCollector("key", ["541511"], str(fp))
        assert c.opportunities == {}

    def test_file_missing(self, tmp_path):
        with patch("time.sleep"):
            c = OpportunityCollector("key", ["541511"], str(tmp_path / "missing.json"))
        assert c.opportunities == {}


class TestSaveOpportunities:
    def test_success(self, collector, tmp_path):
        collector.opportunities = {"id1": {"data": "test"}}
        collector._save_opportunities()
        saved = json.loads(Path(collector.storage_path).read_text())
        assert "id1" in saved

    def test_write_error(self, collector):
        collector.storage_path = Path("/nonexistent/dir/file.json")
        collector.opportunities = {"id1": {"data": "test"}}
        # Should not raise, just logs
        collector._save_opportunities()


class TestCollectDailyOpportunities:
    @patch("time.sleep")
    def test_new_opps_found(self, mock_sleep, collector):
        mock_opps = [
            {"noticeId": "new1", "type": "Solicitation"},
            {"noticeId": "new2", "type": "Solicitation"},
        ]
        with patch.object(
            collector.client, "get_all_opportunities", return_value=mock_opps
        ):
            result = collector.collect_daily_opportunities()
        assert len(result) == 2
        assert "new1" in collector.opportunities
        assert "new2" in collector.opportunities

    @patch("time.sleep")
    def test_duplicates_filtered(self, mock_sleep, collector):
        collector.opportunities["existing"] = {
            "collected_date": "2025-01-01",
            "data": {"noticeId": "existing"},
        }
        mock_opps = [
            {"noticeId": "existing", "type": "Solicitation"},
            {"noticeId": "new1", "type": "Solicitation"},
        ]
        with patch.object(
            collector.client, "get_all_opportunities", return_value=mock_opps
        ):
            result = collector.collect_daily_opportunities()
        assert len(result) == 1
        assert result[0]["noticeId"] == "new1"

    @patch("time.sleep")
    def test_non_solicitation_filtered(self, mock_sleep, collector):
        mock_opps = [
            {"noticeId": "s1", "type": "Solicitation"},
            {"noticeId": "a1", "type": "Award Notice"},
        ]
        with patch.object(
            collector.client, "get_all_opportunities", return_value=mock_opps
        ):
            result = collector.collect_daily_opportunities()
        assert len(result) == 1
        assert result[0]["noticeId"] == "s1"

    @patch("time.sleep")
    def test_no_notice_id_skipped(self, mock_sleep, collector):
        mock_opps = [{"type": "Solicitation"}]  # no noticeId
        with patch.object(
            collector.client, "get_all_opportunities", return_value=mock_opps
        ):
            result = collector.collect_daily_opportunities()
        assert len(result) == 0

    def test_days_back_limit(self, collector):
        with pytest.raises(ValueError, match="Maximum 90"):
            collector.collect_daily_opportunities(days_back=91)

    @patch("time.sleep")
    def test_empty_api_results(self, mock_sleep, collector):
        with patch.object(collector.client, "get_all_opportunities", return_value=[]):
            result = collector.collect_daily_opportunities()
        assert result == []

    @patch("time.sleep")
    def test_exception_reraise(self, mock_sleep, collector):
        with patch.object(
            collector.client,
            "get_all_opportunities",
            side_effect=RuntimeError("API down"),
        ):
            with pytest.raises(RuntimeError, match="API down"):
                collector.collect_daily_opportunities()


class TestGetOpportunitiesByDateRange:
    def test_in_range(self, collector):
        collector.opportunities = {
            "id1": {
                "collected_date": "2025-01-15T10:00:00",
                "data": {"noticeId": "id1"},
            }
        }
        start = datetime(2025, 1, 1)
        end = datetime(2025, 1, 31)
        result = collector.get_opportunities_by_date_range(start, end)
        assert len(result) == 1

    def test_out_of_range(self, collector):
        collector.opportunities = {
            "id1": {
                "collected_date": "2025-03-15T10:00:00",
                "data": {"noticeId": "id1"},
            }
        }
        start = datetime(2025, 1, 1)
        end = datetime(2025, 1, 31)
        result = collector.get_opportunities_by_date_range(start, end)
        assert len(result) == 0


class TestGetOpportunitiesByNaics:
    def test_match(self, collector):
        collector.opportunities = {
            "id1": {"data": {"noticeId": "id1", "naicsCode": "541511,541512"}}
        }
        result = collector.get_opportunities_by_naics("541511")
        assert len(result) == 1

    def test_no_match(self, collector):
        collector.opportunities = {
            "id1": {"data": {"noticeId": "id1", "naicsCode": "541511"}}
        }
        result = collector.get_opportunities_by_naics("999999")
        assert len(result) == 0


class TestGetAllOpportunities:
    def test_returns_data_list(self, collector):
        collector.opportunities = {
            "id1": {"data": {"noticeId": "id1"}},
            "id2": {"data": {"noticeId": "id2"}},
        }
        result = collector.get_all_opportunities()
        assert len(result) == 2


class TestGetSummary:
    def test_empty(self, collector):
        collector.opportunities = {}
        result = collector.get_summary()
        assert result["total_opportunities"] == 0
        assert result["date_range"] is None

    def test_single(self, collector):
        collector.opportunities = {
            "id1": {
                "collected_date": "2025-01-15T10:00:00",
                "data": {"naicsCode": "541511"},
            }
        }
        result = collector.get_summary()
        assert result["total_opportunities"] == 1
        assert result["naics_breakdown"]["541511"] == 1

    def test_multiple(self, collector):
        collector.opportunities = {
            "id1": {
                "collected_date": "2025-01-10T10:00:00",
                "data": {"naicsCode": "541511"},
            },
            "id2": {
                "collected_date": "2025-01-15T10:00:00",
                "data": {"naicsCode": "541512"},
            },
        }
        result = collector.get_summary()
        assert result["total_opportunities"] == 2
        assert "earliest" in result["date_range"]
        assert "latest" in result["date_range"]
