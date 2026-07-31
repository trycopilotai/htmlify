#!/usr/bin/env python3
"""End-to-end tests for the bundled command-line programs."""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skill" / "scripts"
FIXTURE = ROOT / "tests" / "fixtures" / "formal-source.md"


class FormalCliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.directory = Path(self.temporary.name)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def run_script(
        self,
        script: str,
        *arguments: str,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPTS / script), *arguments],
            check=False,
            capture_output=True,
            text=True,
        )

    def test_markdown_to_html_cli(self) -> None:
        output = self.directory / "brief.html"
        result = self.run_script(
            "formal_md_to_html.py",
            str(FIXTURE),
            "--output",
            str(output),
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), str(output))
        self.assertGreater(output.stat().st_size, 0)
        self.assertIn(
            "<h1>Weekly Delivery Brief</h1>",
            output.read_text(encoding="utf-8"),
        )

    def test_combined_cli_can_stop_after_html(self) -> None:
        output = self.directory / "combined.html"
        result = self.run_script(
            "formal_render.py",
            str(FIXTURE),
            "--html",
            str(output),
            "--no-pdf",
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), str(output))
        self.assertTrue(output.exists())
        self.assertFalse(output.with_suffix(".pdf").exists())

    def test_combined_help_documents_output_flags(self) -> None:
        result = self.run_script("formal_render.py", "--help")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--html", result.stdout)
        self.assertIn("--pdf", result.stdout)
        self.assertIn("--no-pdf", result.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
