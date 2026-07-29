# Security

## Supported releases

Security fixes apply to the latest tagged release.

## Reporting a vulnerability

Use GitHub private vulnerability reporting for this
repository. Do not open a public issue for a credential,
private-data disclosure, unsafe link, command-execution
path, or local-file exposure.

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

Every release is scanned before its first remote push.
Release checks cover tracked paths, contents, commit
messages, identities, branches, and tags. The supported tag
must point into the reviewed history.
