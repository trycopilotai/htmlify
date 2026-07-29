#!/usr/bin/env python3
"""Tests for PDF backend selection and output safety."""

from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skill" / "scripts" / "formal_html_to_pdf.py"


def load_pdf_renderer():
    spec = importlib.util.spec_from_file_location(
        "htmlify_formal_html_to_pdf",
        SCRIPT,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load formal_html_to_pdf.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FormalPdfTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.pdf = load_pdf_renderer()

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.directory = Path(self.temporary.name)
        self.source = self.directory / "input.html"
        self.destination = self.directory / "output.pdf"
        self.source.write_text("<h1>Brief</h1>", encoding="utf-8")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_backend_order_and_success_name(self) -> None:
        calls: list[str] = []

        def unavailable(_source: Path, _destination: Path) -> bool:
            calls.append("first")
            return False

        def working(_source: Path, destination: Path) -> bool:
            calls.append("second")
            destination.write_bytes(b"%PDF-working")
            return True

        candidates = (
            ("first", unavailable),
            ("second", working),
        )

        with mock.patch.object(
            self.pdf,
            "_backend_candidates",
            return_value=candidates,
        ):
            backend = self.pdf.to_pdf(
                self.source,
                self.destination,
            )

        self.assertEqual(backend, "second")
        self.assertEqual(calls, ["first", "second"])
        self.assertEqual(
            self.destination.read_bytes(),
            b"%PDF-working",
        )

    def test_failed_backends_preserve_existing_output(self) -> None:
        self.destination.write_bytes(b"existing")

        def failing(_source: Path, candidate: Path) -> bool:
            candidate.write_bytes(b"partial")
            return False

        candidates = (("broken", failing),)

        with mock.patch.object(
            self.pdf,
            "_backend_candidates",
            return_value=candidates,
        ):
            with self.assertRaises(RuntimeError):
                self.pdf.to_pdf(self.source, self.destination)

        self.assertEqual(
            self.destination.read_bytes(),
            b"existing",
        )

    def test_zero_byte_candidate_is_not_success(self) -> None:
        def empty(_source: Path, candidate: Path) -> bool:
            candidate.write_bytes(b"")
            return True

        candidates = (("empty", empty),)

        with mock.patch.object(
            self.pdf,
            "_backend_candidates",
            return_value=candidates,
        ):
            with self.assertRaises(RuntimeError):
                self.pdf.to_pdf(self.source, self.destination)

        self.assertFalse(self.destination.exists())

    def test_missing_source_is_rejected(self) -> None:
        missing = self.directory / "missing.html"

        with self.assertRaises(FileNotFoundError):
            self.pdf.to_pdf(missing, self.destination)


if __name__ == "__main__":
    unittest.main(verbosity=2)
