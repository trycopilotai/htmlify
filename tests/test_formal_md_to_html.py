#!/usr/bin/env python3
"""Tests for the standard-library Markdown renderer."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skill" / "scripts" / "formal_md_to_html.py"
FIXTURE = ROOT / "tests" / "fixtures" / "formal-source.md"


def load_renderer():
    spec = importlib.util.spec_from_file_location(
        "htmlify_formal_md_to_html",
        SCRIPT,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load formal_md_to_html.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FormalMarkdownTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.renderer = load_renderer()

    def test_fixture_renders_document_structure(self) -> None:
        source = FIXTURE.read_text(encoding="utf-8")
        rendered = self.renderer.render(source)

        self.assertIn("<title>Weekly Delivery Brief</title>", rendered)
        self.assertIn("<h1>Weekly Delivery Brief</h1>", rendered)
        self.assertIn('<h2 class="appendix">Appendix: Terms</h2>', rendered)
        self.assertIn("<ul>", rendered)
        self.assertIn("<table>", rendered)
        self.assertIn("<blockquote>", rendered)
        self.assertIn("<pre><code>", rendered)
        self.assertIn("<strong>Ready</strong>", rendered)

    def test_query_string_is_escaped_exactly_once(self) -> None:
        rendered = self.renderer._inline(
            "[evidence](https://example.com/report?a=1&b=2)"
        )

        self.assertIn(
            'href="https://example.com/report?a=1&amp;b=2"',
            rendered,
        )
        self.assertNotIn("&amp;amp;", rendered)

    def test_safe_link_schemes_are_active(self) -> None:
        cases = (
            "[relative](docs/report.html)",
            "[fragment](#result)",
            "[http](http://example.com)",
            "[https](https://example.com)",
            "[mail](mailto:security@example.com)",
        )

        for source in cases:
            with self.subTest(source=source):
                self.assertIn("<a href=", self.renderer._inline(source))

    def test_unsafe_link_schemes_remain_text(self) -> None:
        cases = (
            "[script](javascript:alert%281%29)",
            "[data](data:text/html,unsafe)",
            "[file](file:///etc/passwd)",
            "[network](//example.com/report)",
        )

        for source in cases:
            with self.subTest(source=source):
                rendered = self.renderer._inline(source)
                self.assertNotIn("<a href=", rendered)
                self.assertIn(source, rendered)

    def test_raw_html_is_escaped(self) -> None:
        rendered = self.renderer.render(
            "# Brief\n\n<script>alert('unsafe')</script>"
        )

        self.assertNotIn("<script>", rendered)
        self.assertIn("&lt;script&gt;", rendered)

    def test_table_alignment_is_explicit(self) -> None:
        rendered = self.renderer.render(
            "# Table\n\n"
            "| Left | Center | Right |\n"
            "| :--- | :---: | ---: |\n"
            "| A | B | C |\n"
        )

        self.assertIn('style="text-align:left"', rendered)
        self.assertIn('style="text-align:center"', rendered)
        self.assertIn('style="text-align:right"', rendered)

    def test_default_output_removes_markdown_suffix(self) -> None:
        cases = {
            "brief.md": "brief.html",
            "brief.gpt.md": "brief.html",
            "brief.markdown": "brief.html",
            "brief.txt": "brief.html",
        }

        for source, expected in cases.items():
            with self.subTest(source=source):
                actual = self.renderer.default_output(Path(source))
                self.assertEqual(actual, Path(expected))


if __name__ == "__main__":
    unittest.main(verbosity=2)
