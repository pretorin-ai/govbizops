"""Tests for SolicitationAnalyzer"""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime

from govbizops.solicitation_analyzer import SolicitationAnalyzer


@pytest.fixture
def analyzer():
    with patch("govbizops.solicitation_analyzer.OpenAI"):
        with patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"}):
            a = SolicitationAnalyzer("sam-key")
    return a


@pytest.fixture
def analyzer_no_openai():
    with patch.dict("os.environ", {}, clear=True):
        # Remove OPENAI_API_KEY
        import os

        old = os.environ.pop("OPENAI_API_KEY", None)
        a = SolicitationAnalyzer("sam-key")
        if old is not None:
            os.environ["OPENAI_API_KEY"] = old
    return a


class TestInit:
    def test_with_openai(self, analyzer):
        assert analyzer.openai_client is not None
        assert analyzer.api_key == "sam-key"

    def test_without_openai(self, analyzer_no_openai):
        assert analyzer_no_openai.openai_client is None


class TestFetchDescriptionFromApiUrl:
    def test_success_plain_text(self, analyzer):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = "  Plain text description  "
        with patch.object(analyzer.session, "get", return_value=mock_resp):
            result = analyzer.fetch_description_from_api_url(
                "https://api.sam.gov/opportunities/v2/noticedesc?id=1"
            )
        assert result == "Plain text description"

    def test_success_html(self, analyzer):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = "<p>HTML &amp; content</p>"
        with patch.object(analyzer.session, "get", return_value=mock_resp):
            result = analyzer.fetch_description_from_api_url(
                "https://api.sam.gov/opportunities/v2/noticedesc?id=1"
            )
        assert "HTML" in result
        assert "<p>" not in result

    def test_v1_to_v2_conversion(self, analyzer):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = "desc"
        with patch.object(analyzer.session, "get", return_value=mock_resp) as mock_get:
            analyzer.fetch_description_from_api_url(
                "https://api.sam.gov/opportunities/v1/noticedesc?id=1"
            )
        called_url = mock_get.call_args[0][0]
        assert "/v2/" in called_url

    def test_404(self, analyzer):
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        with patch.object(analyzer.session, "get", return_value=mock_resp):
            result = analyzer.fetch_description_from_api_url(
                "https://api.sam.gov/opportunities/v2/noticedesc?id=1"
            )
        assert result is None

    def test_other_error(self, analyzer):
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.text = "error"
        with patch.object(analyzer.session, "get", return_value=mock_resp):
            result = analyzer.fetch_description_from_api_url(
                "https://api.sam.gov/opportunities/v2/noticedesc?id=1"
            )
        assert result is None

    def test_exception(self, analyzer):
        with patch.object(
            analyzer.session, "get", side_effect=Exception("connection error")
        ):
            result = analyzer.fetch_description_from_api_url(
                "https://api.sam.gov/opportunities/v2/noticedesc?id=1"
            )
        assert result is None


class TestFetchDescriptionFromWeb:
    def test_no_ui_link(self, analyzer):
        result = analyzer.fetch_description_from_web({})
        assert result is None

    def test_workspace_url_conversion(self, analyzer):
        opp = {
            "uiLink": "https://sam.gov/workspace/opp/abc123def456abc123def456abc12345/view"
        }
        with patch(
            "govbizops.solicitation_analyzer.scrape_sam_opportunity",
            return_value={"success": True, "description": "desc"},
        ) as mock_scrape:
            result = analyzer.fetch_description_from_web(opp)
        assert result is not None
        called_url = mock_scrape.call_args[0][0]
        assert "/workspace/" not in called_url

    def test_scrape_success(self, analyzer):
        opp = {"uiLink": "https://sam.gov/opp/abc123def456abc123def456abc12345/view"}
        with patch(
            "govbizops.solicitation_analyzer.scrape_sam_opportunity",
            return_value={"success": True, "description": "Full description"},
        ):
            result = analyzer.fetch_description_from_web(opp)
        assert result["description"] == "Full description"

    def test_scrape_failure(self, analyzer):
        opp = {"uiLink": "https://sam.gov/opp/abc123def456abc123def456abc12345/view"}
        with patch(
            "govbizops.solicitation_analyzer.scrape_sam_opportunity",
            return_value={"success": False, "description": None, "error": "timeout"},
        ):
            result = analyzer.fetch_description_from_web(opp)
        assert result is None

    def test_exception(self, analyzer):
        opp = {"uiLink": "https://sam.gov/opp/abc123def456abc123def456abc12345/view"}
        with patch(
            "govbizops.solicitation_analyzer.scrape_sam_opportunity",
            side_effect=RuntimeError("crash"),
        ):
            result = analyzer.fetch_description_from_web(opp)
        assert result is None


