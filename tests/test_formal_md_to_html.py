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

    def test_escaped_pipe_stays_inside_table_cell(self) -> None:
        rendered = self.renderer.render(
            "# Table\n\n"
            "| Expression | Status |\n"
            "| --- | --- |\n"
            "| a \\| b | intact |\n"
        )

        body_row = rendered.split("<tbody>", 1)[1].split(
            "</tbody>",
            1,
        )[0]
        self.assertEqual(body_row.count("<td"), 2)
        self.assertIn(">a | b</td>", body_row)
        self.assertIn(">intact</td>", body_row)

    def test_escaped_trailing_pipe_is_not_a_row_delimiter(
        self,
    ) -> None:
        rendered = self.renderer.render(
            "# Table\n\n"
            "| Expression |\n"
            "| --- |\n"
            "| a \\|"
        )

        body_row = rendered.split("<tbody>", 1)[1].split(
            "</tbody>",
            1,
        )[0]
        self.assertEqual(body_row.count("<td"), 1)
        self.assertIn(">a |</td>", body_row)

    def test_pipe_escape_preserves_gfm_backslash_runs(
        self,
    ) -> None:
        cases = {
            r"| a \| b | c |": (["a | b", "c"], "a | b"),
            r"| a \\| b | c |": (["a \\| b", "c"], "a | b"),
            r"| a \\\| b | c |": (
                ["a \\\\| b", "c"],
                "a \\| b",
            ),
            r"| a \\\\| b | c |": (
                ["a \\\\\\| b", "c"],
                "a \\| b",
            ),
        }

        for source, expectations in cases.items():
            with self.subTest(source=source):
                split_expected, rendered_expected = expectations
                self.assertEqual(
                    self.renderer._split_row(source),
                    split_expected,
                )
                rendered = self.renderer.render(
                    "# Table\n\n"
                    "| Expression | Status |\n"
                    "| --- | --- |\n"
                    + source
                    + "\n"
                )
                self.assertIn(
                    ">" + rendered_expected + "</td>",
                    rendered,
                )

    def test_escaped_closing_pipe_preserves_backslash_runs(
        self,
    ) -> None:
        cases = {
            r"| a \|": ["a |"],
            r"| a \\|": ["a \\|"],
            r"| a \\\|": ["a \\\\|"],
            r"| a \\\\|": ["a \\\\\\|"],
        }

        for source, expected in cases.items():
            with self.subTest(source=source):
                self.assertEqual(
                    self.renderer._split_row(source),
                    expected,
                )

    def test_code_span_keeps_non_escape_backslashes(self) -> None:
        for count in range(1, 5):
            with self.subTest(count=count):
                row = "| `a " + "\\" * count + "| b` | c |"
                rendered = self.renderer.render(
                    "# Table\n\n"
                    "| Expression | Status |\n"
                    "| --- | --- |\n"
                    + row
                    + "\n"
                )
                expected = (
                    "<code>a "
                    + "\\" * (count - 1)
                    + "| b</code>"
                )
                self.assertIn(expected, rendered)

    def test_link_destination_normalizes_pipe_backslashes(
        self,
    ) -> None:
        for count in range(1, 5):
            with self.subTest(count=count):
                destination = (
                    "https://example.test/a"
                    + "\\" * count
                    + "|b"
                )
                row = "| [x](" + destination + ") | c |"
                rendered = self.renderer.render(
                    "# Table\n\n"
                    "| Expression | Status |\n"
                    "| --- | --- |\n"
                    + row
                    + "\n"
                )
                expected = (
                    'href="https://example.test/a'
                    + "%5C" * ((count - 1) // 2)
                    + '|b"'
                )
                self.assertIn(expected, rendered)

    def test_ordered_list_preserves_non_one_start(self) -> None:
        rendered = self.renderer.render(
            "# Sequence\n\n"
            "3. Third\n"
            "4. Fourth\n"
        )

        self.assertIn('<ol start="3">', rendered)
        self.assertIn("<li>Third</li>", rendered)
        self.assertIn("<li>Fourth</li>", rendered)

    def test_large_ordered_list_start_does_not_raise(self) -> None:
        marker = "9" * 5000
        rendered = self.renderer.render(
            "# Sequence\n\n" + marker + ". Item\n"
        )

        self.assertIn('<ol start="' + marker + '">', rendered)
        self.assertIn("<li>Item</li>", rendered)

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
