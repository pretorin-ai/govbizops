"""Tests for SAMWebScraper and scrape_sam_opportunity"""

import asyncio
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from govbizops.sam_scraper import SAMWebScraper, scrape_sam_opportunity


class TestSAMWebScraperInit:
    def test_default_params(self):
        scraper = SAMWebScraper()
        assert scraper.headless is True
        assert scraper.server_mode is False
        assert scraper.browser is None
        assert scraper.playwright is None

    def test_custom_params(self):
        scraper = SAMWebScraper(headless=False, server_mode=True)
        assert scraper.headless is False
        assert scraper.server_mode is True


class TestStartStop:
    @pytest.mark.asyncio
    async def test_start_lifecycle(self):
        mock_pw = AsyncMock()
        mock_browser = AsyncMock()
        mock_pw.chromium.launch.return_value = mock_browser

        with patch("govbizops.sam_scraper.async_playwright") as mock_apw:
            mock_context = AsyncMock()
            mock_context.start.return_value = mock_pw
            mock_apw.return_value = mock_context

            scraper = SAMWebScraper()
            await scraper.start()

            assert scraper.browser is mock_browser
            assert scraper.playwright is mock_pw

    @pytest.mark.asyncio
    async def test_server_mode_args(self):
        mock_pw = AsyncMock()
        mock_browser = AsyncMock()
        mock_pw.chromium.launch.return_value = mock_browser

        with patch("govbizops.sam_scraper.async_playwright") as mock_apw:
            mock_context = AsyncMock()
            mock_context.start.return_value = mock_pw
            mock_apw.return_value = mock_context

            scraper = SAMWebScraper(server_mode=True)
            await scraper.start()

            launch_kwargs = mock_pw.chromium.launch.call_args
            args_list = launch_kwargs[1]["args"]
            assert "--disable-gpu" in args_list

    @pytest.mark.asyncio
    async def test_stop_idempotent(self):
        scraper = SAMWebScraper()
        scraper.browser = None
        scraper.playwright = None
        # Should not raise
        await scraper.stop()


class TestContextManager:
    @pytest.mark.asyncio
    async def test_aenter_aexit(self):
        mock_pw = AsyncMock()
        mock_browser = AsyncMock()
        mock_pw.chromium.launch.return_value = mock_browser

        with patch("govbizops.sam_scraper.async_playwright") as mock_apw:
            mock_context = AsyncMock()
            mock_context.start.return_value = mock_pw
            mock_apw.return_value = mock_context

            async with SAMWebScraper() as scraper:
                assert scraper.browser is mock_browser
            # After exit, stop should have been called
            mock_browser.close.assert_awaited()


