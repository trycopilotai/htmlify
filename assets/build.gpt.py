#!/usr/bin/env python3

import html
import shutil
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
SHOWCASE_ROOT = ROOT / "examples" / "showcase"
SOCIAL = ASSETS / "social-preview.gpt.html"
SHOWCASES = (
    ("publication-sprint", "Publication sprint"),
    ("control-plane-status", "Control plane status"),
    ("design-evolution", "Design evolution"),
)


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
        color: #667287;
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
        <span> · source.gpt.md</span>
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


def build_showcase(
    chrome: str,
    magick: str,
    work: Path,
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
        source_root / "source.gpt.md",
        source_view,
        title,
    )
    write_labeled_view(
        source_root / "formal.gpt.html",
        formal_view,
        "02 · Formal HTML",
        "formal.gpt.html",
    )
    write_labeled_view(
        source_root / "rich.gpt.html",
        rich_view,
        "03 · Rich HTML",
        "rich.gpt.html",
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
        ASSETS / f"{slug}-poster.gpt.png",
    )
    build_animation(
        magick,
        frames,
        ASSETS / f"{slug}.gpt.gif",
    )


def build() -> None:
    magick = require_program("magick")
    chrome = find_chrome()

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
                str(ASSETS / "social-preview.png"),
            ],
            check=True,
        )

        for slug, title in SHOWCASES:
            build_showcase(
                chrome,
                magick,
                work,
                slug,
                title,
            )


if __name__ == "__main__":
    build()
