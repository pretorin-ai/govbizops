"""Tests for SAMGovClient"""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

from govbizops.client import SAMGovClient


class TestSAMGovClientInit:
    def test_standard_init(self):
        client = SAMGovClient("test-key")
        assert client.api_key == "test-key"
        assert client.BASE_URL == "https://api.sam.gov/opportunities/v2/search"
        assert client._daily_collections == 0
        assert client._last_collection_date is None

    def test_alpha_url(self):
        client = SAMGovClient("test-key", use_alpha=True)
        assert "api-alpha" in client.BASE_URL


class TestCheckDailyLimit:
    def test_same_day_increment(self):
        client = SAMGovClient("key")
        client._last_collection_date = datetime.now().date()
        client._daily_collections = 5
        client._check_daily_limit()
        assert client._daily_collections == 6

    def test_new_day_reset(self):
        client = SAMGovClient("key")
        client._last_collection_date = (datetime.now() - timedelta(days=1)).date()
        client._daily_collections = 50
        client._check_daily_limit()
        assert client._daily_collections == 1

    def test_limit_exceeded(self):
        client = SAMGovClient("key")
        client._last_collection_date = datetime.now().date()
        client._daily_collections = 100
        with pytest.raises(ValueError, match="Daily collection limit reached"):
            client._check_daily_limit()


class TestValidateNaicsCodes:
    def test_valid(self):
        client = SAMGovClient("key")
        client._validate_naics_codes(["541511", "541512"])

    def test_none_is_ok(self):
        client = SAMGovClient("key")
        client._validate_naics_codes(None)

    def test_too_many(self):
        client = SAMGovClient("key")
        codes = [str(i) for i in range(51)]
        with pytest.raises(ValueError, match="Maximum 50"):
            client._validate_naics_codes(codes)


class TestValidateDateRange:
    def test_valid(self):
        client = SAMGovClient("key")
        now = datetime.now()
        client._validate_date_range(now - timedelta(days=30), now)

    def test_too_wide(self):
        client = SAMGovClient("key")
        now = datetime.now()
        with pytest.raises(ValueError, match="Maximum 90 days"):
            client._validate_date_range(now - timedelta(days=91), now)


class TestSearchOpportunities:
    @patch("time.sleep")
    def test_success(self, mock_sleep):
        client = SAMGovClient("key")
        now = datetime.now()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "totalRecords": 1,
            "opportunitiesData": [{"noticeId": "a"}],
        }

        with patch.object(client.session, "get", return_value=mock_resp):
            result = client.search_opportunities(now - timedelta(days=1), now)
        assert result["totalRecords"] == 1
        mock_sleep.assert_called_once_with(2)

    @patch("time.sleep")
    def test_with_naics_codes(self, mock_sleep):
        client = SAMGovClient("key")
        now = datetime.now()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"totalRecords": 0, "opportunitiesData": []}

        with patch.object(client.session, "get", return_value=mock_resp) as mock_get:
            client.search_opportunities(
                now - timedelta(days=1), now, naics_codes=["541511", "541512"]
            )
        call_kwargs = mock_get.call_args[1]
        assert call_kwargs["params"]["ncode"] == "541511,541512"

    @patch("time.sleep")
    def test_no_naics(self, mock_sleep):
        client = SAMGovClient("key")
        now = datetime.now()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"totalRecords": 0, "opportunitiesData": []}

        with patch.object(client.session, "get", return_value=mock_resp) as mock_get:
            client.search_opportunities(now - timedelta(days=1), now, naics_codes=None)
        # ncode should not be in params
        call_kwargs = mock_get.call_args[1]
        assert "ncode" not in call_kwargs["params"]

    @patch("time.sleep")
    def test_extra_kwargs(self, mock_sleep):
        client = SAMGovClient("key")
        now = datetime.now()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"totalRecords": 0, "opportunitiesData": []}

        with patch.object(client.session, "get", return_value=mock_resp) as mock_get:
            client.search_opportunities(now - timedelta(days=1), now, q="test keyword")
        call_kwargs = mock_get.call_args[1]
        assert call_kwargs["params"]["q"] == "test keyword"

    @patch("time.sleep")
    def test_limit_cap(self, mock_sleep):
        client = SAMGovClient("key")
        now = datetime.now()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"totalRecords": 0, "opportunitiesData": []}

        with patch.object(client.session, "get", return_value=mock_resp) as mock_get:
            client.search_opportunities(now - timedelta(days=1), now, limit=5000)
        call_kwargs = mock_get.call_args[1]
        assert call_kwargs["params"]["limit"] == 1000

    @patch("time.sleep")
    def test_http_error(self, mock_sleep):
        client = SAMGovClient("key")
        now = datetime.now()
        mock_resp = MagicMock()
        mock_resp.status_code = 403
        mock_resp.text = "Forbidden"
        mock_resp.raise_for_status.side_effect = Exception("403 Forbidden")

        with patch.object(client.session, "get", return_value=mock_resp):
            with pytest.raises(Exception, match="403"):
                client.search_opportunities(now - timedelta(days=1), now)

    @patch("time.sleep")
    def test_date_range_exceeds_year(self, mock_sleep):
        client = SAMGovClient("key")
        now = datetime.now()
        # Must bypass _validate_date_range (90-day) to reach the 365-day check
        with patch.object(client, "_validate_date_range"):
            with pytest.raises(ValueError, match="cannot exceed 1 year"):
                client.search_opportunities(now - timedelta(days=400), now)


class TestGetAllOpportunities:
    @patch("time.sleep")
    def test_single_page(self, mock_sleep):
        client = SAMGovClient("key")
        now = datetime.now()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "totalRecords": 2,
            "opportunitiesData": [{"noticeId": "a"}, {"noticeId": "b"}],
        }

        with patch.object(client.session, "get", return_value=mock_resp):
            result = client.get_all_opportunities(now - timedelta(days=1), now)
        assert len(result) == 2

    @patch("time.sleep")
    def test_multi_page_pagination(self, mock_sleep):
        client = SAMGovClient("key")
        now = datetime.now()

        page1 = MagicMock()
        page1.status_code = 200
        page1.json.return_value = {
            "totalRecords": 600,
            "opportunitiesData": [{"noticeId": str(i)} for i in range(500)],
        }

        page2 = MagicMock()
        page2.status_code = 200
        page2.json.return_value = {
            "totalRecords": 600,
            "opportunitiesData": [{"noticeId": str(i)} for i in range(500, 600)],
        }

        with patch.object(client.session, "get", side_effect=[page1, page2]):
            result = client.get_all_opportunities(now - timedelta(days=1), now)
        assert len(result) == 600

    @patch("time.sleep")
    def test_empty_results(self, mock_sleep):
        client = SAMGovClient("key")
        now = datetime.now()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "totalRecords": 0,
            "opportunitiesData": [],
        }

        with patch.object(client.session, "get", return_value=mock_resp):
            result = client.get_all_opportunities(now - timedelta(days=1), now)
        assert result == []

    @patch("time.sleep")
    def test_exception_mid_pagination(self, mock_sleep):
        client = SAMGovClient("key")
        now = datetime.now()

        page1 = MagicMock()
        page1.status_code = 200
        page1.json.return_value = {
            "totalRecords": 1000,
            "opportunitiesData": [{"noticeId": str(i)} for i in range(500)],
        }

        with patch.object(
            client.session, "get", side_effect=[page1, Exception("network error")]
        ):
            result = client.get_all_opportunities(now - timedelta(days=1), now)
        # Should return partial results
        assert len(result) == 500
