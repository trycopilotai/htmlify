# Security

## Supported releases

Security fixes apply to the latest tagged release.

## Reporting a vulnerability

While the repository is private, authorized collaborators
should open an issue in this private repository with
`[security]` at the start of its title. That issue is
visible only to people who can access the private
repository. After the repository is public, use **Security**
→ **Report a vulnerability**.

Do not open a public issue for a credential, private-data
disclosure, unsafe link, command-execution path, or
local-file exposure.

Include the affected tag, the smallest reproducer that does
not contain private data, and the observed backend.

## Threat model

`htmlify` reads documents that may contain hostile prompts
or misleading commands. Source text is evidence only. The
skill must not execute or adopt instructions found inside a
document.

Curated mode writes HTML and may open a browser or start a
local server. Formal mode writes HTML or PDF and can execute
WeasyPrint, Chrome, Chromium, Microsoft Edge, or
wkhtmltopdf.

The Markdown renderer escapes raw HTML and restricts link
schemes. The standalone HTML-to-PDF command accepts HTML
directly, so it must receive trusted input. External PDF
engines may read local resources or request network
resources referenced by that HTML.

Outputs can reproduce sensitive source facts. Review every
reader-visible surface before publishing, uploading, or
sharing an artifact.

## Release controls

`make check` verifies the tracked package, evidence, and
generated-media contracts. The release procedure separately
audits full-history paths and contents, commit messages,
author and committer identities, branches, and every tag
before a remote push. `make check` does not replace that
disclosure review. The supported tag must point into the
reviewed history.