class TestFetchDetailedDescription:
    def test_url_field_api_success(self, analyzer):
        opp = {
            "description": "https://api.sam.gov/opportunities/v1/noticedesc?id=1",
            "uiLink": "https://sam.gov/opp/abc123def456abc123def456abc12345/view",
        }
        with patch.object(
            analyzer, "fetch_description_from_api_url", return_value="API desc"
        ):
            result = analyzer.fetch_detailed_description(opp)
        assert "API desc" in result

    def test_url_field_api_fail_web_success(self, analyzer):
        opp = {
            "description": "https://api.sam.gov/opportunities/v1/noticedesc?id=1",
            "uiLink": "https://sam.gov/opp/abc123def456abc123def456abc12345/view",
        }
        with patch.object(
            analyzer, "fetch_description_from_api_url", return_value=None
        ):
            with patch.object(
                analyzer,
                "fetch_description_from_web",
                return_value={
                    "description": "Web desc",
                    "attachments": [{"name": "doc.pdf", "url": "http://x"}],
                },
            ):
                result = analyzer.fetch_detailed_description(opp)
        assert "Web desc" in result
        assert "_web_attachments" in opp

    def test_url_field_both_fail(self, analyzer):
        opp = {
            "description": "https://api.sam.gov/opportunities/v1/noticedesc?id=1",
            "uiLink": "https://sam.gov/opp/abc123def456abc123def456abc12345/view",
        }
        with patch.object(
            analyzer, "fetch_description_from_api_url", return_value=None
        ):
            with patch.object(
                analyzer, "fetch_description_from_web", return_value=None
            ):
                result = analyzer.fetch_detailed_description(opp)
        assert "fetch failed" in result

    def test_plain_text_field(self, analyzer):
        opp = {
            "description": "A" * 60,
        }
        result = analyzer.fetch_detailed_description(opp)
        assert "A" * 60 in result

    def test_short_field_filtered(self, analyzer):
        opp = {"description": "Short"}
        result = analyzer.fetch_detailed_description(opp)
        assert result is None

    def test_no_fields(self, analyzer):
        result = analyzer.fetch_detailed_description({"noticeId": "x"})
        assert result is None


class TestExtractAdditionalInfo:
    def test_all_fields(self, analyzer, sample_opportunity):
        result = analyzer.extract_additional_info(sample_opportunity)
        assert "naics_code" in result
        assert "psc_code" in result
        assert "organization_name" in result

    def test_some_fields(self, analyzer):
        opp = {"naicsCode": "541511"}
        result = analyzer.extract_additional_info(opp)
        assert "naics_code" in result
        assert "psc_code" not in result

    def test_no_fields(self, analyzer):
        result = analyzer.extract_additional_info({})
        assert result == {}

    def test_attachments(self, analyzer):
        opp = {"attachments": [{"name": "doc.pdf"}]}
        result = analyzer.extract_additional_info(opp)
        assert "attachments" in result

    def test_amendment(self, analyzer):
        opp = {"isAmendment": True}
        result = analyzer.extract_additional_info(opp)
        assert result["is_amendment"] is True


class TestExtractDocumentsInfo:
    def test_api_attachments(self, analyzer):
        opp = {
            "attachments": [
                {
                    "type": "PDF",
                    "name": "sow.pdf",
                    "description": "SOW",
                    "url": "http://x",
                }
            ]
        }
        with patch.object(analyzer, "fetch_detailed_description", return_value=""):
            result = analyzer.extract_documents_info(opp)
        assert len(result) >= 1
        assert result[0]["name"] == "sow.pdf"

    def test_web_attachments(self, analyzer):
        opp = {"_web_attachments": [{"name": "rfp.pdf", "url": "http://x"}]}
        with patch.object(analyzer, "fetch_detailed_description", return_value=""):
            result = analyzer.extract_documents_info(opp)
        assert any(d["type"] == "Web Attachment" for d in result)

    def test_pattern_matching(self, analyzer):
        desc_text = "Please see the Statement of Work for details. The RFP is attached. Amendment 001 is included."
        opp = {}
        with patch.object(
            analyzer, "fetch_detailed_description", return_value=desc_text
        ):
            result = analyzer.extract_documents_info(opp)
        types = [d["type"] for d in result]
        assert any("Statement of Work" in t or "SOW" in t for t in types)
        assert any("RFP" in t for t in types)
        assert any("Amendment" in t for t in types)


