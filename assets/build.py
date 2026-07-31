#!/usr/bin/env python3

import argparse
from dataclasses import dataclass
import hashlib
import html
import shutil
import struct
import subprocess
import tempfile
import time
import zlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
SHOWCASE_ROOT = ROOT / "examples" / "showcase"
SOCIAL = ASSETS / "social-preview.html"
SHOWCASES = (
    ("publication-sprint", "Publication sprint"),
    ("control-plane-status", "Control plane status"),
    ("design-evolution", "Design evolution"),
)
STAMP_KEY = b"htmlify-source-sha256"


@dataclass(frozen=True)
class PngMetadata:
    width: int
    height: int
    text_chunks: tuple[bytes, ...]


@dataclass(frozen=True)
class GifMetadata:
    width: int
    height: int
    frame_count: int
    delays: tuple[int, ...]
    loops_forever: bool
    comments: tuple[bytes, ...]
    comment_spans: tuple[tuple[int, int], ...]
    trailer_offset: int


def png_keyword_end(
    data: bytes,
    path: Path,
    label: str,
) -> int:
    separator = data.find(b"\0")
    if separator < 1 or separator > 79:
        raise SystemExit(f"PNG {label} keyword is invalid: {path}")
    keyword = data[:separator]
    if keyword.startswith(b" ") or keyword.endswith(b" "):
        raise SystemExit(f"PNG {label} keyword spacing is invalid: {path}")
    if b"  " in keyword:
        raise SystemExit(f"PNG {label} keyword spacing is invalid: {path}")
    if any(
        not (32 <= value <= 126 or 161 <= value <= 255)
        for value in keyword
    ):
        raise SystemExit(f"PNG {label} keyword is invalid: {path}")
    return separator


def validate_png_zlib_payload(
    data: bytes,
    path: Path,
    label: str,
) -> bytes:
    decompressor = zlib.decompressobj()
    try:
        decoded = decompressor.decompress(data)
        decoded += decompressor.flush()
    except zlib.error as error:
        raise SystemExit(
            f"PNG {label} compressed data is invalid: {path}"
        ) from error
    if not decompressor.eof:
        raise SystemExit(
            f"PNG {label} compressed data is incomplete: {path}"
        )
    if decompressor.unused_data or decompressor.unconsumed_tail:
        raise SystemExit(
            f"PNG {label} compressed data has trailing bytes: {path}"
        )
    return decoded


def require_program(name: str) -> str:
    path = shutil.which(name)
    if path is None:
        raise SystemExit(f"Required program not found: {name}")
    return path


def find_imagemagick() -> str:
    for name in ("magick", "convert"):
        path = shutil.which(name)
        if path is not None:
            return path
    raise SystemExit("ImageMagick is required")


def find_chrome() -> str:
    candidates = [
        (
            "/Applications/Google Chrome.app/Contents/"
            "MacOS/Google Chrome"
        ),
        shutil.which("google-chrome"),
        shutil.which("chromium"),
        shutil.which("chromium-browser"),
    ]
    for candidate in candidates:
        if candidate is None:
            continue
        if Path(candidate).is_file():
            return candidate
    raise SystemExit("Chrome or Chromium is required")


def capture(
    chrome: str,
    source: Path,
    destination: Path,
    width: int,
    height: int,
) -> None:
    profile = destination.parent / (
        f"{destination.stem}-chrome-profile"
    )
    command = [
        chrome,
        "--headless=new",
        "--disable-gpu",
        "--hide-scrollbars",
        "--no-sandbox",
        "--disable-background-networking",
        "--disable-component-update",
        "--disable-default-apps",
        "--disable-sync",
        "--metrics-recording-only",
        "--no-first-run",
        "--no-default-browser-check",
        f"--user-data-dir={profile}",
        f"--window-size={width},{height}",
        f"--screenshot={destination}",
        source.resolve().as_uri(),
    ]
    process = subprocess.Popen(
        command,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        if (
            destination.is_file()
            and destination.stat().st_size > 0
        ):
            break
        if process.poll() is not None:
            break
        time.sleep(0.1)

    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)

    if not destination.is_file():
        raise SystemExit(f"Screenshot missing: {destination}")
    if destination.stat().st_size == 0:
        raise SystemExit(f"Screenshot is empty: {destination}")


def crop_frame(
    magick: str,
    source: Path,
    destination: Path,
) -> None:
    subprocess.run(
        [
            magick,
            str(source),
            "-resize",
            "1280x720^",
            "-gravity",
            "north",
            "-extent",
            "1280x720",
            "-strip",
            str(destination),
        ],
        check=True,
    )


