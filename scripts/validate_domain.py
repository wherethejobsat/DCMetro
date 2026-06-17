#!/usr/bin/env python3
import csv
import json
import re
import sys
from pathlib import Path

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
EGRESS_TYPES = {"escalator", "stairs", "elevator", "other"}
STATION_CODE_PATTERN = re.compile(r"^[A-Z][0-9]{2}$")

EXPECTED_CASES = [
    ("Metro Center (Upper Level)", "A01", ["RD"]),
    ("Metro Center (Lower Level)", "C01", ["BL", "OR", "SV"]),
    ("Gallery Place (Upper Level)", "B01", ["RD"]),
    ("Gallery Place (Lower Level)", "F01", ["GR", "YL"]),
    ("L'Enfant Plaza (Upper Level)", "F03", ["GR", "YL"]),
    ("L'Enfant Plaza (Lower Level)", "D03", ["BL", "OR", "SV"]),
    ("Fort Totten (Upper Level)", "B06", ["RD"]),
    ("Fort Totten (Lower Level)", "E06", ["GR", "YL"]),
    ("Rosslyn", "C05", ["BL", "OR", "SV"]),
    ("Washington National Airport", "C10", ["YL", "BL"]),
    ("Columbia Heights", "E04", ["GR", "YL"]),
]


def fail(message):
    print(f"Error: {message}", file=sys.stderr)
    raise SystemExit(1)


def read_rows(path):
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def is_true(value):
    return str(value).strip().upper() in {"TRUE", "T", "YES", "1"}


def as_float(value, label):
    try:
        return float(value)
    except (TypeError, ValueError):
        fail(f"Invalid numeric value for {label}: {value}")


def as_int(value, label):
    number = as_float(value, label)
    if not number.is_integer():
        fail(f"Invalid integer value for {label}: {value}")
    return int(number)


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


def validate_source_csvs():
    station_rows = read_rows(BASE_DIR / "Stations.csv")
    exit_rows = read_rows(BASE_DIR / "Exits.csv")
    egress_rows = read_rows(BASE_DIR / "Egresses.csv")
    door_rows = read_rows(BASE_DIR / "Doors.csv")

    names = [row.get("nameStd", "").strip() for row in station_rows]
    if not names or any(not name for name in names):
        fail("Stations.csv has a missing station name.")
    duplicates = sorted(name for name in set(names) if names.count(name) > 1)
    if duplicates:
        fail(f"Stations.csv has duplicate stations: {', '.join(duplicates)}")

    for row in station_rows:
        name = row.get("nameStd", "").strip()
        lines = [code for code, col in LINE_COLUMNS.items() if is_true(row.get(col))]
        if not lines:
            fail(f"Station has no active lines: {name}")
        if not row.get("WBDir", "").strip() or not row.get("EBDir", "").strip():
            fail(f"Station has an empty direction label: {name}")

    name_set = set(names)
    for source_name, rows in (("Exits.csv", exit_rows), ("Egresses.csv", egress_rows)):
        for row in rows:
            station = row.get("nameStd", "").strip()
            if station and station not in name_set:
                fail(f"{source_name} references unknown station: {station}")

    door_x = [as_float(row.get("x"), "Doors.csv x") for row in door_rows]
    if not door_x:
        fail("Doors.csv has no door positions.")
    min_x = min(door_x)
    max_x = max(door_x)
    for row in egress_rows:
        station = row.get("nameStd", "").strip()
        x_value = as_float(row.get("x"), f"Egresses.csv x for {station}")
        if not (min_x - 5 <= x_value <= max_x + 5):
            fail(f"Egress x is outside door range for {station}: {x_value}")
        y_value = row.get("y", "").strip()
        if y_value:
            as_int(y_value, f"Egresses.csv y for {station}")

    return set(names)


def validate_app_data(data, source_names):
    meta = data.get("meta", {})
    stations = data.get("stations", [])
    door_count = meta.get("door_count")
    car_count = meta.get("car_count")
    doors_per_car_max = meta.get("doors_per_car_max")
    if not isinstance(door_count, int) or door_count <= 0:
        fail("Embedded meta has invalid door_count.")
    if not isinstance(car_count, int) or car_count <= 0:
        fail("Embedded meta has invalid car_count.")
    if not isinstance(doors_per_car_max, int) or doors_per_car_max <= 0:
        fail("Embedded meta has invalid doors_per_car_max.")

    names = [station.get("name") for station in stations]
    if set(names) != source_names:
        missing = sorted(source_names - set(names))
        extra = sorted(set(names) - source_names)
        fail(f"Embedded station mismatch. Missing: {missing}. Extra: {extra}.")
    if len(names) != len(set(names)):
        fail("Embedded data has duplicate station names.")

    for station in stations:
        name = station.get("name")
        code = station.get("station_code")
        if not code or not STATION_CODE_PATTERN.fullmatch(code):
            fail(f"Invalid station_code for {name}: {code}")
        lines = station.get("lines") or []
        if not lines or set(lines) - LINE_CODES:
            fail(f"Invalid lines for {name}: {lines}")
        directions = station.get("directions") or []
        if {direction.get("key") for direction in directions} != DIRECTION_KEYS:
            fail(f"Invalid directions for {name}.")
        if any(not direction.get("label") for direction in directions):
            fail(f"Empty direction label for {name}.")

        by_dir = station.get("egress_by_dir") or {}
        if set(by_dir) != DIRECTION_KEYS:
            fail(f"Invalid egress directions for {name}.")
        for direction_key, groups in by_dir.items():
            if set(groups) != EGRESS_TYPES:
                fail(f"Invalid egress groups for {name} {direction_key}.")
            for group_name, entries in groups.items():
                for entry in entries:
                    if entry.get("type") != group_name:
                        fail(f"Egress type mismatch for {name} {direction_key}.")
                    if not isinstance(entry.get("x"), (int, float)):
                        fail(f"Non-numeric egress x for {name}.")
                    if entry.get("delta") is not None and entry.get("delta") < 0:
                        fail(f"Negative egress delta for {name}.")
                    doors = entry.get("doors") or []
                    if not doors:
                        fail(f"Egress has no door result for {name}.")
                    for door in doors:
                        if not 1 <= door.get("door_index", 0) <= door_count:
                            fail(f"Invalid door_index for {name}: {door}")
                        if not 1 <= door.get("car_index", 0) <= car_count:
                            fail(f"Invalid car_index for {name}: {door}")
                        if not 1 <= door.get("door_in_car", 0) <= doors_per_car_max:
                            fail(f"Invalid door_in_car for {name}: {door}")

    by_name = {station.get("name"): station for station in stations}
    for name, expected_code, expected_lines in EXPECTED_CASES:
        station = by_name.get(name)
        if station is None:
            fail(f"Missing expected station case: {name}")
        if station.get("station_code") != expected_code:
            fail(f"Unexpected station_code for {name}: {station.get('station_code')}")
        if set(station.get("lines") or []) != set(expected_lines):
            fail(f"Unexpected lines for {name}: {station.get('lines')}")


def main():
    source_names = validate_source_csvs()
    data = load_app_data()
    validate_app_data(data, source_names)
    print("Domain validation passed.")


if __name__ == "__main__":
    main()
