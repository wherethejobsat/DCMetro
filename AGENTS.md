# AGENTS.md

## Project goal

Build a tiny static, mobile-first exit guide web app (PWA) that answers:
Given (station, line, direction), show which train car and door(s) are closest to each egress type (escalator, stairs, elevator).

The output must be easy to use on a phone and must work offline after first load.

## Source data (inputs, do not edit)

These CSVs are the source of truth (see meta.csv for column meanings):

- meta.csv: column definitions / variable meanings
- Doors.csv: x positions of train doors for a parked train
- Stations.csv: station metadata
- Exits.csv: exit text for stations with multiple exits
- Egresses.csv: egress markers (icons) and their x positions

If any of these are missing, fail fast with a clear error.

## Output layout (what to create)

- docs/
  - index.html            Single-page app. Must embed the derived data as JSON in the HTML (no runtime data fetch).
  - manifest.webmanifest  PWA manifest
  - sw.js                 Service worker for offline caching
  - icons/                App icons (at least 192 and 512; can be generated)
  - README.md             How to run locally and deploy (GitHub Pages, Netlify, Cloudflare Pages)

- scripts/
  - build_site.py         Builds docs/index.html by reading the CSVs and embedding a derived JSON payload
  - validate_build.py     Minimal validation/sanity checks (schema expectations, non-empty outputs)

## Development commands

- Build:  python scripts/build_site.py
- Validate: python scripts/validate_build.py
- Serve locally: python -m http.server --directory docs 8000
  Then open: http://localhost:8000/

No Node toolchain is required or expected.

## Non-negotiable constraints

- No runtime network dependency: the app must work without network after the first load.
- No external JS/CSS/fonts at runtime (no CDNs).
- Prefer zero dependencies. Use only Python stdlib in scripts and vanilla browser APIs in the web app.
  If you believe a dependency is necessary, stop and ask first.
- ASCII-only in all committed files (no curly quotes, no non-ASCII punctuation).

## Data processing requirements

- Do not assume the CSV schemas. Inspect headers and use meta.csv to interpret columns.
- Produce a derived, lookup-optimized data model (embed in docs/index.html) that supports:
  - station autocomplete
  - line selector (only lines that serve the station)
  - direction selector (2 directions per line at that station)
  - per-egress-type output (escalator, stairs, elevator)

### Door labeling

From Doors.csv, derive stable door labels.

At minimum, for each door position (ordered along the platform), compute:
- door_index: 1..N along the full train length
- car_index: 1..C (infer C; likely 8 but do not hardcode if the data says otherwise)
- door_in_car: 1..D (infer D doors per car from Doors.csv)

In the UI, display both:
- "Car X, Door Y" (within-car)
- and "Door index Z" (overall index along the train)

### Nearest-door logic

For each egress x position:
- compute the nearest door(s) by absolute delta in x
- if two adjacent doors are near-tied (within a small threshold), show a range (e.g., "Doors 12-13")
- store the delta distance so the UI can optionally show how close the match is

### Egress type mapping

Egresses.csv likely encodes an icon/type. Map to:
- escalator
- stairs
- elevator

If an icon does not map cleanly, show it under "other" rather than dropping it.

### Directions

If the dataset includes terminal names, use "Toward <terminal>" labels.
If not, use "Direction A" and "Direction B" but keep them stable and consistent with the dataset.

## UI requirements (docs/index.html)

- Single page, responsive, mobile-first.
- Station search with autocomplete and fuzzy match (name + station code if present).
- Line selector and direction selector.
- Results section that renders, at minimum:
  - Escalators: list each relevant escalator egress and its recommended boarding position
  - Stairs: same
  - Elevators: same
- Provide a "Copy" button that copies the currently displayed results (plain text) to clipboard.
- Provide a compact "About" section with attribution and "not affiliated with WMATA" note.

## PWA/offline requirements

- manifest.webmanifest + sw.js for offline caching.
- Service worker should cache:
  - index.html
  - manifest
  - sw.js
  - icons
- Use a simple cache-first strategy for static assets.
- Ensure updates work (e.g., bump a cache version string during build).

## Quality bar

- Must work in iOS Safari and Android Chrome.
- Large tap targets (about 44px).
- No console errors on load.
- Deterministic build: repeated runs of build_site.py produce stable output ordering.