def write_source_view(
    source: Path,
    destination: Path,
    title: str,
) -> None:
    rendered_lines = []
    for line in source.read_text(encoding="utf-8").splitlines():
        rendered = html.escape(line)
        if rendered == "":
            rendered = "&nbsp;"
        rendered_lines.append(f"<li><code>{rendered}</code></li>")

    lines = "\n".join(rendered_lines)
    destination.write_text(
        f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{html.escape(title)} source Markdown</title>
    <style>
      * {{ box-sizing: border-box; }}
      html, body {{ margin: 0; min-height: 100%; }}
      body {{
        background: #171a21;
        color: #e5e9f0;
        font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
      }}
      header {{
        position: sticky;
        top: 0;
        z-index: 2;
        display: flex;
        align-items: center;
        justify-content: space-between;
        min-height: 68px;
        padding: 14px 24px;
        border-bottom: 1px solid #343b48;
        background: #20242d;
      }}
      header strong {{
        color: #ffffff;
        font: 700 18px/1.2 ui-sans-serif, system-ui, sans-serif;
      }}
      header span {{
        color: #a9b5c8;
        font-size: 13px;
      }}
      .state {{
        border: 1px solid #9fb8ff;
        border-radius: 999px;
        padding: 7px 12px;
        color: #dce5ff;
        background: #263252;
        font: 700 12px/1 ui-sans-serif, system-ui, sans-serif;
        letter-spacing: 0.08em;
        text-transform: uppercase;
      }}
      ol {{
        margin: 0;
        padding: 18px 0 36px 70px;
        counter-reset: line;
      }}
      li {{
        min-height: 22px;
        padding: 0 28px 0 14px;
        border-left: 1px solid #343b48;
        color: #78859a;
        line-height: 22px;
      }}
      li::marker {{
        color: #78859a;
        font-size: 12px;
      }}
      code {{
        color: #e4e9f2;
        font-size: 13px;
        white-space: pre-wrap;
      }}
    </style>
  </head>
  <body>
    <header>
      <div>
        <strong>{html.escape(title)}</strong>
        <span> · source.md</span>
      </div>
      <div class="state">01 · Source Markdown</div>
    </header>
    <ol>
      {lines}
    </ol>
  </body>
</html>
""",
        encoding="utf-8",
    )


def write_labeled_view(
    source: Path,
    destination: Path,
    state: str,
    filename: str,
) -> None:
    document = source.read_text(encoding="utf-8")
    if "</head>" not in document:
        raise SystemExit(f"HTML has no closing head: {source}")
    if "<body" not in document:
        raise SystemExit(f"HTML has no body: {source}")

    base = f'<base href="{source.parent.resolve().as_uri()}/">'
    badge_style = """
    <style>
      .htmlify-showcase-state {
        position: fixed;
        top: 16px;
        right: 16px;
        z-index: 2147483647;
        border: 1px solid rgba(255, 255, 255, 0.5);
        border-radius: 999px;
        padding: 8px 12px;
        color: #ffffff;
        background: rgba(14, 21, 34, 0.88);
        box-shadow: 0 4px 18px rgba(0, 0, 0, 0.22);
        font: 700 12px/1 ui-sans-serif, system-ui, sans-serif;
        letter-spacing: 0.08em;
        text-transform: uppercase;
      }
    </style>
"""
    badge = (
        '<div class="htmlify-showcase-state">'
        f"{html.escape(state)} · {html.escape(filename)}"
        "</div>"
    )
    document = document.replace(
        "</head>",
        f"{base}{badge_style}</head>",
        1,
    )
    body_end = document.find(">", document.find("<body"))
    if body_end == -1:
        raise SystemExit(f"HTML has an incomplete body: {source}")
    document = (
        document[: body_end + 1]
        + badge
        + document[body_end + 1 :]
    )
    destination.write_text(document, encoding="utf-8")


def build_poster(
    frame: Path,
    destination: Path,
) -> None:
    shutil.copyfile(frame, destination)


def build_animation(
    magick: str,
    frames: list[Path],
    destination: Path,
) -> None:
    if len(frames) != 3:
        raise SystemExit(
            "Showcase animations require exactly three frames"
        )
    subprocess.run(
        [
            magick,
            "-delay",
            "100",
            str(frames[0]),
            "-delay",
            "100",
            str(frames[1]),
            "-delay",
            "200",
            str(frames[2]),
            "-loop",
            "0",
            "-layers",
            "Optimize",
            str(destination),
        ],
        check=True,
    )


def source_fingerprint() -> str:
    inputs = [
        ASSETS / "build.py",
        SOCIAL,
    ]
    for slug, _title in SHOWCASES:
        source_root = SHOWCASE_ROOT / slug
        inputs.extend(
            [
                source_root / "source.md",
                source_root / "formal.html",
                source_root / "rich.html",
            ]
        )

    digest = hashlib.sha256()
    for path in sorted(inputs):
        relative = path.relative_to(ROOT).as_posix()
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def png_metadata(path: Path) -> PngMetadata:
    data = path.read_bytes()
    signature = b"\x89PNG\r\n\x1a\n"
    if not data.startswith(signature):
        raise SystemExit(f"Not a PNG: {path}")

    offset = len(signature)
    chunk_index = 0
    width = 0
    height = 0
    color_type = -1
    bit_depth = -1
    seen_ihdr = False
    seen_plte = False
    seen_idat = False
    idat_finished = False
    palette_entries = 0
    idat_chunks: list[bytes] = []
    text_chunks: list[bytes] = []
    singleton_chunks = {
        b"cHRM",
        b"gAMA",
        b"iCCP",
        b"sBIT",
        b"sRGB",
        b"bKGD",
        b"hIST",
        b"pHYs",
        b"tRNS",
        b"tIME",
        b"eXIf",
    }
    chunks_seen: set[bytes] = set()
    suggested_palette_names: set[bytes] = set()
    before_palette_chunks = {
        b"cHRM",
        b"gAMA",
        b"iCCP",
        b"sBIT",
        b"sRGB",
    }
    before_image_chunks = {
        b"cHRM",
        b"gAMA",
        b"iCCP",
        b"sBIT",
        b"sRGB",
        b"bKGD",
        b"hIST",
        b"pHYs",
        b"tRNS",
        b"eXIf",
    }
    while offset < len(data):
        if offset + 12 > len(data):
            raise SystemExit(f"PNG has a truncated chunk: {path}")
        length = struct.unpack(">I", data[offset : offset + 4])[0]
        chunk_type = data[offset + 4 : offset + 8]
        chunk_end = offset + 12 + length
        if chunk_end > len(data):
            raise SystemExit(f"PNG chunk exceeds file bounds: {path}")
        if not all(
            65 <= value <= 90 or 97 <= value <= 122
            for value in chunk_type
        ):
            raise SystemExit(f"PNG has an invalid chunk type: {path}")
        if chunk_type[2] & 0x20:
            raise SystemExit(
                f"PNG chunk uses the reserved type bit: {path}"
            )

        chunk_data = data[offset + 8 : offset + 8 + length]
        recorded_crc = struct.unpack(
            ">I",
            data[offset + 8 + length : chunk_end],
        )[0]
        computed_crc = zlib.crc32(chunk_type + chunk_data)
        computed_crc &= 0xFFFFFFFF
        if recorded_crc != computed_crc:
            raise SystemExit(f"PNG chunk CRC mismatch: {path}")
        if chunk_type in singleton_chunks:
            if chunk_type in chunks_seen:
                raise SystemExit(
                    f"PNG repeats a singleton chunk: {path}"
                )
        if seen_plte and chunk_type in before_palette_chunks:
            raise SystemExit(
                f"PNG has a chunk after its required position: {path}"
            )
        if seen_idat and chunk_type in before_image_chunks:
            raise SystemExit(
                f"PNG has a chunk after image data: {path}"
            )
        chunks_seen.add(chunk_type)

        if chunk_index == 0 and chunk_type != b"IHDR":
            raise SystemExit(f"PNG does not start with IHDR: {path}")
        if chunk_type == b"IHDR":
            if seen_ihdr or chunk_index != 0 or length != 13:
                raise SystemExit(f"PNG has an invalid IHDR: {path}")
            seen_ihdr = True
            width, height = struct.unpack(">II", chunk_data[:8])
            bit_depth = chunk_data[8]
            color_type = chunk_data[9]
            compression = chunk_data[10]
            filter_method = chunk_data[11]
            interlace = chunk_data[12]
            valid_depths = {
                0: {1, 2, 4, 8, 16},
                2: {8, 16},
                3: {1, 2, 4, 8},
                4: {8, 16},
                6: {8, 16},
            }
            if width == 0 or height == 0:
                raise SystemExit(f"PNG has zero dimensions: {path}")
            if bit_depth not in valid_depths.get(color_type, set()):
                raise SystemExit(
                    f"PNG has an invalid color type or depth: {path}"
                )
            if compression != 0 or filter_method != 0:
                raise SystemExit(
                    f"PNG has an unsupported coding method: {path}"
                )
            if interlace not in (0, 1):
                raise SystemExit(
                    f"PNG has an invalid interlace method: {path}"
                )
        elif chunk_type == b"PLTE":
            if seen_plte or seen_idat:
                raise SystemExit(f"PNG has a misplaced PLTE: {path}")
            if b"bKGD" in chunks_seen or b"hIST" in chunks_seen:
                raise SystemExit(
                    f"PNG has PLTE after a palette-dependent chunk: {path}"
                )
            if color_type in (0, 4):
                raise SystemExit(f"PNG color type forbids PLTE: {path}")
            if length == 0 or length % 3 != 0 or length > 768:
                raise SystemExit(f"PNG has an invalid PLTE: {path}")
            if color_type == 3:
                if length // 3 > 2**bit_depth:
                    raise SystemExit(
                        f"PNG palette exceeds its bit depth: {path}"
                    )
            seen_plte = True
            palette_entries = length // 3
        elif chunk_type == b"IDAT":
            if idat_finished:
                raise SystemExit(
                    f"PNG has nonconsecutive IDAT chunks: {path}"
                )
            if color_type == 3 and not seen_plte:
                raise SystemExit(
                    f"Indexed PNG has no palette: {path}"
                )
            seen_idat = True
            idat_chunks.append(chunk_data)
        elif chunk_type == b"IEND":
            if length != 0:
                raise SystemExit(f"PNG has a nonempty IEND: {path}")
            if not seen_idat:
                raise SystemExit(f"PNG has no IDAT: {path}")
            if chunk_end != len(data):
                raise SystemExit(f"PNG has data after IEND: {path}")
            validate_png_image_data(
                path,
                b"".join(idat_chunks),
                width,
                height,
                bit_depth,
                color_type,
                interlace,
            )
            return PngMetadata(
                width=width,
                height=height,
                text_chunks=tuple(text_chunks),
            )
        else:
            if chunk_type[0] & 0x20 == 0:
                raise SystemExit(
                    f"PNG has an unknown critical chunk: {path}"
                )
            if chunk_type == b"tEXt":
                text_chunks.append(chunk_data)
            if chunk_type == b"tRNS":
                if color_type == 0 and length != 2:
                    raise SystemExit(
                        f"PNG has invalid grayscale transparency: {path}"
                    )
                if color_type == 2 and length != 6:
                    raise SystemExit(
                        f"PNG has invalid truecolor transparency: {path}"
                    )
                if color_type == 3:
                    if length == 0 or length > palette_entries:
                        raise SystemExit(
                            f"PNG has invalid palette transparency: {path}"
                        )
                if color_type not in (0, 2, 3):
                    raise SystemExit(
                        f"PNG color type forbids transparency: {path}"
                    )
                maximum = (1 << bit_depth) - 1
                if color_type == 0:
                    sample = struct.unpack(">H", chunk_data)[0]
                    if sample > maximum:
                        raise SystemExit(
                            f"PNG transparency sample is invalid: {path}"
                        )
                if color_type == 2:
                    samples = struct.unpack(">HHH", chunk_data)
                    if any(value > maximum for value in samples):
                        raise SystemExit(
                            f"PNG transparency sample is invalid: {path}"
                        )
            elif chunk_type == b"bKGD":
                if color_type == 3:
                    if not seen_plte or length != 1:
                        raise SystemExit(
                            f"Indexed PNG has invalid background: {path}"
                        )
                    if chunk_data[0] >= palette_entries:
                        raise SystemExit(
                            f"PNG background exceeds its palette: {path}"
                        )
                elif color_type in (0, 4):
                    if length != 2:
                        raise SystemExit(
                            f"Grayscale PNG has invalid background: {path}"
                        )
                    sample = struct.unpack(">H", chunk_data)[0]
                    if sample > (1 << bit_depth) - 1:
                        raise SystemExit(
                            f"PNG background sample is invalid: {path}"
                        )
                elif color_type in (2, 6):
                    if length != 6:
                        raise SystemExit(
                            f"Truecolor PNG has invalid background: {path}"
                        )
                    samples = struct.unpack(">HHH", chunk_data)
                    maximum = (1 << bit_depth) - 1
                    if any(value > maximum for value in samples):
                        raise SystemExit(
                            f"PNG background sample is invalid: {path}"
                        )
            elif chunk_type == b"hIST":
                if not seen_plte:
                    raise SystemExit(
                        f"PNG histogram has no palette: {path}"
                    )
                if length != palette_entries * 2:
                    raise SystemExit(
                        f"PNG histogram length is invalid: {path}"
                    )
            elif chunk_type == b"cHRM":
                if length != 32:
                    raise SystemExit(
                        f"PNG chromaticity length is invalid: {path}"
                    )
            elif chunk_type == b"gAMA":
                if length != 4 or chunk_data == b"\0\0\0\0":
                    raise SystemExit(f"PNG gamma is invalid: {path}")
            elif chunk_type == b"sRGB":
                if length != 1 or chunk_data[0] > 3:
                    raise SystemExit(
                        f"PNG rendering intent is invalid: {path}"
                    )
                if b"iCCP" in chunks_seen:
                    raise SystemExit(
                        f"PNG contains both sRGB and iCCP: {path}"
                    )
            elif chunk_type == b"iCCP":
                if b"sRGB" in chunks_seen:
                    raise SystemExit(
                        f"PNG contains both sRGB and iCCP: {path}"
                    )
                separator = png_keyword_end(
                    chunk_data,
                    path,
                    "profile",
                )
                if separator + 2 > length:
                    raise SystemExit(
                        f"PNG profile data is incomplete: {path}"
                    )
                if chunk_data[separator + 1] != 0:
                    raise SystemExit(
                        f"PNG profile compression is invalid: {path}"
                    )
                validate_png_zlib_payload(
                    chunk_data[separator + 2 :],
                    path,
                    "profile",
                )
            elif chunk_type == b"sBIT":
                significant_lengths = {
                    0: 1,
                    2: 3,
                    3: 3,
                    4: 2,
                    6: 4,
                }
                if length != significant_lengths[color_type]:
                    raise SystemExit(
                        f"PNG significant-bits length is invalid: {path}"
                    )
                maximum = bit_depth
                if color_type == 3:
                    maximum = 8
                if any(
                    value == 0 or value > maximum
                    for value in chunk_data
                ):
                    raise SystemExit(
                        f"PNG significant-bits value is invalid: {path}"
                    )
            elif chunk_type == b"pHYs":
                if length != 9 or chunk_data[8] not in (0, 1):
                    raise SystemExit(
                        f"PNG physical dimensions are invalid: {path}"
                    )
            elif chunk_type == b"tIME":
                if length != 7:
                    raise SystemExit(
                        f"PNG timestamp length is invalid: {path}"
                    )
                month = chunk_data[2]
                day = chunk_data[3]
                hour = chunk_data[4]
                minute = chunk_data[5]
                second = chunk_data[6]
                if month < 1 or month > 12:
                    raise SystemExit(f"PNG timestamp is invalid: {path}")
                if day < 1 or day > 31:
                    raise SystemExit(f"PNG timestamp is invalid: {path}")
                if hour > 23 or minute > 59 or second > 60:
                    raise SystemExit(f"PNG timestamp is invalid: {path}")
            elif chunk_type == b"tEXt":
                separator = png_keyword_end(
                    chunk_data,
                    path,
                    "text",
                )
                if b"\0" in chunk_data[separator + 1 :]:
                    raise SystemExit(
                        f"PNG text contains a null byte: {path}"
                    )
            elif chunk_type == b"zTXt":
                separator = png_keyword_end(
                    chunk_data,
                    path,
                    "compressed text",
                )
                if separator + 2 > length:
                    raise SystemExit(
                        f"PNG compressed text is incomplete: {path}"
                    )
                if chunk_data[separator + 1] != 0:
                    raise SystemExit(
                        f"PNG text compression is invalid: {path}"
                    )
                text_data = validate_png_zlib_payload(
                    chunk_data[separator + 2 :],
                    path,
                    "text",
                )
                if b"\0" in text_data:
                    raise SystemExit(
                        f"PNG compressed text contains a null byte: {path}"
                    )
            elif chunk_type == b"iTXt":
                separator = png_keyword_end(
                    chunk_data,
                    path,
                    "international text",
                )
                control_end = separator + 3
                if control_end > length:
                    raise SystemExit(
                        f"PNG international text is incomplete: {path}"
                    )
                compression_flag = chunk_data[separator + 1]
                compression_method = chunk_data[separator + 2]
                if compression_flag not in (0, 1):
                    raise SystemExit(
                        f"PNG international text flag is invalid: {path}"
                    )
                if compression_method != 0:
                    raise SystemExit(
                        f"PNG international text method is invalid: {path}"
                    )
                language_end = chunk_data.find(b"\0", control_end)
                if language_end == -1:
                    raise SystemExit(
                        f"PNG international language is incomplete: {path}"
                    )
                language = chunk_data[control_end:language_end]
                if language:
                    language_parts = language.split(b"-")
                    if any(not part for part in language_parts):
                        raise SystemExit(
                            f"PNG international language is invalid: {path}"
                        )
                    if any(
                        len(part) > 8
                        for part in language_parts
                    ):
                        raise SystemExit(
                            f"PNG international language is invalid: {path}"
                        )
                    primary = language_parts[0]
                    if any(
                        not (
                            65 <= value <= 90
                            or 97 <= value <= 122
                        )
                        for value in primary
                    ):
                        raise SystemExit(
                            f"PNG international language is invalid: {path}"
                        )
                    for part in language_parts[1:]:
                        if any(
                            not (
                                48 <= value <= 57
                                or 65 <= value <= 90
                                or 97 <= value <= 122
                            )
                            for value in part
                        ):
                            raise SystemExit(
                                f"PNG international language is invalid: {path}"
                            )
                translated_end = chunk_data.find(
                    b"\0",
                    language_end + 1,
                )
                if translated_end == -1:
                    raise SystemExit(
                        f"PNG translated keyword is incomplete: {path}"
                    )
                translated = chunk_data[
                    language_end + 1 : translated_end
                ]
                if b"\0" in translated:
                    raise SystemExit(
                        f"PNG translated keyword contains a null byte: {path}"
                    )
                try:
                    translated.decode("utf-8")
                except UnicodeDecodeError as error:
                    raise SystemExit(
                        f"PNG translated keyword is invalid: {path}"
                    ) from error
                text_data = chunk_data[translated_end + 1 :]
                if compression_flag == 1:
                    text_data = validate_png_zlib_payload(
                        text_data,
                        path,
                        "international text",
                    )
                if b"\0" in text_data:
                    raise SystemExit(
                        f"PNG international text contains a null byte: {path}"
                    )
                try:
                    text_data.decode("utf-8")
                except UnicodeDecodeError as error:
                    raise SystemExit(
                        f"PNG international text is invalid: {path}"
                    ) from error
            elif chunk_type == b"sPLT":
                separator = png_keyword_end(
                    chunk_data,
                    path,
                    "suggested palette",
                )
                palette_name = chunk_data[:separator]
                if palette_name in suggested_palette_names:
                    raise SystemExit(
                        f"PNG repeats a suggested palette name: {path}"
                    )
                suggested_palette_names.add(palette_name)
                if separator + 2 > length:
                    raise SystemExit(
                        f"PNG suggested palette is incomplete: {path}"
                    )
                sample_depth = chunk_data[separator + 1]
                if sample_depth == 8:
                    entry_size = 6
                elif sample_depth == 16:
                    entry_size = 10
                else:
                    raise SystemExit(
                        f"PNG suggested palette depth is invalid: {path}"
                    )
                entries = chunk_data[separator + 2 :]
                if not entries or len(entries) % entry_size != 0:
                    raise SystemExit(
                        f"PNG suggested palette length is invalid: {path}"
                    )
            elif chunk_type == b"eXIf":
                if length < 8:
                    raise SystemExit(
                        f"PNG Exif profile is incomplete: {path}"
                    )
                byte_order = chunk_data[:4]
                if byte_order not in (b"II\x2a\0", b"MM\0\x2a"):
                    raise SystemExit(
                        f"PNG Exif profile is invalid: {path}"
                    )

        if seen_idat and chunk_type != b"IDAT":
            idat_finished = True
        offset = chunk_end
        chunk_index += 1

    raise SystemExit(f"PNG has no IEND: {path}")


def png_pass_size(
    size: int,
    start: int,
    step: int,
) -> int:
    if size <= start:
        return 0
    return (size - start + step - 1) // step


def validate_png_image_data(
    path: Path,
    compressed: bytes,
    width: int,
    height: int,
    bit_depth: int,
    color_type: int,
    interlace: int,
) -> None:
    samples_by_color_type = {
        0: 1,
        2: 3,
        3: 1,
        4: 2,
        6: 4,
    }
    samples = samples_by_color_type[color_type]
    bits_per_pixel = samples * bit_depth
    passes = ((0, 0, 1, 1),)
    if interlace == 1:
        passes = (
            (0, 0, 8, 8),
            (4, 0, 8, 8),
            (0, 4, 4, 8),
            (2, 0, 4, 4),
            (0, 2, 2, 4),
            (1, 0, 2, 2),
            (0, 1, 1, 2),
        )

    rows: list[tuple[int, int]] = []
    expected_size = 0
    for start_x, start_y, step_x, step_y in passes:
        pass_width = png_pass_size(width, start_x, step_x)
        pass_height = png_pass_size(height, start_y, step_y)
        if pass_width == 0 or pass_height == 0:
            continue
        row_bytes = (pass_width * bits_per_pixel + 7) // 8
        rows.append((pass_height, row_bytes))
        expected_size += pass_height * (row_bytes + 1)

    decompressor = zlib.decompressobj()
    try:
        decoded = decompressor.decompress(compressed)
        decoded += decompressor.flush()
    except zlib.error as error:
        raise SystemExit(
            f"PNG has invalid compressed image data: {path}"
        ) from error
    if not decompressor.eof:
        raise SystemExit(
            f"PNG image data ends before its zlib stream: {path}"
        )
    if decompressor.unused_data or decompressor.unconsumed_tail:
        raise SystemExit(
            f"PNG image data has trailing compressed bytes: {path}"
        )
    if len(decoded) != expected_size:
        raise SystemExit(f"PNG scanline byte count is invalid: {path}")

    offset = 0
    for row_count, row_bytes in rows:
        for _row in range(row_count):
            if decoded[offset] > 4:
                raise SystemExit(f"PNG scanline filter is invalid: {path}")
            offset += row_bytes + 1


def gif_sub_blocks(
    data: bytes,
    offset: int,
    path: Path,
    label: str,
) -> tuple[bytes, int]:
    blocks: list[bytes] = []
    while True:
        if offset >= len(data):
            raise SystemExit(
                f"GIF has a truncated {label} extension: {path}"
            )
        length = data[offset]
        offset += 1
        if length == 0:
            return b"".join(blocks), offset
        block_end = offset + length
        if block_end > len(data):
            raise SystemExit(
                f"GIF {label} block exceeds file bounds: {path}"
            )
        blocks.append(data[offset:block_end])
        offset = block_end


def gif_lzw_indices(
    data: bytes,
    minimum_code_size: int,
    expected_pixels: int,
    path: Path,
) -> bytes:
    clear_code = 1 << minimum_code_size
    end_code = clear_code + 1
    code_size = minimum_code_size + 1
    next_code = end_code + 1
    table = {
        value: bytes([value])
        for value in range(clear_code)
    }
    bit_offset = 0
    previous: bytes | None = None
    decoded = bytearray()
    saw_clear = False
    saw_end = False

    while bit_offset + code_size <= len(data) * 8:
        code = 0
        for bit_index in range(code_size):
            absolute_bit = bit_offset + bit_index
            byte = data[absolute_bit // 8]
            if byte & (1 << (absolute_bit % 8)):
                code |= 1 << bit_index
        bit_offset += code_size

        if code == clear_code:
            table = {
                value: bytes([value])
                for value in range(clear_code)
            }
            code_size = minimum_code_size + 1
            next_code = end_code + 1
            previous = None
            saw_clear = True
            continue
        if code == end_code:
            saw_end = True
            break
        if not saw_clear:
            raise SystemExit(f"GIF image data has no clear code: {path}")

        entry = table.get(code)
        if entry is None:
            if previous is None or code != next_code:
                raise SystemExit(
                    f"GIF image data has an invalid LZW code: {path}"
                )
            entry = previous + previous[:1]
        decoded.extend(entry)
        if len(decoded) > expected_pixels:
            raise SystemExit(
                f"GIF image data exceeds its frame size: {path}"
            )

        if previous is not None and next_code < 4096:
            table[next_code] = previous + entry[:1]
            next_code += 1
            if next_code == 1 << code_size and code_size < 12:
                code_size += 1
        previous = entry

    if not saw_end:
        raise SystemExit(f"GIF image data has no end code: {path}")
    if len(decoded) != expected_pixels:
        raise SystemExit(f"GIF image data does not fill its frame: {path}")
    remaining_bits = len(data) * 8 - bit_offset
    if remaining_bits >= 8:
        raise SystemExit(f"GIF image data follows its end code: {path}")
    for absolute_bit in range(bit_offset, len(data) * 8):
        byte = data[absolute_bit // 8]
        if byte & (1 << (absolute_bit % 8)):
            raise SystemExit(
                f"GIF image data has nonzero padding: {path}"
            )
    return bytes(decoded)


def gif_metadata(path: Path) -> GifMetadata:
    data = path.read_bytes()
    version = data[:6]
    if version not in (b"GIF87a", b"GIF89a"):
        raise SystemExit(f"Not a GIF: {path}")
    if len(data) < 14:
        raise SystemExit(f"GIF has a truncated screen descriptor: {path}")

    width, height = struct.unpack("<HH", data[6:10])
    if width == 0 or height == 0:
        raise SystemExit(f"GIF has zero dimensions: {path}")
    packed = data[10]
    background_index = data[11]
    offset = 13
    global_color_entries = 0
    if packed & 0x80:
        global_color_entries = 2 ** ((packed & 0x07) + 1)
        table_end = offset + 3 * global_color_entries
        if table_end > len(data):
            raise SystemExit(
                f"GIF has a truncated global color table: {path}"
            )
        offset = table_end
        if background_index >= global_color_entries:
            raise SystemExit(
                f"GIF background index exceeds its color table: {path}"
            )

    frame_count = 0
    delays: list[int] = []
    comments: list[bytes] = []
    comment_spans: list[tuple[int, int]] = []
    pending_delay: int | None = None
    pending_transparent_index: int | None = None
    loops_forever = False
    loop_count: int | None = None
    while offset < len(data):
        block_start = offset
        introducer = data[offset]
        offset += 1
        if introducer == 0x3B:
            trailer_offset = offset - 1
            if offset != len(data):
                raise SystemExit(f"GIF has data after trailer: {path}")
            if frame_count == 0:
                raise SystemExit(f"GIF has no image frames: {path}")
            if pending_delay is not None:
                raise SystemExit(
                    f"GIF has a control extension without a frame: {path}"
                )
            return GifMetadata(
                width=width,
                height=height,
                frame_count=frame_count,
                delays=tuple(delays),
                loops_forever=loops_forever,
                comments=tuple(comments),
                comment_spans=tuple(comment_spans),
                trailer_offset=trailer_offset,
            )

        if introducer == 0x2C:
            descriptor_end = offset + 9
            if descriptor_end > len(data):
                raise SystemExit(
                    f"GIF has a truncated image descriptor: {path}"
                )
            left, top, frame_width, frame_height = struct.unpack(
                "<HHHH",
                data[offset : offset + 8],
            )
            descriptor_packed = data[offset + 8]
            offset = descriptor_end
            if descriptor_packed & 0x18:
                raise SystemExit(
                    f"GIF image descriptor uses reserved bits: {path}"
                )
            if frame_width == 0 or frame_height == 0:
                raise SystemExit(
                    f"GIF has a zero-size image frame: {path}"
                )
            if left + frame_width > width:
                raise SystemExit(
                    f"GIF image frame exceeds screen width: {path}"
                )
            if top + frame_height > height:
                raise SystemExit(
                    f"GIF image frame exceeds screen height: {path}"
                )
            active_color_entries = global_color_entries
            if descriptor_packed & 0x80:
                active_color_entries = 2 ** (
                    (descriptor_packed & 0x07) + 1
                )
                table_end = offset + 3 * active_color_entries
                if table_end > len(data):
                    raise SystemExit(
                        f"GIF has a truncated local color table: {path}"
                    )
                offset = table_end
            if active_color_entries == 0:
                raise SystemExit(
                    f"GIF image frame has no active color table: {path}"
                )
            if pending_transparent_index is not None:
                if pending_transparent_index >= active_color_entries:
                    raise SystemExit(
                        f"GIF transparent index exceeds its color table: {path}"
                    )
            if offset >= len(data):
                raise SystemExit(
                    f"GIF image frame has no LZW code size: {path}"
                )
            lzw_code_size = data[offset]
            offset += 1
            if lzw_code_size < 2 or lzw_code_size > 8:
                raise SystemExit(
                    f"GIF image frame has invalid LZW code size: {path}"
                )
            image_data, offset = gif_sub_blocks(
                data,
                offset,
                path,
                "image data",
            )
            if not image_data:
                raise SystemExit(
                    f"GIF image frame has no image data: {path}"
                )
            indices = gif_lzw_indices(
                image_data,
                lzw_code_size,
                frame_width * frame_height,
                path,
            )
            if any(
                value >= active_color_entries
                for value in indices
            ):
                raise SystemExit(
                    f"GIF image index exceeds its color table: {path}"
                )
            frame_count += 1
            if pending_delay is None:
                delays.append(0)
            else:
                delays.append(pending_delay)
            pending_delay = None
            pending_transparent_index = None
            continue

        if introducer != 0x21:
            raise SystemExit(
                f"GIF has an unknown block introducer: {path}"
            )
        if offset >= len(data):
            raise SystemExit(
                f"GIF has a truncated extension label: {path}"
            )
        extension_label = data[offset]
        offset += 1
        if extension_label == 0xF9:
            if version != b"GIF89a":
                raise SystemExit(
                    f"GIF87a contains a GIF89a extension: {path}"
                )
            if pending_delay is not None:
                raise SystemExit(
                    f"GIF has consecutive control extensions: {path}"
                )
            if offset >= len(data) or data[offset] != 4:
                raise SystemExit(
                    f"GIF has an invalid control extension: {path}"
                )
            extension_end = offset + 6
            if extension_end > len(data):
                raise SystemExit(
                    f"GIF has a truncated control extension: {path}"
                )
            if data[extension_end - 1] != 0:
                raise SystemExit(
                    f"GIF control extension has no terminator: {path}"
                )
            control_packed = data[offset + 1]
            if control_packed & 0xE0:
                raise SystemExit(
                    f"GIF control extension uses reserved bits: {path}"
                )
            disposal_method = (control_packed >> 2) & 0x07
            if disposal_method > 3:
                raise SystemExit(
                    f"GIF control extension has invalid disposal: {path}"
                )
            pending_delay = struct.unpack(
                "<H",
                data[offset + 2 : offset + 4],
            )[0]
            if control_packed & 0x01:
                pending_transparent_index = data[offset + 4]
            else:
                pending_transparent_index = None
            offset = extension_end
            continue

        if extension_label == 0xFF:
            if version != b"GIF89a":
                raise SystemExit(
                    f"GIF87a contains a GIF89a extension: {path}"
                )
            if offset >= len(data) or data[offset] != 11:
                raise SystemExit(
                    f"GIF has an invalid application extension: {path}"
                )
            identifier_end = offset + 12
            if identifier_end > len(data):
                raise SystemExit(
                    f"GIF has a truncated application extension: {path}"
                )
            identifier = data[offset + 1 : identifier_end]
            application_identifier = identifier[:8]
            if any(
                value < 0x20 or value > 0x7E
                for value in application_identifier
            ):
                raise SystemExit(
                    f"GIF application identifier is invalid: {path}"
                )
            payload, offset = gif_sub_blocks(
                data,
                identifier_end,
                path,
                "application",
            )
            if identifier == b"NETSCAPE2.0":
                if loop_count is not None:
                    raise SystemExit(
                        f"GIF repeats its loop extension: {path}"
                    )
                if len(payload) != 3 or payload[0] != 1:
                    raise SystemExit(
                        f"GIF has invalid loop metadata: {path}"
                    )
                loop_count = struct.unpack("<H", payload[1:3])[0]
                if loop_count == 0:
                    loops_forever = True
            continue

        if extension_label == 0xFE:
            if version != b"GIF89a":
                raise SystemExit(
                    f"GIF87a contains a GIF89a extension: {path}"
                )
            comment, offset = gif_sub_blocks(
                data,
                offset,
                path,
                "comment",
            )
            comments.append(comment)
            comment_spans.append((block_start, offset))
            continue

        if extension_label == 0x01:
            if version != b"GIF89a":
                raise SystemExit(
                    f"GIF87a contains a GIF89a extension: {path}"
                )
            if offset >= len(data) or data[offset] != 12:
                raise SystemExit(
                    f"GIF has an invalid plain-text extension: {path}"
                )
            header_end = offset + 13
            if header_end > len(data):
                raise SystemExit(
                    f"GIF has a truncated plain-text extension: {path}"
                )
            if global_color_entries == 0:
                raise SystemExit(
                    f"GIF plain text has no global color table: {path}"
                )
            text_header = data[offset + 1 : header_end]
            (
                text_left,
                text_top,
                text_width,
                text_height,
            ) = struct.unpack("<HHHH", text_header[:8])
            cell_width = text_header[8]
            cell_height = text_header[9]
            foreground_index = text_header[10]
            background_index = text_header[11]
            if text_width == 0 or text_height == 0:
                raise SystemExit(
                    f"GIF plain-text grid has zero dimensions: {path}"
                )
            if text_left + text_width > width:
                raise SystemExit(
                    f"GIF plain-text grid exceeds screen width: {path}"
                )
            if text_top + text_height > height:
                raise SystemExit(
                    f"GIF plain-text grid exceeds screen height: {path}"
                )
            if cell_width == 0 or cell_height == 0:
                raise SystemExit(
                    f"GIF plain-text cell has zero dimensions: {path}"
                )
            if foreground_index >= global_color_entries:
                raise SystemExit(
                    f"GIF plain-text foreground index is invalid: {path}"
                )
            if background_index >= global_color_entries:
                raise SystemExit(
                    f"GIF plain-text background index is invalid: {path}"
                )
            if pending_transparent_index is not None:
                if pending_transparent_index >= global_color_entries:
                    raise SystemExit(
                        f"GIF transparent index exceeds its color table: {path}"
                    )
            text, offset = gif_sub_blocks(
                data,
                header_end,
                path,
                "plain text",
            )
            if any(value < 0x20 or value > 0x7E for value in text):
                raise SystemExit(
                    f"GIF plain text contains a nonprintable byte: {path}"
                )
            pending_delay = None
            pending_transparent_index = None
            continue

        _extension, offset = gif_sub_blocks(
            data,
            offset,
            path,
            "unknown",
        )

    raise SystemExit(f"GIF has no trailer: {path}")


def stamp_png(path: Path, fingerprint: str) -> None:
    data = path.read_bytes()
    png_metadata(path)

    chunk_type = b"tEXt"
    chunk_data = STAMP_KEY + b"\0" + fingerprint.encode("ascii")
    checksum = zlib.crc32(chunk_type + chunk_data)
    chunk = (
        struct.pack(">I", len(chunk_data))
        + chunk_type
        + chunk_data
        + struct.pack(">I", checksum)
    )
    signature = data[:8]
    stamped = bytearray(signature)
    offset = len(signature)
    while offset < len(data):
        length = struct.unpack(">I", data[offset : offset + 4])[0]
        chunk_end = offset + 12 + length
        existing_type = data[offset + 4 : offset + 8]
        existing_data = data[offset + 8 : offset + 8 + length]
        is_old_stamp = (
            existing_type == b"tEXt"
            and existing_data.startswith(STAMP_KEY + b"\0")
        )
        if not is_old_stamp:
            stamped.extend(data[offset:chunk_end])
        if existing_type == b"IHDR":
            stamped.extend(chunk)
        offset = chunk_end
    path.write_bytes(bytes(stamped))
    png_metadata(path)


def stamp_gif(path: Path, fingerprint: str) -> None:
    data = path.read_bytes()
    metadata = gif_metadata(path)

    comment = STAMP_KEY + b"=" + fingerprint.encode("ascii")
    extension = b"\x21\xfe"
    for offset in range(0, len(comment), 255):
        block = comment[offset : offset + 255]
        extension += bytes([len(block)]) + block
    extension += b"\x00"
    unstamped = bytearray()
    cursor = 0
    for existing, span in zip(
        metadata.comments,
        metadata.comment_spans,
    ):
        start, end = span
        if existing.startswith(STAMP_KEY + b"="):
            unstamped.extend(data[cursor:start])
            cursor = end
    unstamped.extend(data[cursor:])
    trailer = len(unstamped) - 1
    unstamped[trailer:trailer] = extension
    path.write_bytes(bytes(unstamped))
    gif_metadata(path)


def stamp_assets(output_root: Path) -> None:
    fingerprint = source_fingerprint()
    for name in generated_asset_names():
        path = output_root / name
        if path.suffix == ".png":
            stamp_png(path, fingerprint)
        else:
            stamp_gif(path, fingerprint)


def validate_source_stamp(
    path: Path,
    expected_fingerprint: str,
) -> None:
    marker = STAMP_KEY + b"=" + expected_fingerprint.encode(
        "ascii"
    )
    png_marker = STAMP_KEY + b"\0" + expected_fingerprint.encode(
        "ascii"
    )
    found = False
    if path.suffix == ".png":
        found = png_marker in png_metadata(path).text_chunks
    elif path.suffix == ".gif":
        found = marker in gif_metadata(path).comments
    else:
        raise SystemExit(f"Unsupported asset format: {path}")
    if not found:
        raise SystemExit(
            f"Asset source fingerprint is stale: {path}"
        )


def build_showcase(
    chrome: str,
    magick: str,
    work: Path,
    output_root: Path,
    slug: str,
    title: str,
) -> None:
    source_root = SHOWCASE_ROOT / slug
    temporary_root = work / slug
    temporary_root.mkdir()

    source_view = temporary_root / "source.html"
    formal_view = temporary_root / "formal.html"
    rich_view = temporary_root / "rich.html"
    write_source_view(
        source_root / "source.md",
        source_view,
        title,
    )
    write_labeled_view(
        source_root / "formal.html",
        formal_view,
        "02 · Formal HTML",
        "formal.html",
    )
    write_labeled_view(
        source_root / "rich.html",
        rich_view,
        "03 · Rich HTML",
        "rich.html",
    )

    frames = []
    for name, view in (
        ("source", source_view),
        ("formal", formal_view),
        ("rich", rich_view),
    ):
        capture_path = temporary_root / f"{name}-capture.png"
        frame_path = temporary_root / f"{name}-frame.png"
        capture(chrome, view, capture_path, 1280, 720)
        crop_frame(magick, capture_path, frame_path)
        frames.append(frame_path)

    build_poster(
        frames[-1],
        output_root / f"{slug}-poster.png",
    )
    build_animation(
        magick,
        frames,
        output_root / f"{slug}.gif",
    )


def png_dimensions(path: Path) -> tuple[int, int]:
    metadata = png_metadata(path)
    return metadata.width, metadata.height


def gif_dimensions(path: Path) -> tuple[int, int]:
    metadata = gif_metadata(path)
    return metadata.width, metadata.height


def gif_delays(path: Path) -> list[int]:
    return list(gif_metadata(path).delays)


def gif_loops_forever(path: Path) -> bool:
    return gif_metadata(path).loops_forever


def validate_assets(output_root: Path) -> None:
    expected_fingerprint = source_fingerprint()
    social = output_root / "social-preview.png"
    if png_dimensions(social) != (1280, 640):
        raise SystemExit(
            f"Unexpected social preview dimensions: {social}"
        )
    validate_source_stamp(social, expected_fingerprint)
    for slug, _title in SHOWCASES:
        poster = output_root / f"{slug}-poster.png"
        animation = output_root / f"{slug}.gif"
        if png_dimensions(poster) != (1280, 720):
            raise SystemExit(
                f"Unexpected poster dimensions: {poster}"
            )
        if gif_dimensions(animation) != (1280, 720):
            raise SystemExit(
                f"Unexpected animation dimensions: {animation}"
            )
        if gif_metadata(animation).frame_count != 3:
            raise SystemExit(
                f"Unexpected animation frame count: {animation}"
            )
        if gif_delays(animation) != [100, 100, 200]:
            raise SystemExit(
                f"Unexpected animation timing: {animation}"
            )
        if not gif_loops_forever(animation):
            raise SystemExit(
                f"Animation does not loop forever: {animation}"
            )
        validate_source_stamp(poster, expected_fingerprint)
        validate_source_stamp(animation, expected_fingerprint)


def generated_asset_names() -> list[str]:
    names = ["social-preview.png"]
    for slug, _title in SHOWCASES:
        names.append(f"{slug}-poster.png")
        names.append(f"{slug}.gif")
    return names


def build(output_root: Path = ASSETS) -> None:
    magick = find_imagemagick()
    chrome = find_chrome()
    output_root.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(
        prefix="htmlify-assets-"
    ) as temporary:
        work = Path(temporary)
        social_capture = work / "social.png"
        capture(
            chrome,
            SOCIAL,
            social_capture,
            1280,
            640,
        )
        subprocess.run(
            [
                magick,
                str(social_capture),
                "-strip",
                str(output_root / "social-preview.png"),
            ],
            check=True,
        )

        for slug, title in SHOWCASES:
            build_showcase(
                chrome,
                magick,
                work,
                output_root,
                slug,
                title,
            )
        stamp_assets(output_root)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ASSETS,
    )
    parser.add_argument(
        "--check",
        action="store_true",
    )
    return parser.parse_args()


if __name__ == "__main__":
    arguments = parse_args()
    if arguments.check:
        validate_assets(ASSETS)
    else:
        build(arguments.output_dir)