class TestGenerateAiResponse:
    def test_no_client(self, analyzer_no_openai):
        result = analyzer_no_openai.generate_ai_response({}, "desc", {}, [])
        assert result is None

    def test_success(self, analyzer):
        mock_completion = MagicMock()
        mock_completion.choices = [MagicMock()]
        mock_completion.choices[0].message.content = "AI generated response"
        analyzer.openai_client.chat.completions.create.return_value = mock_completion

        result = analyzer.generate_ai_response(
            {"title": "Test", "solicitationNumber": "S1"},
            "description text",
            {"naics_code": "541511"},
            [{"type": "SOW", "name": "sow.pdf", "description": "SOW doc"}],
        )
        assert result == "AI generated response"

    def test_exception(self, analyzer):
        analyzer.openai_client.chat.completions.create.side_effect = Exception(
            "API error"
        )
        result = analyzer.generate_ai_response({"title": "Test"}, "desc", {}, [])
        assert "Error generating AI response" in result

    def test_documents_without_name(self, analyzer):
        mock_completion = MagicMock()
        mock_completion.choices = [MagicMock()]
        mock_completion.choices[0].message.content = "response"
        analyzer.openai_client.chat.completions.create.return_value = mock_completion

        result = analyzer.generate_ai_response(
            {"title": "Test"},
            "desc",
            {},
            [{"type": "SOW", "context": "Statement of Work details"}],
        )
        assert result == "response"


class TestFetchOpportunityById:
    def test_found_exact_match(self, analyzer):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "opportunitiesData": [{"noticeId": "target-id", "title": "Found It"}]
        }
        with patch.object(analyzer.session, "get", return_value=mock_resp):
            result = analyzer.fetch_opportunity_by_id("target-id")
        assert result["title"] == "Found It"

    def test_found_url_match(self, analyzer):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "opportunitiesData": [
                {
                    "noticeId": "other",
                    "uiLink": "https://sam.gov/opp/target-id/view",
                    "title": "URL Match",
                }
            ]
        }
        with patch.object(analyzer.session, "get", return_value=mock_resp):
            result = analyzer.fetch_opportunity_by_id("target-id")
        assert result["title"] == "URL Match"

    def test_not_found(self, analyzer):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"opportunitiesData": []}
        with patch.object(analyzer.session, "get", return_value=mock_resp):
            result = analyzer.fetch_opportunity_by_id("nonexistent")
        assert result is None

    def test_exception(self, analyzer):
        with patch.object(analyzer.session, "get", side_effect=Exception("network")):
            result = analyzer.fetch_opportunity_by_id("id")
        assert result is None

    def test_api_error_status(self, analyzer):
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.text = "error"
        with patch.object(analyzer.session, "get", return_value=mock_resp):
            result = analyzer.fetch_opportunity_by_id("id")
        assert result is None


class TestAnalyzeByUrl:
    def test_valid_url(self, analyzer):
        opp = {"noticeId": "abc", "title": "Test"}
        with patch.object(analyzer, "fetch_opportunity_by_id", return_value=opp):
            with patch.object(
                analyzer,
                "analyze_solicitation",
                return_value={"opportunity": opp},
            ):
                result = analyzer.analyze_by_url(
                    "https://sam.gov/opp/abc123def456abc123def456abc12345/view"
                )
        assert "opportunity" in result

    def test_invalid_url(self, analyzer):
        with pytest.raises(ValueError, match="Could not extract"):
            analyzer.analyze_by_url("https://sam.gov/not-valid")

    def test_opportunity_not_found(self, analyzer):
        with patch.object(analyzer, "fetch_opportunity_by_id", return_value=None):
            result = analyzer.analyze_by_url(
                "https://sam.gov/opp/abc123def456abc123def456abc12345/view"
            )
        assert "error" in result


class TestAnalyzeSolicitation:
    def test_with_openai(self, analyzer):
        opp = {"title": "Test Solicitation", "noticeId": "123"}
        with patch.object(analyzer, "fetch_detailed_description", return_value="desc"):
            with patch.object(
                analyzer, "extract_additional_info", return_value={"k": "v"}
            ):
                with patch.object(analyzer, "extract_documents_info", return_value=[]):
                    with patch.object(
                        analyzer,
                        "generate_ai_response",
                        return_value="AI says...",
                    ):
                        result = analyzer.analyze_solicitation(opp)
        assert result["ai_response"] == "AI says..."
        assert "analysis_timestamp" in result

    def test_without_openai(self, analyzer_no_openai):
        opp = {"title": "Test Solicitation", "noticeId": "123"}
        with patch.object(
            analyzer_no_openai, "fetch_detailed_description", return_value="desc"
        ):
            with patch.object(
                analyzer_no_openai, "extract_additional_info", return_value={}
            ):
                with patch.object(
                    analyzer_no_openai, "extract_documents_info", return_value=[]
                ):
                    result = analyzer_no_openai.analyze_solicitation(opp)
        assert result["ai_response"] is None

    def test_openai_exception(self, analyzer):
        opp = {"title": "Test Solicitation", "noticeId": "123"}
        with patch.object(analyzer, "fetch_detailed_description", return_value="desc"):
            with patch.object(analyzer, "extract_additional_info", return_value={}):
                with patch.object(analyzer, "extract_documents_info", return_value=[]):
                    with patch.object(
                        analyzer,
                        "generate_ai_response",
                        side_effect=Exception("fail"),
                    ):
                        result = analyzer.analyze_solicitation(opp)
        assert "unavailable" in result["ai_response"]
