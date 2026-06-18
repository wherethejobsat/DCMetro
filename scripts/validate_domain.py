#!/usr/bin/env python3
import csv
import json
import re
import sys
from pathlib import Path

from build_site import build_station_reference_lookup, resolve_station_reference

BASE_DIR = Path(__file__).resolve().parents[1]
DOCS_DIR = BASE_DIR / "docs"

LINE_COLUMNS = {
    "RD": "hasRD",
    "GR": "hasGR",
    "YL": "hasYL",
    "BL": "hasBL",
    "OR": "hasOR",
    "SV": "hasSV",
}
LINE_CODES = set(LINE_COLUMNS)
DIRECTION_KEYS = {"WB", "EB"}
STATION_CODE_PATTERN = re.compile(r"^[A-Z][0-9]{2}$")

EXPECTED_CASES = [
    ("Metro Center (Upper Level)", "A01", {"RD"}),
    ("Metro Center (Lower Level)", "C01", {"BL", "OR", "SV"}),
    ("Gallery Place (Upper Level)", "B01", {"RD"}),
    ("Gallery Place (Lower Level)", "F01", {"GR", "YL"}),
    ("L'Enfant Plaza (Upper Level)", "F03", {"GR", "YL"}),
    ("L'Enfant Plaza (Lower Level)", "D03", {"BL", "OR", "SV"}),
    ("Fort Totten (Upper Level)", "B06", {"RD"}),
    ("Fort Totten (Lower Level)", "E06", {"GR", "YL"}),
    ("Rosslyn", "C05", {"BL", "OR", "SV"}),
    ("Washington National Airport", "C10", {"YL", "BL"}),
    ("Columbia Heights", "E04", {"GR", "YL"}),
]


def fail(message):
    print(f"Error: {message}", file=sys.stderr)
    raise SystemExit(1)


def read_rows(path):
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def is_true(value):
    return str(value).strip().upper() in {"TRUE", "T", "YES", "1"}


def station_lines(row):
    return {code for code, col in LINE_COLUMNS.items() if is_true(row.get(col))}


def load_app_data():
    html_path = DOCS_DIR / "index.html"
    if not html_path.exists():
        fail("docs/index.html does not exist. Run scripts/build_site.py first.")
    html = html_path.read_text(encoding="utf-8")
    match = re.search(
        r"<script id=\"app-data\" type=\"application/json\">(.*?)</script>",
        html,
        re.S,
    )
    if not match:
        fail("docs/index.html missing embedded app-data JSON.")
    return json.loads(match.group(1))


def load_station_sources():
    station_rows = read_rows(BASE_DIR / "Stations.csv")
    if not station_rows:
        fail("Stations.csv has no data rows.")

    by_name = {}
    duplicates = set()
    for row in station_rows:
        name = row.get("nameStd", "").strip()
        if not name:
            fail("Stations.csv has a missing station name.")
        if name in by_name:
            duplicates.add(name)
        by_name[name] = row

    if duplicates:
        fail(f"Stations.csv has duplicate stations: {', '.join(sorted(duplicates))}")

    for name, row in by_name.items():
        lines = station_lines(row)
        if not lines:
            fail(f"Station has no active lines: {name}")
        unknown_lines = lines - LINE_CODES
        if unknown_lines:
            fail(f"Station has unknown lines for {name}: {', '.join(sorted(unknown_lines))}")
        if not row.get("WBDir", "").strip() or not row.get("EBDir", "").strip():
            fail(f"Station has an empty direction label: {name}")

    return by_name


def validate_cross_file_station_references(source_rows):
    station_lookup = build_station_reference_lookup(source_rows)
    for file_name in ("Exits.csv", "Egresses.csv"):
        for row in read_rows(BASE_DIR / file_name):
            station = row.get("nameStd", "").strip()
            if station:
                resolve_station_reference(station, station_lookup, file_name)


def validate_expected_source_cases(source_by_name):
    for name, expected_code, expected_lines in EXPECTED_CASES:
        row = source_by_name.get(name)
        if row is None:
            fail(f"Stations.csv is missing expected station case: {name}")
        found_lines = station_lines(row)
        if found_lines != expected_lines:
            fail(f"Unexpected source lines for {name}: {sorted(found_lines)}")
        if not row.get("WBDir", "").strip() or not row.get("EBDir", "").strip():
            fail(f"Expected station has empty direction labels: {name}")


def validate_embedded_inventory(data, source_names):
    stations = data.get("stations", [])
    if not stations:
        fail("Embedded data has no stations.")

    names = [station.get("name") for station in stations]
    embedded_names = set(names)
    if embedded_names != source_names:
        missing = sorted(source_names - embedded_names)
        extra = sorted(embedded_names - source_names)
        fail(f"Embedded station mismatch. Missing: {missing}. Extra: {extra}.")
    if len(names) != len(embedded_names):
        fail("Embedded data has duplicate station names.")

    for station in stations:
        name = station.get("name")
        code = station.get("station_code")
        if not code or not STATION_CODE_PATTERN.fullmatch(code):
            fail(f"Invalid station_code for {name}: {code}")

        lines = station.get("lines") or []
        if not lines:
            fail(f"Embedded station has no lines: {name}")
        unknown_lines = set(lines) - LINE_CODES
        if unknown_lines:
            fail(f"Embedded station has unknown lines for {name}: {', '.join(sorted(unknown_lines))}")

        directions = station.get("directions") or []
        if {direction.get("key") for direction in directions} != DIRECTION_KEYS:
            fail(f"Embedded station has invalid directions: {name}")
        if any(not direction.get("label") for direction in directions):
            fail(f"Embedded station has an empty direction label: {name}")

    by_name = {station.get("name"): station for station in stations}
    for name, expected_code, expected_lines in EXPECTED_CASES:
        station = by_name.get(name)
        if station is None:
            fail(f"Embedded data is missing expected station case: {name}")
        if station.get("station_code") != expected_code:
            fail(f"Unexpected station_code for {name}: {station.get('station_code')}")
        found_lines = set(station.get("lines") or [])
        if found_lines != expected_lines:
            fail(f"Unexpected embedded lines for {name}: {sorted(found_lines)}")


def main():
    source_by_name = load_station_sources()
    source_names = set(source_by_name)
    validate_cross_file_station_references(source_by_name.values())
    validate_expected_source_cases(source_by_name)
    validate_embedded_inventory(load_app_data(), source_names)
    print("Domain validation passed.")


if __name__ == "__main__":
    main()
