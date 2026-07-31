import hashlib
import importlib.util
import json
import math
import struct
import subprocess
import tempfile
import unittest
from html.parser import HTMLParser
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
RELEASE_SKILL_SHA256 = (
    "a4d310b9b9a621d31ac1bcf5cd7fafcc1a3dadb4ded"
    "9704aaaf0d8185d64c8a7"
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def git_blob(commit: str, relative_path: str) -> bytes:
    result = subprocess.run(
        ["git", "show", f"{commit}:{relative_path}"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    return result.stdout


class SemanticHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.problems: list[str] = []

    def handle_starttag(
        self,
        tag: str,
        attributes: list[tuple[str, str | None]],
    ) -> None:
        values = dict(attributes)
        aria_label = values.get("aria-label")
        if aria_label is not None:
            if tag in {"div", "dl", "ol", "ul"}:
                self.problems.append(
                    f"<{tag}> misuses aria-label: {aria_label}"
                )
        if tag == "div" and values.get("role") == "region":
            self.problems.append(
                '<div role="region"> should be a native section'
            )


class EvidenceTest(unittest.TestCase):
    def test_example_manifests_match_files(self) -> None:
        for mode in ("curated", "formal"):
            manifest_path = (
                EXAMPLES / mode / "manifest.gpt.json"
            )
            manifest_text = manifest_path.read_text(
                encoding="utf-8"
            )
            manifest = read_json(manifest_path)
            self.assertNotRegex(
                manifest_text,
                (
                    r"\b[0-9a-f]{8}-[0-9a-f]{4}-"
                    r"[0-9a-f]{4}-[0-9a-f]{4}-"
                    r"[0-9a-f]{12}\b"
                ),
            )
            self.assertEqual(manifest["mode"], mode)
            self.assertEqual(
                manifest["input_commit"],
                "7a074c7",
            )
            self.assertEqual(
                manifest["skill_sha256"],
                RELEASE_SKILL_SHA256,
            )
            self.assertEqual(
                sha256(ROOT / "skill" / "SKILL.md"),
                RELEASE_SKILL_SHA256,
            )
            if mode == "curated":
                source_relative = (
                    "examples/curated/"
                    "release-readiness.gpt.md"
                )
                self.assertEqual(
                    manifest["run_record"],
                    {
                        "kind": "output-last-message",
                        "edited": True,
                        "edit_method": (
                            "Prettier 3.7.4 repository "
                            "Markdown codec"
                        ),
                    },
                )
                self.assertTrue(manifest["output_edited"])
                self.assertEqual(
                    manifest["output_edit_method"],
                    "original agent session continuation",
                )
                self.assertGreaterEqual(
                    len(manifest["follow_up_prompts"]),
                    2,
                )
            else:
                source_relative = (
                    "examples/formal/delivery-brief.gpt.md"
                )
            self.assertEqual(
                git_blob(
                    manifest["input_commit"],
                    source_relative,
                ),
                (ROOT / source_relative).read_bytes(),
                source_relative,
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

    def test_showcase_manifests_match_real_runs(self) -> None:
        for slug in SHOWCASE_SLUGS:
            showcase = EXAMPLES / "showcase" / slug
            manifest = read_json(
                showcase / "manifest.gpt.json"
            )
            manifest_text = (
                showcase / "manifest.gpt.json"
            ).read_text(encoding="utf-8")
            self.assertNotRegex(
                manifest_text,
                (
                    r"\b[0-9a-f]{8}-[0-9a-f]{4}-"
                    r"[0-9a-f]{4}-[0-9a-f]{4}-"
                    r"[0-9a-f]{12}\b"
                ),
            )
            self.assertGreaterEqual(
                len(manifest["follow_up_prompts"]),
                1,
            )
            transcript = (
                showcase / "run.gpt.md"
            ).read_text(encoding="utf-8")

            self.assertEqual(manifest["mode"], "curated")
            self.assertEqual(
                manifest["input_commit"],
                "e3d5173",
            )
            self.assertEqual(
                manifest["skill_sha256"],
                RELEASE_SKILL_SHA256,
            )
            self.assertEqual(
                manifest["agent_version"],
                "codex-cli 0.146.0",
            )
            source_relative = (
                f"examples/showcase/{slug}/source.gpt.md"
            )
            self.assertEqual(
                git_blob(
                    manifest["input_commit"],
                    source_relative,
                ),
                (ROOT / source_relative).read_bytes(),
                source_relative,
            )
            self.assertTrue(manifest["output_edited"])
            self.assertEqual(
                manifest["output_edit_method"],
                "original agent session continuation",
            )
            self.assertEqual(
                manifest["run_record"],
                {
                    "kind": "output-last-message",
                    "edited": True,
                    "edit_method": (
                        "Prettier 3.7.4 repository "
                        "Markdown codec"
                    ),
                },
            )
            self.assertEqual(
                manifest["visual_qa"]["result"],
                "passed",
            )
            self.assertIn(
                f"examples/showcase/{slug}/rich.gpt.html",
                transcript,
            )
            self.assertNotIn("/Users/", transcript)
            self.assertNotIn("/tmp/", transcript)

            for relative_path, expected in manifest[
                "files"
            ].items():
                self.assertEqual(
                    sha256(ROOT / relative_path),
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
        self.assertFalse(manifest["output_edited"])

    def test_curated_transcript_names_public_paths(
        self,
    ) -> None:
        transcript = (
            EXAMPLES / "curated" / "run.gpt.md"
        ).read_text(encoding="utf-8")
        self.assertIn("**Mode:** Curated", transcript)
        self.assertIn(
            "examples/curated/release-readiness.gpt.md",
            transcript,
        )
        self.assertIn("examples/curated/index.html", transcript)
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
            "manifest.gpt.json",
            "run.gpt.md",
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

    def test_declared_text_contrast_meets_wcag_aa(
        self,
    ) -> None:
        audit = read_json(
            EXAMPLES / "contrast-audit.gpt.json"
        )
        minimum = audit["minimum_ratio"]
        for relative_path, pairs in audit[
            "documents"
        ].items():
            document = (
                ROOT / relative_path
            ).read_text(encoding="utf-8").lower()
            for pair in pairs:
                ratio = self.contrast_ratio(
                    pair["foreground"],
                    pair["background"],
                )
                self.assertGreaterEqual(
                    ratio,
                    minimum,
                    (
                        f"{relative_path}: {pair['label']} "
                        f"{ratio:.2f}:1"
                    ),
                )
                tokens = pair.get("tokens")
                if tokens is None:
                    tokens = [
                        pair["foreground"],
                        pair["background"],
                    ]
                for token in tokens:
                    self.assertIn(
                        token.lower(),
                        document,
                        f"{relative_path}: {pair['label']}",
                    )

    def test_curated_html_uses_native_labelled_semantics(
        self,
    ) -> None:
        paths = [
            EXAMPLES / "curated" / "index.html",
        ]
        for slug in SHOWCASE_SLUGS:
            paths.append(
                EXAMPLES
                / "showcase"
                / slug
                / "rich.gpt.html"
            )

        for path in paths:
            document = path.read_text(encoding="utf-8")
            self.assertTrue(
                document.startswith("<!DOCTYPE html>"),
                path,
            )
            parser = SemanticHTMLParser()
            parser.feed(document)
            parser.close()
            self.assertEqual(parser.problems, [], path)

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
                'class="empty-check" aria-hidden="true"'
            ),
            4,
        )
        self.assertEqual(
            publication.count("Not marked clear"),
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
        for size in ("12 px", "16 px", "32 px"):
            self.assertIn(size, design)
        self.assertIn("0 O 1 I l", design)

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
                ASSETS,
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

    def test_asset_validation_rejects_bad_timing(
        self,
    ) -> None:
        specification = importlib.util.spec_from_file_location(
            "htmlify_asset_builder_validation",
            BUILD_SCRIPT,
        )
        if specification is None:
            self.fail("Could not load the asset builder")
        if specification.loader is None:
            self.fail("Asset builder has no loader")

        builder = importlib.util.module_from_spec(specification)
        specification.loader.exec_module(builder)

        with tempfile.TemporaryDirectory() as temporary:
            output_root = Path(temporary)
            (output_root / "social-preview.png").write_bytes(
                self.png_header(1280, 640)
            )
            for slug in SHOWCASE_SLUGS:
                (
                    output_root / f"{slug}-poster.gpt.png"
                ).write_bytes(self.png_header(1280, 720))
                (
                    output_root / f"{slug}.gpt.gif"
                ).write_bytes(self.gif_header(1280, 720))

            with self.assertRaises(SystemExit):
                builder.validate_assets(output_root)

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

    @staticmethod
    def png_header(width: int, height: int) -> bytes:
        return (
            b"\x89PNG\r\n\x1a\n"
            + b"\x00" * 8
            + struct.pack(">II", width, height)
        )

    @staticmethod
    def gif_header(width: int, height: int) -> bytes:
        return b"GIF89a" + struct.pack("<HH", width, height)

    @staticmethod
    def contrast_ratio(
        foreground: str,
        background: str,
    ) -> float:
        first = EvidenceTest.relative_luminance(foreground)
        second = EvidenceTest.relative_luminance(background)
        lighter = max(first, second)
        darker = min(first, second)
        return (lighter + 0.05) / (darker + 0.05)

    @staticmethod
    def relative_luminance(color: str) -> float:
        value = color.removeprefix("#")
        channels = []
        for offset in (0, 2, 4):
            channel = int(value[offset : offset + 2], 16)
            normalized = channel / 255
            if normalized <= 0.04045:
                linear = normalized / 12.92
            else:
                linear = math.pow(
                    (normalized + 0.055) / 1.055,
                    2.4,
                )
            channels.append(linear)
        return (
            0.2126 * channels[0]
            + 0.7152 * channels[1]
            + 0.0722 * channels[2]
        )


if __name__ == "__main__":
    unittest.main()
