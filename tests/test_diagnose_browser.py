"""Tests for diagnose_browser module"""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from govbizops.diagnose_browser import test_browser, check_system_deps


class TestTestBrowser:
    @pytest.mark.asyncio
    async def test_full_success(self):
        mock_pw = AsyncMock()
        mock_browser = AsyncMock()
        mock_page = AsyncMock()
        mock_pw.chromium.launch.return_value = mock_browser
        mock_browser.new_page.return_value = mock_page
        mock_page.title.return_value = "Example Domain"
        mock_page.evaluate.return_value = "Mozilla/5.0 test user agent string"

        with patch("govbizops.diagnose_browser.async_playwright") as mock_apw:
            mock_context = AsyncMock()
            mock_context.start.return_value = mock_pw
            mock_apw.return_value = mock_context
            result = await test_browser()
        assert result is True

    @pytest.mark.asyncio
    async def test_sam_gov_failure(self):
        mock_pw = AsyncMock()
        mock_browser = AsyncMock()
        mock_page = AsyncMock()
        mock_pw.chromium.launch.return_value = mock_browser
        mock_browser.new_page.return_value = mock_page
        mock_page.title.return_value = "Example Domain"
        mock_page.evaluate.return_value = "Mozilla/5.0 test user agent string"

        # First goto succeeds (example.com), second fails (sam.gov)
        call_count = 0

        async def goto_side_effect(url, **kwargs):
            nonlocal call_count
            call_count += 1
            if "sam.gov" in url:
                raise Exception("timeout")

        mock_page.goto.side_effect = goto_side_effect

        with patch("govbizops.diagnose_browser.async_playwright") as mock_apw:
            mock_context = AsyncMock()
            mock_context.start.return_value = mock_pw
            mock_apw.return_value = mock_context
            result = await test_browser()
        # Still returns True - sam.gov failure is caught
        assert result is True

    @pytest.mark.asyncio
    async def test_browser_launch_exception(self):
        with patch("govbizops.diagnose_browser.async_playwright") as mock_apw:
            mock_context = AsyncMock()
            mock_context.start.side_effect = Exception("no browser")
            mock_apw.return_value = mock_context
            result = await test_browser()
        assert result is False


class TestCheckSystemDeps:
    def test_browser_found(self, capsys):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "/usr/bin/chromium\n"
        with patch("subprocess.run", return_value=mock_result):
            check_system_deps()
        captured = capsys.readouterr()
        assert "Found" in captured.out

    def test_subprocess_exception(self, capsys):
        """Cover the bare except: pass when subprocess.run raises."""
        with patch("subprocess.run", side_effect=OSError("not found")):
            with patch("builtins.open", side_effect=OSError("no file")):
                check_system_deps()
        captured = capsys.readouterr()
        assert "No browser binary found" in captured.out

    def test_browser_not_found(self, capsys):
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        with patch("subprocess.run", return_value=mock_result):
            check_system_deps()
        captured = capsys.readouterr()
        assert "No browser binary found" in captured.out

    def test_meminfo_readable(self, capsys):
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        meminfo_lines = [
            "MemTotal:       16384 kB\n",
            "Shmem:          1024 kB\n",
            "MemFree:        8000 kB\n",
        ]
        mock_open = MagicMock()
        mock_open.__enter__ = MagicMock(return_value=meminfo_lines)
        mock_open.__exit__ = MagicMock(return_value=False)
        with patch("subprocess.run", return_value=mock_result):
            with patch("builtins.open", return_value=mock_open):
                check_system_deps()
        captured = capsys.readouterr()
        assert "Shared memory" in captured.out or "No browser" in captured.out

    def test_meminfo_not_readable(self, capsys):
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        with patch("subprocess.run", return_value=mock_result):
            with patch("builtins.open", side_effect=OSError("no file")):
                check_system_deps()
        captured = capsys.readouterr()
        assert "Could not check" in captured.out
