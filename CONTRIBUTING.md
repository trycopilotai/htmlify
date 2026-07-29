# Contributing

Contributions should make a documented behavior more
truthful, portable, or useful.

## Before changing code

Open or choose an issue and identify its mode:

- `curated-mode` for source extraction and visual decision
  surfaces;
- `formal-mode` for Markdown, HTML, or PDF rendering.

Issues labelled `good first issue` are scoped to one
documented behavior and include a verification target.

Do not put private documents, local paths, credentials,
customer names, or unpublished repository names into an
issue, fixture, commit message, or example.

## Development

The offline suite needs Python 3.11 or later:

```sh
make check
```

Add a focused test for every behavior change. A renderer
change also needs a golden output change when it affects
reader-visible HTML.

Tests must not fetch network resources. PDF backend
integration is a release check and must state the backend it
exercised.

## Pull requests

Keep one concern per commit. Put interface and intent before
tests, implementation, and generated evidence.

Describe:

- the behavior that changed;
- the command that verifies it;
- the backend or operating-system surface not tested;
- any generated artifact and its derivation command.

Do not add an automated-agent co-author trailer.

By contributing, you agree that your contribution is
licensed under the MIT License.
