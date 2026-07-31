# Examples

## Showcase transformations

Each showcase retains one synthetic Markdown source and two
renderings. The formal version preserves source order; the
rich version reorganizes the same facts around the
document's useful visual structure.

| Shape                | Source                                              | Formal                                            | Rich                                            |
| -------------------- | --------------------------------------------------- | ------------------------------------------------- | ----------------------------------------------- |
| Publication timeline | [Markdown](showcase/publication-sprint/source.md)   | [HTML](showcase/publication-sprint/formal.html)   | [HTML](showcase/publication-sprint/rich.html)   |
| System control path  | [Markdown](showcase/control-plane-status/source.md) | [HTML](showcase/control-plane-status/formal.html) | [HTML](showcase/control-plane-status/rich.html) |
| Design progression   | [Markdown](showcase/design-evolution/source.md)     | [HTML](showcase/design-evolution/formal.html)     | [HTML](showcase/design-evolution/rich.html)     |

Each rich showcase also retains the exact agent version,
invocation, input commit, skill hash, output hashes, edit
state, release visual QA, and repository-relative run
record:

- [Publication sprint manifest](showcase/publication-sprint/manifest.json)
  and [final run record](showcase/publication-sprint/run.md)
- [Control-plane manifest](showcase/control-plane-status/manifest.json)
  and
  [final run record](showcase/control-plane-status/run.md)
- [Design-evolution manifest](showcase/design-evolution/manifest.json)
  and [final run record](showcase/design-evolution/run.md)

The README animations are generated from these files in
source → formal → rich order:

```sh
make assets
```

## Release evidence

The release-evidence examples exercise both `htmlify` modes
with synthetic source material.

| Mode    | Source contract                 | Retained output                  |
| ------- | ------------------------------- | -------------------------------- |
| Curated | Interpret facts into a decision | Self-contained HTML              |
| Formal  | Preserve order for print        | Deterministic HTML; optional PDF |

Each release-evidence example has a machine-readable
manifest containing the source commit, skill hash, generator
and version, invocation, date, output hashes, and post-run
edit state.

- [Curated example](curated/README.md)
- [Formal example](formal/README.md)

Run the evidence checks with:

```sh
python3 tests/test_evidence.py
```

The PDF run exercised Chrome on macOS and produced one US
Letter page. It does not establish behavior for WeasyPrint,
Chromium, Microsoft Edge, wkhtmltopdf, Windows, or Linux.

The curated run used OpenAI Codex CLI 0.146.0 and was
visually checked at 1440 by 900 pixels, then checked for
document-level overflow at 390 by 844 pixels. Its output is
one model run, not a promise that every agent or model will
make the same design choices.

The [contrast audit](contrast-audit.json) records the
foreground/background pairs that the test suite holds to a
4.5:1 minimum.
