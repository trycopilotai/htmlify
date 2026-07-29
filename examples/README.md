# Release evidence

The committed examples exercise both `htmlify` modes with
synthetic source material.

| Mode    | Source contract                 | Retained output            |
| ------- | ------------------------------- | -------------------------- |
| Curated | Interpret facts into a decision | Self-contained HTML        |
| Formal  | Preserve order for print        | Deterministic HTML and PDF |

Each example has a machine-readable manifest containing the
source commit, skill hash, generator and version,
invocation, date, output hashes, and post-run edit state.

- [Curated example](curated/README.md)
- [Formal example](formal/README.md)

Run the evidence checks with:

```sh
python3 tests/test_evidence.gpt.py
```

The PDF run exercised Chrome on macOS and produced one US
Letter page. It does not establish behavior for WeasyPrint,
Chromium, Microsoft Edge, wkhtmltopdf, Windows, or Linux.

The curated run used OpenAI Codex CLI 0.146.0 and was
visually checked at 1440 by 900 pixels. Its output is one
model run, not a promise that every agent or model will make
the same design choices.
