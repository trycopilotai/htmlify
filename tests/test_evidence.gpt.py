import hashlib
import importlib.util
import json
import struct
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples"
ASSETS = ROOT / "assets"
BUILD_SCRIPT = ASSETS / "build.gpt.py"
SHOWCASE_SLUGS = (
    "publication-sprint",
    "control-plane-status",
    "design-evolution",
)


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
        expected_media = {
            "social-preview.png",
        }
        self.assertEqual(
            self.png_dimensions(
                ASSETS / "social-preview.png"
            ),
            (1280, 640),
        )
        for slug in SHOWCASE_SLUGS:
            poster = ASSETS / f"{slug}-poster.gpt.png"
            animation = ASSETS / f"{slug}.gpt.gif"
            expected_media.add(poster.name)
            expected_media.add(animation.name)
            self.assertEqual(
                self.png_dimensions(poster),
                (1280, 720),
            )
            self.assertEqual(
                self.gif_dimensions(animation),
                (1280, 720),
            )
            self.assertEqual(
                animation.read_bytes().count(
                    b"\x21\xf9\x04"
                ),
                3,
            )
            self.assertEqual(
                self.gif_delays(animation),
                [100, 100, 200],
            )

        actual_media = {
            path.name
            for path in ASSETS.iterdir()
            if path.suffix in {".gif", ".png"}
        }
        self.assertEqual(actual_media, expected_media)

    def test_showcases_have_three_committed_states(
        self,
    ) -> None:
        expected = {
            "source.gpt.md",
            "formal.gpt.html",
            "rich.gpt.html",
        }
        for slug in SHOWCASE_SLUGS:
            showcase = EXAMPLES / "showcase" / slug
            actual = {
                path.name
                for path in showcase.iterdir()
                if path.is_file()
            }
            self.assertEqual(actual, expected)

            source = (
                showcase / "source.gpt.md"
            ).read_text(encoding="utf-8")
            formal = (
                showcase / "formal.gpt.html"
            ).read_text(encoding="utf-8")
            rich = (
                showcase / "rich.gpt.html"
            ).read_text(encoding="utf-8")
            self.assertIn("synthetic example", source.lower())
            self.assertIn("<html", formal.lower())
            self.assertIn("<html", rich.lower())

    def test_formal_showcases_rederive_from_source(
        self,
    ) -> None:
        renderer = (
            ROOT / "skill" / "scripts" / "formal_md_to_html.py"
        )
        with tempfile.TemporaryDirectory() as temporary:
            generated_root = Path(temporary)
            for slug in SHOWCASE_SLUGS:
                showcase = EXAMPLES / "showcase" / slug
                generated = generated_root / f"{slug}.html"
                subprocess.run(
                    [
                        "python3",
                        str(renderer),
                        str(showcase / "source.gpt.md"),
                        "--output",
                        str(generated),
                    ],
                    check=True,
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(
                    generated.read_bytes(),
                    (showcase / "formal.gpt.html").read_bytes(),
                    slug,
                )

    def test_rich_showcases_preserve_contract_facts(
        self,
    ) -> None:
        publication = (
            EXAMPLES
            / "showcase"
            / "publication-sprint"
            / "rich.gpt.html"
        ).read_text(encoding="utf-8")
        self.assertIn("Begin full narrative", publication)
        self.assertIn(
            "Introduction and findings are connected",
            publication,
        )
        self.assertNotIn("✓", publication)
        self.assertEqual(
            publication.count(
                'class="gate" role="checkbox" '
                'aria-checked="false"'
            ),
            4,
        )

        control_plane = (
            EXAMPLES
            / "showcase"
            / "control-plane-status"
            / "rich.gpt.html"
        ).read_text(encoding="utf-8")
        self.assertIn(
            "Restart the service with the matching digest.",
            control_plane,
        )

        design = (
            EXAMPLES
            / "showcase"
            / "design-evolution"
            / "rich.gpt.html"
        ).read_text(encoding="utf-8")
        self.assertRegex(
            design,
            (
                r"\.micro span:nth-child\(3\) \{\s+"
                r"font-size: 32px;"
            ),
        )

    def test_asset_builder_orders_source_formal_rich(
        self,
    ) -> None:
        specification = importlib.util.spec_from_file_location(
            "htmlify_asset_builder",
            BUILD_SCRIPT,
        )
        if specification is None:
            self.fail("Could not load the asset builder")
        if specification.loader is None:
            self.fail("Asset builder has no loader")

        builder = importlib.util.module_from_spec(specification)
        specification.loader.exec_module(builder)

        captured_views = []
        animation_frames = []
        poster_frames = []

        def fake_capture(
            chrome: str,
            source: Path,
            destination: Path,
            width: int,
            height: int,
        ) -> None:
            captured_views.append(
                source.read_text(encoding="utf-8")
            )
            destination.write_bytes(b"capture")

        def fake_crop_frame(
            magick: str,
            source: Path,
            destination: Path,
        ) -> None:
            destination.write_bytes(b"frame")

        def fake_build_poster(
            frame: Path,
            destination: Path,
        ) -> None:
            poster_frames.append(frame.name)

        def fake_build_animation(
            magick: str,
            frames: list[Path],
            destination: Path,
        ) -> None:
            animation_frames.extend(
                frame.name for frame in frames
            )

        builder.capture = fake_capture
        builder.crop_frame = fake_crop_frame
        builder.build_poster = fake_build_poster
        builder.build_animation = fake_build_animation

        with tempfile.TemporaryDirectory() as temporary:
            builder.build_showcase(
                "chrome",
                "magick",
                Path(temporary),
                "publication-sprint",
                "Publication sprint",
            )

        self.assertIn("01 · Source Markdown", captured_views[0])
        self.assertIn("02 · Formal HTML", captured_views[1])
        self.assertIn("03 · Rich HTML", captured_views[2])
        self.assertEqual(
            animation_frames,
            [
                "source-frame.png",
                "formal-frame.png",
                "rich-frame.png",
            ],
        )
        self.assertEqual(poster_frames, ["rich-frame.png"])

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
                    "'agents/openai.yaml', "
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

    @staticmethod
    def gif_delays(path: Path) -> list[int]:
        data = path.read_bytes()
        marker = b"\x21\xf9\x04"
        delays = []
        offset = 0
        while True:
            offset = data.find(marker, offset)
            if offset == -1:
                break
            delays.append(
                struct.unpack("<H", data[offset + 4 : offset + 6])[
                    0
                ]
            )
            offset += len(marker)
        return delays


if __name__ == "__main__":
    unittest.main()
