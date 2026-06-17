# Release Checklist

- Run validation: `python scripts/build_site.py` and `python scripts/validate_build.py`.
- Open the site locally if possible: `python -m http.server --directory docs 8000`.
- Test station search.
- Test example buttons.
- Test URL params, for example `?station=Metro%20Center&line=RD&direction=WB`.
- Test copy feedback.
- Confirm GitHub repo About fields manually:
  - Description: "Fast offline DC Metro exit guide: find the train car and door closest to escalators, stairs, and elevators."
  - Website: https://wherethejobsat.github.io/DCMetro/
  - Topics: wmata, dc-metro, washington-dc, transit, pwa, github-pages, open-data, javascript, python
- Tag first public release, suggested: `v2025.12-data`.
- Post using `LAUNCH_POST.md`.
