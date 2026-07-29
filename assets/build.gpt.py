#!/usr/bin/env python3

import shutil
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
CURATED = ROOT / "examples" / "curated" / "index.html"
FORMAL = (
    ROOT / "examples" / "formal" / "delivery-brief.html"
)
SOCIAL = ASSETS / "social-preview.gpt.html"


def require_program(name: str) -> str:
    path = shutil.which(name)
    if path is None:
        raise SystemExit(f"Required program not found: {name}")
    return path


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
    subprocess.run(
        [
            chrome,
            "--headless=new",
            "--disable-gpu",
            "--hide-scrollbars",
            "--no-sandbox",
            f"--window-size={width},{height}",
            f"--screenshot={destination}",
            "--dump-dom",
            source.resolve().as_uri(),
        ],
        check=True,
        capture_output=True,
        timeout=30,
    )
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


def build() -> None:
    magick = require_program("magick")
    chrome = find_chrome()

    with tempfile.TemporaryDirectory(
        prefix="htmlify-assets-"
    ) as temporary:
        work = Path(temporary)
        curated_capture = work / "curated.png"
        formal_capture = work / "formal.png"
        social_capture = work / "social.png"
        curated_frame = work / "curated-frame.png"
        formal_frame = work / "formal-frame.png"

        capture(
            chrome,
            CURATED,
            curated_capture,
            1280,
            720,
        )
        capture(
            chrome,
            FORMAL,
            formal_capture,
            1280,
            720,
        )
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
                str(ASSETS / "social-preview.png"),
            ],
            check=True,
        )

        crop_frame(
            magick,
            curated_capture,
            curated_frame,
        )
        crop_frame(
            magick,
            formal_capture,
            formal_frame,
        )

        shutil.copyfile(
            curated_frame,
            ASSETS / "demo-poster.png",
        )
        subprocess.run(
            [
                magick,
                "-delay",
                "220",
                str(curated_frame),
                "-delay",
                "220",
                str(formal_frame),
                "-loop",
                "0",
                "-layers",
                "Optimize",
                str(ASSETS / "demo.gif"),
            ],
            check=True,
        )


if __name__ == "__main__":
    build()