class TestScrapeOpportunity:
    @pytest.mark.asyncio
    async def test_success(self):
        scraper = SAMWebScraper()
        mock_browser = AsyncMock()
        mock_page = AsyncMock()
        mock_browser.new_page.return_value = mock_page
        scraper.browser = mock_browser

        # Page content with description
        html = """<html><body>
        <p>This is a substantial description paragraph that is longer than fifty characters for testing.</p>
        </body></html>"""
        mock_page.content.return_value = html
        mock_page.wait_for_selector.side_effect = Exception("not found")
        mock_page.query_selector.return_value = None

        result = await scraper.scrape_opportunity("https://sam.gov/opp/123/view")
        assert result["success"] is True
        assert result["description"] is not None
        mock_page.close.assert_awaited()

    @pytest.mark.asyncio
    async def test_selector_found(self):
        """Test when one of the content selectors succeeds."""
        scraper = SAMWebScraper()
        mock_browser = AsyncMock()
        mock_page = AsyncMock()
        mock_browser.new_page.return_value = mock_page
        scraper.browser = mock_browser

        # First selector succeeds
        mock_page.wait_for_selector.return_value = True
        mock_page.query_selector.return_value = None
        html = """<html><body>
        <p>This is a substantial description paragraph that is longer than fifty characters for testing.</p>
        </body></html>"""
        mock_page.content.return_value = html

        result = await scraper.scrape_opportunity("https://sam.gov/opp/123/view")
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_description_tab_click_exception(self):
        """Test when clicking description tab raises exception."""
        scraper = SAMWebScraper()
        mock_browser = AsyncMock()
        mock_page = AsyncMock()
        mock_browser.new_page.return_value = mock_page
        scraper.browser = mock_browser

        mock_page.wait_for_selector.side_effect = Exception("not found")
        mock_page.query_selector.side_effect = Exception("click failed")
        html = """<html><body>
        <p>This is a substantial description paragraph that is longer than fifty characters for testing.</p>
        </body></html>"""
        mock_page.content.return_value = html

        result = await scraper.scrape_opportunity("https://sam.gov/opp/123/view")
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_method3_description_patterns(self):
        """Test description extraction via method 3 (regex patterns)."""
        scraper = SAMWebScraper()
        mock_browser = AsyncMock()
        mock_page = AsyncMock()
        mock_browser.new_page.return_value = mock_page
        scraper.browser = mock_browser

        mock_page.wait_for_selector.side_effect = Exception("not found")
        mock_page.query_selector.return_value = None
        # No paragraphs > 50 chars, but a div with description class
        html = (
            """<html><body>
        <p>Short</p>
        <div class="description-content">"""
            + "A" * 120
            + """</div>
        </body></html>"""
        )
        mock_page.content.return_value = html

        result = await scraper.scrape_opportunity("https://sam.gov/opp/123/view")
        assert result["success"] is True
        assert result["description"] is not None

    @pytest.mark.asyncio
    async def test_method4_main_content(self):
        """Test description extraction via method 4 (main content area)."""
        scraper = SAMWebScraper()
        mock_browser = AsyncMock()
        mock_page = AsyncMock()
        mock_browser.new_page.return_value = mock_page
        scraper.browser = mock_browser

        mock_page.wait_for_selector.side_effect = Exception("not found")
        mock_page.query_selector.return_value = None
        # No paragraphs > 50 chars, no description divs, but main content
        html = "<html><body><main><nav>Nav</nav>" + "B" * 250 + "</main></body></html>"
        mock_page.content.return_value = html

        result = await scraper.scrape_opportunity("https://sam.gov/opp/123/view")
        assert result["success"] is True
        assert result["description"] is not None

    @pytest.mark.asyncio
    async def test_attachment_div_with_links(self):
        """Test attachment extraction from div elements containing links."""
        scraper = SAMWebScraper()
        mock_browser = AsyncMock()
        mock_page = AsyncMock()
        mock_browser.new_page.return_value = mock_page
        scraper.browser = mock_browser

        mock_page.wait_for_selector.side_effect = Exception("not found")
        mock_page.query_selector.return_value = None
        html = """<html><body>
        <p>This is a substantial description paragraph that is longer than fifty characters for testing.</p>
        <div class="attachment-section">
            <a href="https://sam.gov/file.pdf">Download File</a>
        </div>
        </body></html>"""
        mock_page.content.return_value = html

        result = await scraper.scrape_opportunity("https://sam.gov/opp/123/view")
        assert result["success"] is True
        assert len(result["attachments"]) >= 1

    @pytest.mark.asyncio
    async def test_selector_fallback(self):
        scraper = SAMWebScraper()
        mock_browser = AsyncMock()
        mock_page = AsyncMock()
        mock_browser.new_page.return_value = mock_page
        scraper.browser = mock_browser

        # All selectors fail
        mock_page.wait_for_selector.side_effect = Exception("not found")
        html = "<html><body><main><p>Short</p></main></body></html>"
        mock_page.content.return_value = html
        mock_page.query_selector.return_value = None

        result = await scraper.scrape_opportunity("https://sam.gov/opp/123/view")
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_description_tab_click(self):
        scraper = SAMWebScraper()
        mock_browser = AsyncMock()
        mock_page = AsyncMock()
        mock_browser.new_page.return_value = mock_page
        scraper.browser = mock_browser

        mock_desc_link = AsyncMock()
        mock_page.query_selector.return_value = mock_desc_link
        mock_page.wait_for_selector.side_effect = Exception("not found")

        html = "<html><body><p>This is a substantial description paragraph that is longer than fifty characters for testing.</p></body></html>"
        mock_page.content.return_value = html

        with patch("govbizops.sam_scraper.asyncio.sleep", new_callable=AsyncMock):
            result = await scraper.scrape_opportunity("https://sam.gov/opp/123/view")
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_attachment_extraction(self):
        scraper = SAMWebScraper()
        mock_browser = AsyncMock()
        mock_page = AsyncMock()
        mock_browser.new_page.return_value = mock_page
        scraper.browser = mock_browser

        mock_page.wait_for_selector.side_effect = Exception("not found")
        mock_page.query_selector.return_value = None

        html = """<html><body>
        <p>This is a substantial description paragraph that is longer than fifty characters for testing purposes.</p>
        <a href="https://sam.gov/doc.pdf">Important Document.pdf</a>
        <a href="/attachment/spec.docx">Specifications.docx</a>
        <a href="https://sam.gov/doc.pdf">Important Document.pdf</a>
        </body></html>"""
        mock_page.content.return_value = html

        result = await scraper.scrape_opportunity("https://sam.gov/opp/123/view")
        assert result["success"] is True
        # Dedup should reduce duplicates
        assert len(result["attachments"]) == 2

    @pytest.mark.asyncio
    async def test_exception_returns_error(self):
        scraper = SAMWebScraper()
        mock_browser = AsyncMock()
        mock_page = AsyncMock()
        mock_page.goto.side_effect = Exception("timeout")
        mock_browser.new_page.return_value = mock_page
        scraper.browser = mock_browser

        result = await scraper.scrape_opportunity("https://sam.gov/opp/123/view")
        assert result["success"] is False
        assert result["error"] == "timeout"
        mock_page.close.assert_awaited()

    @pytest.mark.asyncio
    async def test_auto_start_if_no_browser(self):
        scraper = SAMWebScraper()
        mock_pw = AsyncMock()
        mock_browser = AsyncMock()
        mock_page = AsyncMock()
        mock_pw.chromium.launch.return_value = mock_browser
        mock_browser.new_page.return_value = mock_page
        mock_page.wait_for_selector.side_effect = Exception("x")
        mock_page.query_selector.return_value = None
        mock_page.content.return_value = "<html><body></body></html>"

        with patch("govbizops.sam_scraper.async_playwright") as mock_apw:
            mock_context = AsyncMock()
            mock_context.start.return_value = mock_pw
            mock_apw.return_value = mock_context
            result = await scraper.scrape_opportunity("https://sam.gov/opp/123/view")
        assert result is not None


