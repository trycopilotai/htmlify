# Curated decision surface

This example turns a fictional release-readiness review into
a single decision surface.

- [Source Markdown](release-readiness.gpt.md)
- [Rendered HTML](index.html)
- [Final run record](run.gpt.md)
- [Evidence manifest](manifest.gpt.json)

The page places the source's hold decision, four required
gates, and milestone sequence in the first viewport.
Supporting workstreams remain visually separate from the
required-gate rule.

The retained run record names only repository-relative
paths. The HTML is self-contained and has no external
scripts, styles, images, or links.

The output was visually checked at 1440 by 900 pixels and
checked for document-level overflow at an emulated 390 by
844 pixel viewport. The wide gate table scrolls inside its
panel at that width. Responsive behavior was not visually
tested on a physical mobile device.
