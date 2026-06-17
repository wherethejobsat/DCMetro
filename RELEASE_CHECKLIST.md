# Release Checklist

- Rebuild: `python scripts/build_site.py`.
- Run validation: `python scripts/validate_build.py` and `python scripts/validate_domain.py`.
- Confirm generated files are committed: `git diff --exit-code -- docs/index.html docs/app.js docs/sw.js docs/manifest.webmanifest docs/social-preview.svg docs/icons/icon-192.svg docs/icons/icon-512.svg`.
- Open the site locally if possible: `python -m http.server --directory docs 8000`.
- Test station search.
- Test example buttons.
- Test URL params, for example `?station=Metro%20Center&line=RD&direction=WB`.
- Test split-level transfer stations: Metro Center, Gallery Place, L'Enfant Plaza, and Fort Totten.
- Test copy feedback.
- Confirm GitHub repo About fields manually:
  - Description: "Fast offline DC Metro exit guide: find the train car and door closest to escalators, stairs, and elevators."
  - Website: https://wherethejobsat.github.io/DCMetro/
  - Topics: wmata, dc-metro, washington-dc, transit, pwa, github-pages, open-data, javascript, python
- Tag first public release, suggested: `v2025.12-data`.
- Post using `LAUNCH_POST.md`.