class TestScrapeSync:
    def test_wrapper_delegates(self):
        scraper = SAMWebScraper()
        expected = {"success": True, "description": "test"}
        with patch.object(
            scraper, "scrape_opportunity", new_callable=AsyncMock, return_value=expected
        ):
            result = scraper.scrape_sync("https://sam.gov/opp/123/view")
        assert result == expected

    @pytest.mark.asyncio
    async def test_from_running_loop(self):
        """scrape_sync should work when called from inside a running event loop."""
        scraper = SAMWebScraper()
        expected = {"success": True, "description": "from loop"}
        with patch.object(
            scraper, "scrape_opportunity", new_callable=AsyncMock, return_value=expected
        ):
            result = scraper.scrape_sync("https://sam.gov/opp/123/view")
        assert result == expected


class TestScrapeSamOpportunity:
    def test_explicit_server_mode(self):
        expected = {"success": True, "description": "test"}
        mock_scraper = AsyncMock()
        mock_scraper.scrape_opportunity.return_value = expected
        mock_scraper.__aenter__ = AsyncMock(return_value=mock_scraper)
        mock_scraper.__aexit__ = AsyncMock(return_value=False)
        with patch("govbizops.sam_scraper.SAMWebScraper", return_value=mock_scraper):
            result = scrape_sam_opportunity(
                "https://sam.gov/opp/123/view", server_mode=True
            )
        assert result == expected

    def test_auto_detect_kubernetes(self, monkeypatch):
        monkeypatch.setenv("KUBERNETES_SERVICE_HOST", "10.0.0.1")
        monkeypatch.setenv("DISPLAY", ":0")
        expected = {"success": True}
        mock_scraper = AsyncMock()
        mock_scraper.scrape_opportunity.return_value = expected
        mock_scraper.__aenter__ = AsyncMock(return_value=mock_scraper)
        mock_scraper.__aexit__ = AsyncMock(return_value=False)
        with patch("govbizops.sam_scraper.SAMWebScraper", return_value=mock_scraper):
            result = scrape_sam_opportunity("https://sam.gov/opp/123/view")
        assert result == expected

    def test_auto_detect_no_display(self, monkeypatch):
        monkeypatch.delenv("KUBERNETES_SERVICE_HOST", raising=False)
        monkeypatch.delenv("DISPLAY", raising=False)
        expected = {"success": True}
        mock_scraper = AsyncMock()
        mock_scraper.scrape_opportunity.return_value = expected
        mock_scraper.__aenter__ = AsyncMock(return_value=mock_scraper)
        mock_scraper.__aexit__ = AsyncMock(return_value=False)
        with patch("govbizops.sam_scraper.SAMWebScraper", return_value=mock_scraper):
            result = scrape_sam_opportunity("https://sam.gov/opp/123/view")
        assert result == expected

    @pytest.mark.asyncio
    async def test_from_running_loop(self):
        """scrape_sam_opportunity should work when called from inside a running event loop."""
        expected = {"success": True, "description": "from loop"}
        mock_scraper = AsyncMock()
        mock_scraper.scrape_opportunity.return_value = expected
        mock_scraper.__aenter__ = AsyncMock(return_value=mock_scraper)
        mock_scraper.__aexit__ = AsyncMock(return_value=False)
        with patch("govbizops.sam_scraper.SAMWebScraper", return_value=mock_scraper):
            result = scrape_sam_opportunity("https://sam.gov/opp/123/view")
        assert result == expected
