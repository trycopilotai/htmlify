# Curated decision surface

This example turns a fictional release-readiness review into
a single decision surface.

- [Source Markdown](release-readiness.gpt.md)
- [Rendered HTML](index.html)
- [Run transcript](run.gpt.md)
- [Evidence manifest](manifest.gpt.json)

The page places the source's hold decision, four required
gates, and milestone sequence in the first viewport.
Supporting workstreams remain visually separate from the
required-gate rule.

The retained transcript names only repository-relative
paths. The HTML is self-contained and has no external
scripts, styles, images, or links.

The output was visually checked at 1440 by 900 pixels and
through Chrome's print layout. Responsive behavior was
implemented at 900 and 600 pixel breakpoints but was not
visually tested on a physical mobile device.
