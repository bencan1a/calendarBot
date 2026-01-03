# Bundled Fonts

## DejaVu Sans

This directory contains DejaVu Sans fonts bundled with CalendarBot Framebuffer UI
to ensure consistent rendering across different systems.

**Fonts:**
- `DejaVuSans.ttf` - Regular weight
- `DejaVuSans-Bold.ttf` - Bold weight

**License:** [Bitstream Vera and Arev fonts license](https://dejavu-fonts.github.io/License.html)

DejaVu fonts are free software under a license similar to the X11 license,
allowing use, modification, and redistribution.

**Source:** https://dejavu-fonts.github.io/

**Why bundled?**
Bundling fonts ensures pixel-perfect rendering regardless of what fonts are
installed on the target Raspberry Pi system. This is critical for matching
the visual design specified in the architecture plan.

**Size:** ~1.4MB total (acceptable for ensuring visual consistency)
