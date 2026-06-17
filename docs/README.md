# DC Metro Exit Guide (static PWA)

## Public URL

Live app: https://wherethejobsat.github.io/DCMetro/

This repo is configured to publish the static app from `docs/` with GitHub
Pages. If the repository is public, GitHub visitors can also find this link at
the top of the root README.

No Node toolchain or Python package install step is needed for the current
build.

## Local build and serve

1) Build the site:

   python scripts/build_site.py

2) Validate the build:

   python scripts/validate_build.py

3) Serve locally:

   python -m http.server --directory docs 8000

Open http://localhost:8000/

## Deploy

### GitHub Pages (docs folder)

1) Commit the generated `docs/` folder.
2) In GitHub, go to Settings -> Pages.
3) Set Source to the branch you want, and Folder to `/docs`.
4) Save.
5) Optional: in the repo About panel, set Website to
   `https://wherethejobsat.github.io/DCMetro/` so the app link appears in the
   sidebar too.

### Netlify

- Build command: python scripts/build_site.py
- Publish directory: docs

### Cloudflare Pages

- Build command: python scripts/build_site.py
- Build output directory: docs
