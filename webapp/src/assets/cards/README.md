# Animated cards

Place card artwork for the Home carousel in this folder.

Recommended naming keeps the visual order predictable:

- `01.webp`
- `02.webp`
- `03.webp`
- ...

Supported formats: PNG, JPG/JPEG, WEBP, AVIF and SVG.

You can also place files directly in `webapp/src/assets/` when their names start with `card-`, for example `card-01.webp`.

The carousel discovers these files at Vite build time, so redeploy/rebuild the webapp after adding or replacing card images.
