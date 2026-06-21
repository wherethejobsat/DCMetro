# AGENTS.md

## Project goal

Build a tiny static, mobile-first exit guide web app (PWA) that answers:
Given (station, line, direction), show which train car and door(s) are closest to each egress type (escalator, stairs, elevator).

The output must be easy to use on a phone and must work offline after first load. Preserve the core product contract: dependency-free static site, no runtime API dependency, no external runtime assets, and no tracking/account/server requirement.

## Source data (inputs, do not edit)

These CSVs are the source of truth (see meta.csv for column meanings):

- meta.csv: column definitions / variable meanings
- Doors.csv: x positions of train doors for a parked train
- Stations.csv: station metadata
- Exits.csv: exit text for stations with multiple exits
- Egresses.csv: egress markers (icons) and their x positions

If any of these are missing or malformed, fail fast with a clear error. Do not invent local fallbacks, substitute alternate data, or silently coerce source schema problems.

## Generated and maintained files

`scripts/build_site.py` reads the source CSVs and generates exactly these app files:

- docs/index.html
- docs/app.js
- docs/sw.js
- docs/manifest.webmanifest
- docs/social-preview.svg
- docs/icons/icon-192.svg
- docs/icons/icon-512.svg

Do not hand-edit generated files independently. Change the build templates, source logic, or CSV inputs, then regenerate with `python scripts/build_site.py`.

Current app split:

- `docs/index.html`: generated page shell, CSS, and embedded derived JSON in `<script id="app-data" type="application/json">`.
- `docs/app.js`: generated browser logic loaded by `index.html`; it reads the embedded JSON from the DOM.
- No runtime data fetch is allowed. The app must keep working from the committed static files after first load.

`docs/README.md` is hand-maintained deployment documentation, not a generated build output. See `DATA_PROVENANCE.md` for the authoritative source/generated/hand-maintained inventory. See `CHANGELOG.md` for release and data-change history.

## Scripts

- `scripts/build_site.py`: builds generated `docs/` app output from the CSV source files.
- `scripts/validate_build.py`: validates required files, schemas, embedded app data, and station-code coverage.
- `scripts/validate_domain.py`: validates domain inventory, station references, direction labels, line coverage, split-level cases, transfers, and representative regressions.

## Development commands

Build:

```sh
python scripts/build_site.py
```

Validate:

```sh
python scripts/validate_build.py
python scripts/validate_domain.py
```

Confirm generated files are up to date:

```sh
git diff --exit-code -- docs/index.html docs/app.js docs/sw.js docs/manifest.webmanifest docs/social-preview.svg docs/icons/icon-192.svg docs/icons/icon-512.svg
```

Serve locally:

```sh
python -m http.server --directory docs 8000
```

Then open `http://localhost:8000/`.

No Node toolchain is required or expected.

## Non-negotiable constraints

- No runtime network dependency: the app must work without network after the first load.
- No external JS/CSS/fonts at runtime (no CDNs).
- Prefer zero dependencies. Use only Python stdlib in scripts and vanilla browser APIs in the web app.
  If you believe a dependency is necessary, stop and ask first.
- Use plain ASCII punctuation in committed text (no curly quotes or non-ASCII punctuation). Code may normalize non-ASCII source-data variants where necessary; represent those variants with explicit escapes where practical and explain why.

## Data processing requirements

- Do not assume the CSV schemas. Inspect headers and use meta.csv to interpret columns.
- Validate source schemas, required columns, station references, station-code coverage, and expected line/direction cases before trusting output.
- Produce a derived, lookup-optimized data model embedded in docs/index.html and consumed by docs/app.js that supports:
  - station autocomplete
  - line selector (only lines that serve the station)
  - direction selector (2 directions per line at that station)
  - per-egress-type output (escalator, stairs, elevator, other)
- Keep generated data and output ordering deterministic across repeated builds.

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

Egresses.csv encodes an icon/type. Map recognized values to:
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
  - app.js
  - manifest
  - sw.js
  - social-preview.svg
  - icons
- Use a simple cache-first strategy for static assets.
- Ensure updates work. When generated static assets change in a way that requires clients to refresh service-worker cache, make sure the generated CACHE_VERSION changes; update the build cache-version seed if needed.

## Quality bar

- Must work in iOS Safari and Android Chrome.
- Large tap targets (about 44px).
- No console errors on load.
- Deterministic build: repeated runs of build_site.py produce stable output ordering.
- Preserve accessibility expectations for readable labels, large tap targets, keyboard-usable controls, copyable plain-text results, and clear no-affiliation language.
