# Agent and Maintainer Guide

This file is repo-scoped guidance for automated coding agents and maintainers.
The user-facing project overview lives in `README.md`; deployment and artifact
inventory details live in `docs/README.md` and `DATA_PROVENANCE.md`.

## Product Contract

Build a tiny static, mobile-first exit guide web app that answers:
given a station, line, and direction, show which train car and door or doors
are closest to each egress type: escalator, stairs, elevator, and other.

Preserve the core contract:

- Dependency-free static site.
- No runtime API dependency.
- No external runtime JS, CSS, fonts, images, or tracking.
- No account, backend server, or build-time Node toolchain.
- Works offline after first load.

## Source Data

These CSVs are source inputs and should not be edited casually:

- `meta.csv`: column definitions and variable meanings.
- `Doors.csv`: x positions of train doors for a parked train.
- `Stations.csv`: station metadata.
- `Exits.csv`: exit text for stations with multiple exits.
- `Egresses.csv`: egress markers and x positions.

If source files are missing or malformed, fail fast with a clear error. Do not
invent local fallbacks, substitute alternate data, or silently coerce source
schema problems.

## Generated Files

`scripts/build_site.py` reads the source CSVs and generates exactly these app
files:

- `docs/index.html`
- `docs/app.js`
- `docs/sw.js`
- `docs/manifest.webmanifest`
- `docs/social-preview.svg`
- `docs/icons/icon-192.svg`
- `docs/icons/icon-512.svg`

Do not hand-edit generated files independently. Change the build script,
templates, source logic, or source CSVs, then regenerate with:

```sh
python scripts/build_site.py
```

Current generated app split:

- `docs/index.html`: page shell, CSS, and embedded derived JSON in
  `<script id="app-data" type="application/json">`.
- `docs/app.js`: browser logic that reads embedded JSON from the DOM.
- No runtime data fetch is allowed.

`docs/README.md` is hand-maintained deployment documentation. See
`DATA_PROVENANCE.md` for the source/generated/hand-maintained inventory and
`CHANGELOG.md` for release and data-change history.

## Development Commands

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

## Data Processing Rules

- Inspect headers and use `meta.csv` to interpret columns.
- Validate source schemas, required columns, station references, station-code
  coverage, and expected line/direction cases before trusting output.
- Keep generated data and output ordering deterministic across repeated builds.
- Embed the derived lookup-optimized data model in `docs/index.html`; consume it
  from `docs/app.js`.
- Support station autocomplete, station-specific line choices, two directions
  per line at each station, and per-egress-type results.

### Door Labels

From `Doors.csv`, derive stable door labels from ordered door positions:

- `door_index`: 1..N along the full train length.
- `car_index`: 1..C, inferred from the data.
- `door_in_car`: 1..D, inferred from the data.

The UI must display both "Car X, Door Y" and "Door index Z".

### Nearest Doors

For each egress x position:

- Compute nearest door or doors by absolute x-distance.
- If adjacent doors are near-tied within the configured threshold, show a range.
- Store the delta distance for optional display.

### Egress Types

Map recognized egress icons/types to:

- escalator
- stairs
- elevator

Unknown or ambiguous values belong under `other`; do not drop them.

### Directions

Use "Toward <terminal>" labels when terminal names exist in the data. Otherwise
use stable "Direction A" and "Direction B" labels.

## UI and PWA Requirements

- Single-page, responsive, mobile-first app.
- Large tap targets, about 44px or larger.
- Station search with autocomplete and fuzzy match by name and station code.
- Line selector and direction selector.
- Results for escalators, stairs, elevators, and other egresses.
- Copy button that copies the current results as plain text.
- Compact About section with attribution and "not affiliated with WMATA" text.
- `manifest.webmanifest` and `sw.js` for offline caching.
- Cache `index.html`, `app.js`, manifest, service worker, social preview, and
  icons.
- Use a simple cache-first strategy for static assets.
- When generated static assets change in a cache-relevant way, update the
  generated cache version seed.

## Quality Bar

- Must work in iOS Safari and Android Chrome.
- No console errors on load.
- Deterministic builds.
- Accessible labels, keyboard-usable controls, readable text, and copyable
  plain-text results.
- Plain ASCII punctuation in committed text. Source-data normalization may
  represent non-ASCII variants with explicit escapes where needed.
