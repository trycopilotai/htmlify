import hashlib
import importlib.util
import json
import math
import struct
import subprocess
import tempfile
import unittest
import zlib
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples"
ASSETS = ROOT / "assets"
BUILD_SCRIPT = ASSETS / "build.py"
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
                EXAMPLES / mode / "manifest.json"
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
                    "release-readiness.md"
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
                    "examples/formal/delivery-brief.md"
                )
            self.assertEqual(
                git_blob(
                    manifest["input_commit"],
                    manifest["historical_input_path"],
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
                showcase / "manifest.json"
            )
            manifest_text = (
                showcase / "manifest.json"
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
                showcase / "run.md"
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
                f"examples/showcase/{slug}/source.md"
            )
            self.assertEqual(
                git_blob(
                    manifest["input_commit"],
                    manifest["historical_input_path"],
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
                manifest["historical_output_path"],
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
            EXAMPLES / "formal" / "manifest.json"
        )
        self.assertEqual(manifest["pdf_backend"], "chrome")
        self.assertEqual(manifest["pdf_pages"], 1)
        self.assertFalse(manifest["output_edited"])

    def test_curated_transcript_preserves_historical_paths(
        self,
    ) -> None:
        manifest = read_json(
            EXAMPLES / "curated" / "manifest.json"
        )
        transcript = (
            EXAMPLES / "curated" / "run.md"
        ).read_text(encoding="utf-8")
        self.assertIn("**Mode:** Curated", transcript)
        self.assertIn(
            manifest["historical_input_path"],
            transcript,
        )
        self.assertIn("examples/curated/index.html", transcript)
        self.assertNotIn("/Users/", transcript)
        self.assertNotIn("/tmp/", transcript)

    def test_launch_assets_have_expected_dimensions(
        self,
    ) -> None:
        specification = importlib.util.spec_from_file_location(
            "htmlify_asset_builder_committed_media",
            BUILD_SCRIPT,
        )
        if specification is None:
            self.fail("Could not load the asset builder")
        if specification.loader is None:
            self.fail("Asset builder has no loader")
        builder = importlib.util.module_from_spec(specification)
        specification.loader.exec_module(builder)

        expected_media = {
            "social-preview.png",
        }
        self.assertEqual(
            builder.png_dimensions(
                ASSETS / "social-preview.png"
            ),
            (1280, 640),
        )
        for slug in SHOWCASE_SLUGS:
            poster = ASSETS / f"{slug}-poster.png"
            animation = ASSETS / f"{slug}.gif"
            expected_media.add(poster.name)
            expected_media.add(animation.name)
            self.assertEqual(
                builder.png_dimensions(poster),
                (1280, 720),
            )
            self.assertEqual(
                builder.gif_dimensions(animation),
                (1280, 720),
            )
            metadata = builder.gif_metadata(animation)
            self.assertEqual(
                metadata.frame_count,
                3,
            )
            self.assertEqual(
                metadata.delays,
                (100, 100, 200),
            )
            self.assertTrue(metadata.loops_forever)

        actual_media = {
            path.name
            for path in ASSETS.iterdir()
            if path.suffix in {".gif", ".png"}
        }
        self.assertEqual(actual_media, expected_media)

    def test_reader_visible_source_paths_are_current(self) -> None:
        curated = (
            EXAMPLES / "curated" / "index.html"
        ).read_text(encoding="utf-8")
        publication = (
            EXAMPLES
            / "showcase"
            / "publication-sprint"
            / "rich.html"
        ).read_text(encoding="utf-8")

        self.assertIn(
            "examples/curated/release-readiness.md",
            curated,
        )
        self.assertNotIn("release-readiness.gpt.md", curated)
        self.assertIn(
            "Curated from <strong>source.md</strong>",
            publication,
        )
        self.assertNotIn("source.gpt.md", publication)

    def test_showcases_have_three_committed_states(
        self,
    ) -> None:
        expected = {
            "source.md",
            "formal.html",
            "rich.html",
            "manifest.json",
            "run.md",
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
                showcase / "source.md"
            ).read_text(encoding="utf-8")
            formal = (
                showcase / "formal.html"
            ).read_text(encoding="utf-8")
            rich = (
                showcase / "rich.html"
            ).read_text(encoding="utf-8")
            self.assertIn("synthetic example", source.lower())
            self.assertIn("<html", formal.lower())
            self.assertIn("<html", rich.lower())

    def test_declared_text_contrast_meets_wcag_aa(
        self,
    ) -> None:
        audit = read_json(
            EXAMPLES / "contrast-audit.json"
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
                / "rich.html"
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
                        str(showcase / "source.md"),
                        "--output",
                        str(generated),
                    ],
                    check=True,
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(
                    generated.read_bytes(),
                    (showcase / "formal.html").read_bytes(),
                    slug,
                )

    def test_rich_showcases_preserve_contract_facts(
        self,
    ) -> None:
        publication = (
            EXAMPLES
            / "showcase"
            / "publication-sprint"
            / "rich.html"
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
            / "rich.html"
        ).read_text(encoding="utf-8")
        self.assertIn(
            "Restart the service with the matching digest.",
            control_plane,
        )

        design = (
            EXAMPLES
            / "showcase"
            / "design-evolution"
            / "rich.html"
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
                    output_root / f"{slug}-poster.png"
                ).write_bytes(self.png_header(1280, 720))
                (
                    output_root / f"{slug}.gif"
                ).write_bytes(self.gif_header(1280, 720))

            with self.assertRaises(SystemExit):
                builder.validate_assets(output_root)

    def test_png_parser_rejects_corrupt_chunks_crc_and_iend(
        self,
    ) -> None:
        specification = importlib.util.spec_from_file_location(
            "htmlify_asset_builder_corrupt_png",
            BUILD_SCRIPT,
        )
        if specification is None:
            self.fail("Could not load the asset builder")
        if specification.loader is None:
            self.fail("Asset builder has no loader")

        builder = importlib.util.module_from_spec(specification)
        specification.loader.exec_module(builder)
        valid = self.minimal_png(1, 1)
        corrupt_crc = bytearray(valid)
        corrupt_crc[29] ^= 1
        header = (
            struct.pack(">II", 1, 1)
            + b"\x08\x02\x00\x00\x00"
        )
        signature = b"\x89PNG\r\n\x1a\n"
        invalid_idat = (
            signature
            + self.png_chunk(b"IHDR", header)
            + self.png_chunk(b"IDAT", b"not-zlib")
            + self.png_chunk(b"IEND", b"")
        )
        misordered_transparency = (
            signature
            + self.png_chunk(b"IHDR", header)
            + self.png_chunk(
                b"IDAT",
                zlib.compress(b"\x00\x00\x00\x00"),
            )
            + self.png_chunk(b"tRNS", b"\x00" * 6)
            + self.png_chunk(b"IEND", b"")
        )
        indexed_header = (
            struct.pack(">II", 1, 1)
            + b"\x08\x03\x00\x00\x00"
        )
        background_before_palette = (
            signature
            + self.png_chunk(b"IHDR", indexed_header)
            + self.png_chunk(b"bKGD", b"\x00")
            + self.png_chunk(
                b"PLTE",
                b"\x00\x00\x00\xff\xff\xff",
            )
            + self.png_chunk(
                b"IDAT",
                zlib.compress(b"\x00\x00"),
            )
            + self.png_chunk(b"IEND", b"")
        )
        histogram_without_palette = (
            signature
            + self.png_chunk(b"IHDR", header)
            + self.png_chunk(b"hIST", b"")
            + self.png_chunk(
                b"IDAT",
                zlib.compress(b"\x00\x00\x00\x00"),
            )
            + self.png_chunk(b"IEND", b"")
        )
        invalid_background = (
            signature
            + self.png_chunk(b"IHDR", header)
            + self.png_chunk(b"bKGD", b"")
            + self.png_chunk(
                b"IDAT",
                zlib.compress(b"\x00\x00\x00\x00"),
            )
            + self.png_chunk(b"IEND", b"")
        )
        valid_image_data = self.png_chunk(
            b"IDAT",
            zlib.compress(b"\x00\x00\x00\x00"),
        )
        suggested_palette = self.png_chunk(
            b"sPLT",
            b"palette\0\x08" + b"\x00\x00\x00\xff\x00\x01",
        )
        misplaced_suggested_palette = (
            signature
            + self.png_chunk(b"IHDR", header)
            + valid_image_data
            + suggested_palette
            + self.png_chunk(b"IEND", b"")
        )
        one_bit_indexed_header = (
            struct.pack(">II", 1, 1)
            + b"\x01\x03\x00\x00\x00"
        )
        indexed_out_of_palette = (
            signature
            + self.png_chunk(b"IHDR", one_bit_indexed_header)
            + self.png_chunk(b"PLTE", b"\x00\x00\x00")
            + self.png_chunk(
                b"IDAT",
                zlib.compress(b"\x00\x80"),
            )
            + self.png_chunk(b"IEND", b"")
        )
        invalid_icc_profile = (
            signature
            + self.png_chunk(b"IHDR", header)
            + self.png_chunk(
                b"iCCP",
                b"profile\0\0" + zlib.compress(b"not-an-icc-profile"),
            )
            + valid_image_data
            + self.png_chunk(b"IEND", b"")
        )
        invalid_exif_profile = (
            signature
            + self.png_chunk(b"IHDR", header)
            + self.png_chunk(
                b"eXIf",
                b"II\x2a\x00\x00\x00\x00\x00",
            )
            + valid_image_data
            + self.png_chunk(b"IEND", b"")
        )
        invalid_text_chunks = {
            "text-null": self.png_chunk(
                b"tEXt",
                b"k\0a\0b",
            ),
            "compressed-text-null": self.png_chunk(
                b"zTXt",
                b"k\0\0" + zlib.compress(b"a\0b"),
            ),
            "international-text-null": self.png_chunk(
                b"iTXt",
                b"k\0\0\0\0\0a\0b",
            ),
            "international-language": self.png_chunk(
                b"iTXt",
                b"k\0\0\0-\0\0text",
            ),
        }
        corruptions = {
            "header-only": self.png_header(1, 1),
            "crc": bytes(corrupt_crc),
            "invalid-idat": invalid_idat,
            "misordered-transparency": misordered_transparency,
            "background-before-palette": (
                background_before_palette
            ),
            "histogram-without-palette": (
                histogram_without_palette
            ),
            "invalid-background": invalid_background,
            "misplaced-suggested-palette": (
                misplaced_suggested_palette
            ),
            "indexed-out-of-palette": indexed_out_of_palette,
            "invalid-icc-profile": invalid_icc_profile,
            "invalid-exif-profile": invalid_exif_profile,
            "missing-iend": valid[:-12],
            "trailing-data": valid + b"\x00",
        }
        for label, text_chunk in invalid_text_chunks.items():
            corruptions[label] = (
                signature
                + self.png_chunk(b"IHDR", header)
                + text_chunk
                + valid_image_data
                + self.png_chunk(b"IEND", b"")
            )

        with tempfile.TemporaryDirectory() as temporary:
            for label, data in corruptions.items():
                with self.subTest(label=label):
                    path = Path(temporary) / f"{label}.png"
                    path.write_bytes(data)
                    with self.assertRaises(SystemExit):
                        builder.png_metadata(path)

    def test_gif_parser_rejects_corrupt_structure(
        self,
    ) -> None:
        specification = importlib.util.spec_from_file_location(
            "htmlify_asset_builder_corrupt_gif",
            BUILD_SCRIPT,
        )
        if specification is None:
            self.fail("Could not load the asset builder")
        if specification.loader is None:
            self.fail("Asset builder has no loader")

        builder = importlib.util.module_from_spec(specification)
        specification.loader.exec_module(builder)
        valid = self.minimal_gif(1, 1)
        descriptor = valid.find(b"\x2c")
        self.assertNotEqual(descriptor, -1)
        screen_with_table = valid[:19]
        no_color_table = bytearray(valid)
        no_color_table[10] = 0
        del no_color_table[13:19]
        invalid_lzw = valid.replace(
            b"\x02\x02\x4c\x01\x00",
            b"\x02\x03xyz\x00",
            1,
        )
        reserved_descriptor = bytearray(valid)
        reserved_descriptor[descriptor + 9] = 0x18
        conflicting_loop = (
            valid[:19]
            + b"\x21\xff\x0bNETSCAPE2.0"
            + b"\x03\x01\x01\x00\x00"
            + valid[19:]
        )
        invalid_application_identifier = (
            valid[:19]
            + b"\x21\xff\x0b"
            + b"\x00" * 11
            + b"\x00"
            + valid[19:]
        )
        invalid_transparent_index = valid.replace(
            b"\x21\xf9\x04\x00\x64\x00\x00\x00",
            b"\x21\xf9\x04\x01\x64\x00\x02\x00",
            1,
        )
        invalid_plain_text = (
            valid[:descriptor]
            + b"\x21\x01\x0c"
            + b"\x00\x00\x00\x00\x01\x00\x01\x00"
            + b"\x01\x01\xff\xff\x00"
            + valid[descriptor:]
        )
        nonascii_plain_text = (
            valid[:descriptor]
            + b"\x21\x01\x0c"
            + b"\x00\x00\x00\x00\x01\x00\x01\x00"
            + b"\x01\x01\x00\x01\x01\xff\x00"
            + valid[descriptor:]
        )
        nonascii_comment = (
            valid[:19]
            + b"\x21\xfe\x01\xff\x00"
            + valid[19:]
        )
        corruptions = {
            "descriptor": valid[: descriptor + 5],
            "extension": (
                screen_with_table + b"\x21\xfe\x03abc\x3b"
            ),
            "no-color-table": bytes(no_color_table),
            "invalid-lzw": invalid_lzw,
            "reserved-descriptor": bytes(reserved_descriptor),
            "conflicting-loop": conflicting_loop,
            "invalid-application-identifier": (
                invalid_application_identifier
            ),
            "invalid-transparent-index": invalid_transparent_index,
            "invalid-plain-text": invalid_plain_text,
            "nonascii-plain-text": nonascii_plain_text,
            "nonascii-comment": nonascii_comment,
            "no-frames": screen_with_table + b"\x3b",
            "missing-trailer": valid[:-1],
            "trailing-data": valid + b"\x00",
        }

        with tempfile.TemporaryDirectory() as temporary:
            valid_path = Path(temporary) / "valid.gif"
            valid_path.write_bytes(valid)
            metadata = builder.gif_metadata(valid_path)
            self.assertEqual(metadata.frame_count, 1)
            self.assertEqual(metadata.delays, (100,))
            self.assertTrue(metadata.loops_forever)

            for label, data in corruptions.items():
                with self.subTest(label=label):
                    path = Path(temporary) / f"{label}.gif"
                    path.write_bytes(data)
                    with self.assertRaises(SystemExit):
                        builder.gif_metadata(path)

    def test_asset_check_rejects_stale_source_fingerprint(
        self,
    ) -> None:
        specification = importlib.util.spec_from_file_location(
            "htmlify_asset_builder_fingerprint",
            BUILD_SCRIPT,
        )
        if specification is None:
            self.fail("Could not load the asset builder")
        if specification.loader is None:
            self.fail("Asset builder has no loader")

        builder = importlib.util.module_from_spec(specification)
        specification.loader.exec_module(builder)

        with tempfile.TemporaryDirectory() as temporary:
            asset = Path(temporary) / "social-preview.png"
            source = ASSETS / "social-preview.png"
            asset.write_bytes(source.read_bytes())
            fingerprint = builder.source_fingerprint()
            builder.validate_source_stamp(asset, fingerprint)
            with self.assertRaises(SystemExit):
                builder.validate_source_stamp(
                    asset,
                    "0" * len(fingerprint),
                )

    def test_evidence_lock_matches_reader_surfaces(
        self,
    ) -> None:
        lock = read_json(
            EXAMPLES / "evidence-lock.json"
        )
        for relative_path, expected in lock["files"].items():
            index = subprocess.run(
                ["git", "ls-files", "-s", "--", relative_path],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )
            fields = index.stdout.split()
            self.assertGreaterEqual(
                len(fields),
                4,
                relative_path,
            )
            self.assertIn(
                fields[0],
                {"100644", "100755"},
                relative_path,
            )
            worktree_actual = sha256(ROOT / relative_path)
            self.assertEqual(
                worktree_actual,
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
    def png_header(width: int, height: int) -> bytes:
        return (
            b"\x89PNG\r\n\x1a\n"
            + b"\x00" * 8
            + struct.pack(">II", width, height)
        )

    @staticmethod
    def png_chunk(chunk_type: bytes, data: bytes) -> bytes:
        checksum = zlib.crc32(chunk_type + data)
        checksum &= 0xFFFFFFFF
        return (
            struct.pack(">I", len(data))
            + chunk_type
            + data
            + struct.pack(">I", checksum)
        )

    @staticmethod
    def minimal_png(width: int, height: int) -> bytes:
        header = (
            struct.pack(">II", width, height)
            + b"\x08\x02\x00\x00\x00"
        )
        pixels = zlib.compress(b"\x00\x00\x00\x00")
        return (
            b"\x89PNG\r\n\x1a\n"
            + EvidenceTest.png_chunk(b"IHDR", header)
            + EvidenceTest.png_chunk(b"IDAT", pixels)
            + EvidenceTest.png_chunk(b"IEND", b"")
        )

    @staticmethod
    def gif_header(width: int, height: int) -> bytes:
        return b"GIF89a" + struct.pack("<HH", width, height)

    @staticmethod
    def minimal_gif(width: int, height: int) -> bytes:
        screen = (
            b"GIF89a"
            + struct.pack("<HH", width, height)
            + b"\x80\x00\x00"
            + b"\x00\x00\x00\xff\xff\xff"
        )
        loop = b"\x21\xff\x0bNETSCAPE2.0\x03\x01\x00\x00\x00"
        control = b"\x21\xf9\x04\x00\x64\x00\x00\x00"
        descriptor = (
            b"\x2c"
            + b"\x00\x00\x00\x00"
            + struct.pack("<HH", width, height)
            + b"\x00"
        )
        image_data = b"\x02\x02\x4c\x01\x00"
        return screen + loop + control + descriptor + image_data + b"\x3b"

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
