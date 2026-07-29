import hashlib
import json
import struct
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples"
ASSETS = ROOT / "assets"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class EvidenceTest(unittest.TestCase):
    def test_example_manifests_match_files(self) -> None:
        for mode in ("curated", "formal"):
            manifest_path = (
                EXAMPLES / mode / "manifest.gpt.json"
            )
            manifest = read_json(manifest_path)
            self.assertEqual(manifest["mode"], mode)
            self.assertEqual(
                manifest["input_commit"],
                "7a074c7",
            )
            self.assertEqual(
                manifest["skill_sha256"],
                sha256(ROOT / "skill" / "SKILL.md"),
            )

            for relative_path, expected in manifest[
                "files"
            ].items():
                actual = sha256(ROOT / relative_path)
                self.assertEqual(
                    actual,
                    expected,
                    relative_path,
                )

    def test_formal_manifest_records_live_backend(
        self,
    ) -> None:
        manifest = read_json(
            EXAMPLES / "formal" / "manifest.gpt.json"
        )
        self.assertEqual(manifest["pdf_backend"], "chrome")
        self.assertEqual(manifest["pdf_pages"], 1)
        self.assertFalse(manifest["edited"])

    def test_curated_transcript_names_public_paths(
        self,
    ) -> None:
        transcript = (
            EXAMPLES / "curated" / "run.gpt.md"
        ).read_text(encoding="utf-8")
        self.assertIn("Selected mode: curated", transcript)
        self.assertIn(
            "examples/curated/release-readiness.gpt.md",
            transcript,
        )
        self.assertIn(
            "examples/curated/index.html",
            transcript,
        )
        self.assertNotIn("/Users/", transcript)
        self.assertNotIn("/tmp/", transcript)

    def test_launch_assets_have_expected_dimensions(
        self,
    ) -> None:
        self.assertEqual(
            self.png_dimensions(
                ASSETS / "social-preview.png"
            ),
            (1280, 640),
        )
        self.assertEqual(
            self.png_dimensions(ASSETS / "demo-poster.png"),
            (1280, 720),
        )
        self.assertEqual(
            self.gif_dimensions(ASSETS / "demo.gif"),
            (1280, 720),
        )
        self.assertGreater(
            (ASSETS / "demo.gif").read_bytes().count(
                b"\x21\xf9\x04"
            ),
            1,
        )

    def test_evidence_lock_matches_reader_surfaces(
        self,
    ) -> None:
        lock = read_json(
            EXAMPLES / "evidence-lock.gpt.json"
        )
        for relative_path, expected in lock["files"].items():
            actual = sha256(ROOT / relative_path)
            self.assertEqual(
                actual,
                expected,
                relative_path,
            )

    def test_documented_install_is_complete(self) -> None:
        result = subprocess.run(
            [
                "python3",
                "-c",
                (
                    "from pathlib import Path; "
                    "root = Path('skill'); "
                    "expected = {'SKILL.md', "
                    "'scripts/formal_md_to_html.py', "
                    "'scripts/formal_html_to_pdf.py', "
                    "'scripts/formal_render.py'}; "
                    "actual = {str(path.relative_to(root)) "
                    "for path in root.rglob('*') "
                    "if path.is_file() and "
                    "'__pycache__' not in path.parts}; "
                    "raise SystemExit(actual != expected)"
                ),
            ],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0)

    @staticmethod
    def png_dimensions(path: Path) -> tuple[int, int]:
        data = path.read_bytes()
        if data[:8] != b"\x89PNG\r\n\x1a\n":
            raise AssertionError(f"Not a PNG: {path}")
        return struct.unpack(">II", data[16:24])

    @staticmethod
    def gif_dimensions(path: Path) -> tuple[int, int]:
        data = path.read_bytes()
        if data[:6] not in (b"GIF87a", b"GIF89a"):
            raise AssertionError(f"Not a GIF: {path}")
        return struct.unpack("<HH", data[6:10])


if __name__ == "__main__":
    unittest.main()
