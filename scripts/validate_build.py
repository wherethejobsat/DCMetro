#!/usr/bin/env python3
import csv
import json
import re
import sys
from pathlib import Path
from collections import defaultdict

BASE_DIR = Path(__file__).resolve().parents[1]
DOCS_DIR = BASE_DIR / "docs"

INPUT_FILES = {
    "meta": BASE_DIR / "meta.csv",
    "doors": BASE_DIR / "Doors.csv",
    "stations": BASE_DIR / "Stations.csv",
    "exits": BASE_DIR / "Exits.csv",
    "egresses": BASE_DIR / "Egresses.csv",
}

REQUIRED_COLUMNS = {
    "Doors": ["Car", "x"],
    "Stations": [
        "nameStd",
        "nameAlt",
        "subtitile",
        "hasRD",
        "hasGR",
        "hasYL",
        "hasBL",
        "hasOR",
        "hasSV",
        "platformType",
        "WBDir",
        "EBDir",
    ],
    "Exits": ["nameStd", "exitLabel", "description"],
    "Egresses": [
        "nameStd",
        "icon",
        "y",
        "x",
        "dir",
        "zDir",
        "pref",
        "x2",
        "exitLabel",
        "group",
    ],
}


def fail(message):
    print(f"Error: {message}", file=sys.stderr)
    raise SystemExit(1)


def read_meta(path):
    meta = defaultdict(set)
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            file_key = row.get("File", "").strip()
            var = row.get("Variable", "").strip()
            if file_key and var:
                for part in file_key.split(","):
                    key = part.strip()
                    if key:
                        meta[key].add(var)
    return meta


def ensure_inputs_exist():
    for label, path in INPUT_FILES.items():
        if not path.exists():
            fail(f"Missing required input file: {path}")


def ensure_columns(meta, file_label, headers, required):
    missing = [col for col in required if col not in headers]
    if missing:
        fail(f"{file_label} missing columns: {', '.join(missing)}")

    meta_missing = [col for col in required if col not in meta.get(file_label, set())]
    if meta_missing:
        fail(f"meta.csv missing variables for {file_label}: {', '.join(meta_missing)}")


def load_headers(path):
    with path.open(newline="") as handle:
        reader = csv.reader(handle)
        return next(reader, [])


def load_station_names(path):
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        return [row.get("nameStd", "").strip() for row in reader if row.get("nameStd")]


def load_embedded_data(path):
    html = path.read_text(encoding="utf-8")
    match = re.search(r"<script id=\"app-data\" type=\"application/json\">(.*?)</script>", html, re.S)
    if not match:
        fail("docs/index.html missing embedded app-data JSON")
    return json.loads(match.group(1))


def validate():
    ensure_inputs_exist()

    meta = read_meta(INPUT_FILES["meta"])
    for key, file_path in {
        "Doors": INPUT_FILES["doors"],
        "Stations": INPUT_FILES["stations"],
        "Exits": INPUT_FILES["exits"],
        "Egresses": INPUT_FILES["egresses"],
    }.items():
        headers = load_headers(file_path)
        ensure_columns(meta, key, headers, REQUIRED_COLUMNS[key])

    index_path = DOCS_DIR / "index.html"
    if not index_path.exists():
        fail("docs/index.html does not exist. Run scripts/build_site.py first.")

    app_js_path = DOCS_DIR / "app.js"
    if not app_js_path.exists():
        fail("docs/app.js does not exist. Run scripts/build_site.py first.")
    if not app_js_path.read_text(encoding="utf-8").strip():
        fail("docs/app.js is empty.")

    data = load_embedded_data(index_path)
    stations = data.get("stations", [])
    if not stations:
        fail("Embedded data has no stations.")

    names_in_data = {station.get("name") for station in stations}
    sample_names = [name for name in load_station_names(INPUT_FILES["stations"]) if name][:3]
    if not sample_names:
        fail("Stations.csv has no station names.")

    for name in sample_names:
        if name not in names_in_data:
            fail(f"Station not found in embedded data: {name}")

    print("Validation passed.")


if __name__ == "__main__":
    validate()
