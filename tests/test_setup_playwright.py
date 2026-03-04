"""Tests for setup_playwright module"""

import pytest
from unittest.mock import patch, MagicMock

from govbizops.setup_playwright import main


class TestMain:
    def test_success(self, capsys):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stderr = ""
        with patch(
            "govbizops.setup_playwright.subprocess.run", return_value=mock_result
        ):
            main()
        captured = capsys.readouterr()
        assert "successfully" in captured.out

    def test_failure(self, capsys):
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "install failed"
        with patch(
            "govbizops.setup_playwright.subprocess.run", return_value=mock_result
        ):
            main()
        captured = capsys.readouterr()
        assert "failed" in captured.out.lower()

    def test_subprocess_exception(self, capsys):
        with patch(
            "govbizops.setup_playwright.subprocess.run",
            side_effect=OSError("not found"),
        ):
            main()
        captured = capsys.readouterr()
        assert "Error" in captured.out
