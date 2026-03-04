"""Tests for OpportunityCollector"""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

from govbizops.collector import OpportunityCollector
from govbizops.database import Opportunity


@pytest.fixture
def collector(db_session):
    """Create a collector with a test DB session."""
    with patch("time.sleep"):
        c = OpportunityCollector(
            api_key="test-key",
            naics_codes=["541511"],
            db_session=db_session,
        )
    return c


class TestInit:
    def test_valid_init(self, db_session):
        with patch("time.sleep"):
            c = OpportunityCollector(
                api_key="key",
                naics_codes=["541511", "541512"],
                db_session=db_session,
            )
        assert c.naics_codes == ["541511", "541512"]

    def test_too_many_naics(self, db_session):
        codes = [str(i) for i in range(51)]
        with pytest.raises(ValueError, match="Maximum 50"):
            OpportunityCollector("key", codes, db_session)


class TestCollectDailyOpportunities:
    @patch("time.sleep")
    def test_new_opps_found(self, mock_sleep, collector, db_session):
        mock_opps = [
            {"noticeId": "new1", "type": "Solicitation"},
            {"noticeId": "new2", "type": "Solicitation"},
        ]
        with patch.object(
            collector.client, "get_all_opportunities", return_value=mock_opps
        ):
            result = collector.collect_daily_opportunities()
        assert len(result) == 2
        assert db_session.query(Opportunity).count() == 2

    @patch("time.sleep")
    def test_duplicates_filtered(self, mock_sleep, collector, db_session):
        # Pre-insert an existing opportunity
        db_session.add(Opportunity(notice_id="existing", opp_type="Solicitation"))
        db_session.commit()

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
    def test_in_range(self, collector, db_session):
        opp = Opportunity(
            notice_id="id1",
            collected_date=datetime(2025, 1, 15, 10, 0, 0),
        )
        db_session.add(opp)
        db_session.commit()

        start = datetime(2025, 1, 1)
        end = datetime(2025, 1, 31)
        result = collector.get_opportunities_by_date_range(start, end)
        assert len(result) == 1

    def test_out_of_range(self, collector, db_session):
        opp = Opportunity(
            notice_id="id1",
            collected_date=datetime(2025, 3, 15, 10, 0, 0),
        )
        db_session.add(opp)
        db_session.commit()

        start = datetime(2025, 1, 1)
        end = datetime(2025, 1, 31)
        result = collector.get_opportunities_by_date_range(start, end)
        assert len(result) == 0


class TestGetOpportunitiesByNaics:
    def test_match(self, collector, db_session):
        opp = Opportunity(notice_id="id1", naics_code="541511,541512")
        db_session.add(opp)
        db_session.commit()

        result = collector.get_opportunities_by_naics("541511")
        assert len(result) == 1

    def test_no_match(self, collector, db_session):
        opp = Opportunity(notice_id="id1", naics_code="541511")
        db_session.add(opp)
        db_session.commit()

        result = collector.get_opportunities_by_naics("999999")
        assert len(result) == 0


class TestGetAllOpportunities:
    def test_returns_data_list(self, collector, db_session):
        db_session.add(Opportunity(notice_id="id1"))
        db_session.add(Opportunity(notice_id="id2"))
        db_session.commit()

        result = collector.get_all_opportunities()
        assert len(result) == 2


class TestGetSummary:
    def test_empty(self, collector):
        result = collector.get_summary()
        assert result["total_opportunities"] == 0
        assert result["date_range"] is None

    def test_single(self, collector, db_session):
        opp = Opportunity(
            notice_id="id1",
            naics_code="541511",
            collected_date=datetime(2025, 1, 15, 10, 0, 0),
        )
        db_session.add(opp)
        db_session.commit()

        result = collector.get_summary()
        assert result["total_opportunities"] == 1
        assert result["naics_breakdown"]["541511"] == 1

    def test_multiple(self, collector, db_session):
        db_session.add(
            Opportunity(
                notice_id="id1",
                naics_code="541511",
                collected_date=datetime(2025, 1, 10, 10, 0, 0),
            )
        )
        db_session.add(
            Opportunity(
                notice_id="id2",
                naics_code="541512",
                collected_date=datetime(2025, 1, 15, 10, 0, 0),
            )
        )
        db_session.commit()

        result = collector.get_summary()
        assert result["total_opportunities"] == 2
        assert "earliest" in result["date_range"]
        assert "latest" in result["date_range"]
