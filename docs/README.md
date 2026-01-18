# Metro Exit Guide (static PWA)

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

1) Commit the generated docs/ folder.
2) In GitHub, go to Settings -> Pages.
3) Set Source to the branch you want, and Folder to /docs.
4) Save.

### Netlify

- Build command: python scripts/build_site.py
- Publish directory: docs

### Cloudflare Pages

- Build command: python scripts/build_site.py
- Build output directory: docs
