# Formal HTML and PDF

This example passes a fictional delivery brief through the
bundled formal renderer.

- [Source Markdown](delivery-brief.md)
- [Rendered HTML](delivery-brief.html)
- [Rendered PDF](delivery-brief.pdf)
- [Evidence manifest](manifest.json)

The live run selected Google Chrome 150.0.7871.187 and
produced a non-empty, single-page US Letter PDF. The page
was rasterized with Poppler at 1275 by 1650 pixels and
visually inspected for clipping, overlap, spacing, table
alignment, and unreadable glyphs.

The run did not exercise WeasyPrint, Chromium, Microsoft
Edge, or wkhtmltopdf. The PDF bytes include backend metadata
and a generation timestamp, so byte-for-byte reproduction
requires the same renderer environment and run time.
