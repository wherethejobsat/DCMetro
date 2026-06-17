# Data Provenance

## Source material

The app is built from the CSV files in the repo root:

- `meta.csv`: column definitions and variable meanings.
- `Doors.csv`: train door x positions.
- `Stations.csv`: station names, line flags, platform type, and direction labels.
- `Exits.csv`: exit labels and descriptions.
- `Egresses.csv`: egress marker types and x positions.

The repo also includes source/reference PDFs named `WMATA Metro Station Platform Exit Guide June 2025.pdf` and `WMATA Metro Station Platform Exit Guide December 2025.pdf`. The documented source year is 2025. The CSV files are the source of truth for the generated app.

## Generated files

`python scripts/build_site.py` reads the CSVs and writes:

- `docs/index.html`
- `docs/app.js`
- `docs/sw.js`
- `docs/manifest.webmanifest`
- `docs/social-preview.svg`
- `docs/icons/icon-192.svg`
- `docs/icons/icon-512.svg`

The embedded JSON in `docs/index.html` is generated from the CSV source files. It is optimized for station lookup and nearest-door display. CI rebuilds these files and fails if the committed generated output differs from the source build output.

## Validation

- `scripts/validate_build.py` checks required files, required columns, embedded app data, and WMATA station-code coverage.
- `scripts/validate_domain.py` checks station source rows, active line coverage, direction labels, cross-file station references, egress coordinate sanity, generated door bounds, split-level station cases, and representative station-code/line regressions.

## Hand-maintained files

Based on the current repo layout, these files are hand-maintained:

- The root CSV source files and reference PDFs.
- `scripts/build_site.py`
- `scripts/validate_build.py`
- `scripts/validate_domain.py`
- `README.md`
- `DATA_PROVENANCE.md`
- `LICENSE`
- `.github/` workflow and issue templates.
- `LAUNCH_POST.md`
- `RELEASE_CHECKLIST.md`

## Non-affiliation

This project is not affiliated with, endorsed by, or maintained by WMATA.

## Corrections

If a station recommendation looks wrong, open an issue with:

- Station
- Line
- Direction
- Exit element type: escalator, stairs, elevator, or other
- Current app result
- Corrected result
- Evidence or source
- Date observed

Station conditions, construction, signage, elevator access, escalator status, and normal operating patterns can change.

## Reuse note

The code in this repo has its own license. Rights to the underlying data, PDFs, station geometry, or other source material may differ. Do not treat this repo's code license as a blanket license for WMATA source material unless you have confirmed the source-material rights separately.
