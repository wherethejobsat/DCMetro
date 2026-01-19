#!/usr/bin/env python3
import csv
import hashlib
import json
import os
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
DOCS_DIR = BASE_DIR / "docs"
ICONS_DIR = DOCS_DIR / "icons"

INPUT_FILES = {
    "meta": BASE_DIR / "meta.csv",
    "doors": BASE_DIR / "Doors.csv",
    "stations": BASE_DIR / "Stations.csv",
    "exits": BASE_DIR / "Exits.csv",
    "egresses": BASE_DIR / "Egresses.csv",
}

LINE_DEFS = [
    ("RD", "Red", "#c60c30"),
    ("GR", "Green", "#00a651"),
    ("YL", "Yellow", "#ffd200"),
    ("BL", "Blue", "#0078bf"),
    ("OR", "Orange", "#f29330"),
    ("SV", "Silver", "#a2a4a3"),
]

LINE_COLS = {
    "RD": "hasRD",
    "GR": "hasGR",
    "YL": "hasYL",
    "BL": "hasBL",
    "OR": "hasOR",
    "SV": "hasSV",
}

EGRESS_TYPE_MAP = {
    "esc": "escalator",
    "el": "elevator",
    "stair": "stairs",
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

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\">
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
  <meta name=\"theme-color\" content=\"#0f4c4b\">
  <link rel=\"manifest\" href=\"./manifest.webmanifest\">
  <title>Metro Exit Guide</title>
  <style>
    :root {
      --bg: #f4f1e6;
      --bg-accent: #e8f2f1;
      --ink: #1d2327;
      --muted: #5b646b;
      --card: rgba(255, 255, 255, 0.92);
      --accent: #0f4c4b;
      --accent-soft: #d5ebe9;
      --sun: #f08a24;
      --shadow: 0 12px 30px rgba(0, 0, 0, 0.12);
      --radius: 18px;
    }

    * {
      box-sizing: border-box;
    }

    body {
      margin: 0;
      min-height: 100vh;
      font-family: "Trebuchet MS", "Gill Sans", "Segoe UI", sans-serif;
      color: var(--ink);
      background:
        radial-gradient(circle at 15% 20%, rgba(240, 138, 36, 0.12), transparent 55%),
        radial-gradient(circle at 85% 10%, rgba(15, 76, 75, 0.12), transparent 45%),
        linear-gradient(130deg, var(--bg), var(--bg-accent));
    }

    header {
      padding: 24px 20px 8px;
      text-align: left;
    }

    header h1 {
      margin: 0 0 6px;
      font-family: "Georgia", "Times New Roman", serif;
      font-size: 1.6rem;
      letter-spacing: 0.5px;
    }

    header p {
      margin: 0;
      color: var(--muted);
      font-size: 0.95rem;
    }

    main {
      padding: 12px 20px 40px;
      max-width: 760px;
      margin: 0 auto;
    }

    .card {
      background: var(--card);
      border-radius: var(--radius);
      padding: 18px;
      box-shadow: var(--shadow);
      margin-bottom: 18px;
      animation: rise 0.6s ease both;
    }

    @keyframes rise {
      from {
        opacity: 0;
        transform: translateY(12px);
      }
      to {
        opacity: 1;
        transform: translateY(0);
      }
    }

    .field {
      margin-bottom: 14px;
    }

    label {
      display: block;
      font-weight: 600;
      margin-bottom: 6px;
    }

    input, select, button {
      width: 100%;
      min-height: 44px;
      border-radius: 12px;
      border: 1px solid #c9d2d5;
      padding: 10px 12px;
      font-size: 1rem;
      font-family: inherit;
      background: #fff;
    }

    input:focus, select:focus, button:focus {
      outline: 2px solid rgba(15, 76, 75, 0.35);
      outline-offset: 2px;
    }

    .combo {
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 8px;
    }

    .combo button {
      width: auto;
      padding: 0 14px;
      background: var(--accent-soft);
      border-color: transparent;
      cursor: pointer;
      font-weight: 600;
    }

    .suggestions {
      margin-top: 8px;
      border-radius: 12px;
      overflow: hidden;
      border: 1px solid #d4dbdf;
      background: #fff;
    }

    .suggestions button {
      border: none;
      border-bottom: 1px solid #edf1f3;
      text-align: left;
      width: 100%;
      padding: 12px 14px;
      background: #fff;
      cursor: pointer;
    }

    .suggestions button:last-child {
      border-bottom: none;
    }

    .tags {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      margin-top: 6px;
    }

    .tag {
      padding: 2px 8px;
      border-radius: 999px;
      font-size: 0.75rem;
      font-weight: 700;
      color: #1f2327;
      background: #e5ecef;
    }

    .results-header {
      display: flex;
      flex-direction: column;
      gap: 10px;
      margin-bottom: 14px;
    }

    .results-header .meta {
      color: var(--muted);
      font-size: 0.9rem;
    }

    .copy-btn {
      background: var(--accent);
      color: #fff;
      border: none;
      font-weight: 700;
      cursor: pointer;
    }

    .egress-block {
      margin-bottom: 16px;
      animation: fadeIn 0.6s ease both;
    }

    .egress-block h3 {
      margin: 0 0 8px;
      font-size: 1.1rem;
      font-family: "Georgia", "Times New Roman", serif;
    }

    .egress-item {
      background: #f9fbfb;
      border-radius: 14px;
      padding: 12px 14px;
      margin-bottom: 8px;
      border: 1px solid #e4ebee;
    }

    .egress-item strong {
      display: block;
      margin-bottom: 4px;
    }

    .egress-item .muted {
      color: var(--muted);
      font-size: 0.9rem;
    }

    .empty {
      color: var(--muted);
      font-style: italic;
      padding: 8px 0;
    }

    .about {
      font-size: 0.9rem;
      color: var(--muted);
      line-height: 1.5;
    }

    @keyframes fadeIn {
      from { opacity: 0; transform: translateY(8px); }
      to { opacity: 1; transform: translateY(0); }
    }

    @media (min-width: 720px) {
      header {
        text-align: center;
      }

      .results-header {
        flex-direction: row;
        justify-content: space-between;
        align-items: center;
      }
    }

    @media (prefers-reduced-motion: reduce) {
      * {
        animation: none !important;
      }
    }
  </style>
</head>
<body>
  <header>
    <h1>Metro Exit Guide</h1>
    <p>Pick a station, line, and direction to see the closest doors.</p>
  </header>
  <main>
    <section class=\"card\">
      <div class=\"field\">
        <label for=\"stationInput\">Station</label>
        <div class=\"combo\">
          <input id=\"stationInput\" type=\"text\" autocomplete=\"off\" placeholder=\"Start typing a station name\">
          <button id=\"clearStation\" type=\"button\">Clear</button>
        </div>
        <div id=\"stationSuggestions\" class=\"suggestions\" hidden></div>
      </div>
      <div class=\"field\">
        <label for=\"lineSelect\">Line</label>
        <select id=\"lineSelect\" disabled></select>
        <div id=\"lineTags\" class=\"tags\"></div>
      </div>
      <div class=\"field\">
        <label for=\"directionSelect\">Direction</label>
        <select id=\"directionSelect\" disabled></select>
      </div>
    </section>

    <section class=\"card\">
      <div class=\"results-header\">
        <div>
          <div id=\"resultsTitle\" class=\"meta\">Select a station to see results.</div>
          <div id=\"resultsSub\" class=\"meta\"></div>
        </div>
        <button id=\"copyBtn\" class=\"copy-btn\" type=\"button\" disabled>Copy</button>
      </div>
      <div id=\"results\"></div>
    </section>

    <section class=\"card\">
      <h2>About</h2>
      <p class=\"about\">
        Data source: WMATA Metro Station Platform Exit Guide (2025). Not affiliated with WMATA.
        Works offline after the first load.
      </p>
    </section>
  </main>

  <script id=\"app-data\" type=\"application/json\">{{DATA_JSON}}</script>
  <script>
    const DATA = JSON.parse(document.getElementById("app-data").textContent);
    const stationInput = document.getElementById("stationInput");
    const stationSuggestions = document.getElementById("stationSuggestions");
    const clearStation = document.getElementById("clearStation");
    const lineSelect = document.getElementById("lineSelect");
    const directionSelect = document.getElementById("directionSelect");
    const results = document.getElementById("results");
    const resultsTitle = document.getElementById("resultsTitle");
    const resultsSub = document.getElementById("resultsSub");
    const copyBtn = document.getElementById("copyBtn");
    const lineTags = document.getElementById("lineTags");

    const normalize = (value) => value
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, " ")
      .trim();

    const stations = DATA.stations.map((station) => {
      const tokens = [station.name, station.alt || "", station.subtitle || ""].join(" ");
      return {
        ...station,
        search: normalize(tokens),
        nameLower: station.name.toLowerCase(),
        altLower: (station.alt || "").toLowerCase(),
      };
    });

    let selectedStation = null;

    const lineName = (code) => (DATA.lines[code] ? DATA.lines[code].name : code);

    const renderLineTags = (station) => {
      lineTags.innerHTML = "";
      if (!station) {
        return;
      }
      station.lines.forEach((code) => {
        const tag = document.createElement("span");
        tag.className = "tag";
        tag.style.background = DATA.lines[code] ? DATA.lines[code].color : "#e5ecef";
        tag.style.color = "#111";
        tag.textContent = lineName(code);
        lineTags.appendChild(tag);
      });
    };

    const buildSuggestionButton = (station) => {
      const button = document.createElement("button");
      const subtitle = station.subtitle ? ` - ${station.subtitle}` : "";
      button.textContent = `${station.name}${subtitle}`;
      button.type = "button";
      button.addEventListener("click", () => selectStation(station));
      return button;
    };

    const showSuggestions = (items) => {
      stationSuggestions.innerHTML = "";
      if (!items.length) {
        stationSuggestions.hidden = true;
        return;
      }
      items.forEach((station) => {
        stationSuggestions.appendChild(buildSuggestionButton(station));
      });
      stationSuggestions.hidden = false;
    };

    const findSuggestions = (query) => {
      const q = normalize(query);
      if (!q) {
        return [];
      }
      const results = stations.map((station) => {
        let score = 0;
        if (station.nameLower.startsWith(query.toLowerCase())) {
          score += 3;
        }
        if (station.altLower && station.altLower.startsWith(query.toLowerCase())) {
          score += 2;
        }
        if (station.search.includes(q)) {
          score += 1;
        }
        return { station, score };
      }).filter((entry) => entry.score > 0);

      results.sort((a, b) => {
        if (b.score !== a.score) {
          return b.score - a.score;
        }
        return a.station.name.localeCompare(b.station.name);
      });

      return results.slice(0, 8).map((entry) => entry.station);
    };

    const fillSelect = (select, options, placeholder) => {
      select.innerHTML = "";
      if (placeholder) {
        const opt = document.createElement("option");
        opt.value = "";
        opt.textContent = placeholder;
        select.appendChild(opt);
      }
      options.forEach((item) => {
        const opt = document.createElement("option");
        opt.value = item.value;
        opt.textContent = item.label;
        select.appendChild(opt);
      });
    };

    const renderSelectors = () => {
      if (!selectedStation) {
        lineSelect.disabled = true;
        directionSelect.disabled = true;
        fillSelect(lineSelect, [], "Select a station first");
        fillSelect(directionSelect, [], "Select a station first");
        renderLineTags(null);
        return;
      }

      const lineOptions = selectedStation.lines.map((code) => ({
        value: code,
        label: `${lineName(code)} Line`,
      }));

      fillSelect(lineSelect, lineOptions, "Select a line");
      lineSelect.disabled = false;
      lineSelect.value = lineOptions.length ? lineOptions[0].value : "";

      const dirOptions = selectedStation.directions.map((dir) => ({
        value: dir.key,
        label: dir.label,
      }));
      fillSelect(directionSelect, dirOptions, "Select a direction");
      directionSelect.disabled = false;
      directionSelect.value = dirOptions.length ? dirOptions[0].value : "";

      renderLineTags(selectedStation);
    };

    const formatDoorLabel = (door) => `Car ${door.car_index}, Door ${door.door_in_car}`;

    const findDirectionLabel = (station, key) => {
      for (let i = 0; i < station.directions.length; i += 1) {
        if (station.directions[i].key === key) {
          return station.directions[i].label;
        }
      }
      return "";
    };

    const formatDoorIndex = (doors) => {
      if (doors.length === 1) {
        return `Door index ${doors[0].door_index}`;
      }
      const first = doors[0].door_index;
      const last = doors[doors.length - 1].door_index;
      return `Door index ${first}-${last}`;
    };

    const buildResultItem = (egress, index) => {
      const wrapper = document.createElement("div");
      wrapper.className = "egress-item";

      const title = document.createElement("strong");
      title.textContent = egress.label || `Egress ${index + 1}`;

      const doorLine = document.createElement("div");
      const doorLabels = egress.doors.map(formatDoorLabel);
      doorLine.textContent = doorLabels.length > 1
        ? `${doorLabels.join(" or ")}`
        : doorLabels[0];

      const details = document.createElement("div");
      details.className = "muted";
      const delta = egress.delta != null ? `, delta ${egress.delta}` : "";
      details.textContent = `${formatDoorIndex(egress.doors)}${delta}`;

      wrapper.appendChild(title);
      wrapper.appendChild(doorLine);
      wrapper.appendChild(details);
      return wrapper;
    };

    const renderResults = () => {
      results.innerHTML = "";
      results.classList.remove("animate");

      if (!selectedStation) {
        resultsTitle.textContent = "Select a station to see results.";
        resultsSub.textContent = "";
        copyBtn.disabled = true;
        return;
      }

      const lineCode = lineSelect.value || selectedStation.lines[0];
      const directionKey = directionSelect.value || selectedStation.directions[0].key;
      const directionLabel = findDirectionLabel(selectedStation, directionKey);

      resultsTitle.textContent = `${selectedStation.name} - ${lineName(lineCode)} Line`;
      resultsSub.textContent = directionLabel;
      copyBtn.disabled = false;

      const groups = [
        { key: "escalator", label: "Escalators" },
        { key: "stairs", label: "Stairs" },
        { key: "elevator", label: "Elevators" },
        { key: "other", label: "Other" },
      ];

      const egressForDir = selectedStation.egress_by_dir[directionKey] || {};

      groups.forEach((group) => {
        const block = document.createElement("div");
        block.className = "egress-block";

        const header = document.createElement("h3");
        header.textContent = group.label;
        block.appendChild(header);

        const list = egressForDir[group.key] || [];
        if (!list.length) {
          const empty = document.createElement("div");
          empty.className = "empty";
          empty.textContent = "No entries.";
          block.appendChild(empty);
        } else {
          list.forEach((egress, idx) => {
            block.appendChild(buildResultItem(egress, idx));
          });
        }

        results.appendChild(block);
      });

      results.classList.add("animate");
    };

    const selectStation = (station) => {
      selectedStation = station;
      stationInput.value = station.name;
      stationSuggestions.hidden = true;
      renderSelectors();
      renderResults();
    };

    stationInput.addEventListener("input", (event) => {
      if (selectedStation && event.target.value.toLowerCase() !== selectedStation.nameLower) {
        selectedStation = null;
        renderSelectors();
        renderResults();
      }
      const suggestions = findSuggestions(event.target.value);
      showSuggestions(suggestions);
    });

    stationInput.addEventListener("keydown", (event) => {
      if (event.key === "Enter") {
        const suggestions = findSuggestions(event.target.value);
        if (suggestions.length) {
          selectStation(suggestions[0]);
        }
      }
    });

    clearStation.addEventListener("click", () => {
      stationInput.value = "";
      selectedStation = null;
      stationSuggestions.hidden = true;
      renderSelectors();
      renderResults();
    });

    lineSelect.addEventListener("change", renderResults);
    directionSelect.addEventListener("change", renderResults);

    copyBtn.addEventListener("click", () => {
      if (!selectedStation) {
        return;
      }
      const lineCode = lineSelect.value || selectedStation.lines[0];
      const directionKey = directionSelect.value || selectedStation.directions[0].key;
      const directionLabel = findDirectionLabel(selectedStation, directionKey);
      const egressForDir = selectedStation.egress_by_dir[directionKey] || {};

      const lines = [];
      lines.push(`Station: ${selectedStation.name}`);
      lines.push(`Line: ${lineName(lineCode)} Line`);
      lines.push(`Direction: ${directionLabel}`);
      lines.push("");

      const groups = [
        { key: "escalator", label: "Escalators" },
        { key: "stairs", label: "Stairs" },
        { key: "elevator", label: "Elevators" },
        { key: "other", label: "Other" },
      ];

      groups.forEach((group) => {
        lines.push(`${group.label}:`);
        const list = egressForDir[group.key] || [];
        if (!list.length) {
          lines.push("- None");
        } else {
          list.forEach((egress, idx) => {
            const label = egress.label || `Egress ${idx + 1}`;
            const doorLabels = egress.doors.map(formatDoorLabel).join(" or ");
            const delta = egress.delta != null ? ` (delta ${egress.delta})` : "";
            const indexLabel = formatDoorIndex(egress.doors);
            lines.push(`- ${label}: ${doorLabels}, ${indexLabel}${delta}`);
          });
        }
        lines.push("");
      });

      const payload = lines.join("\n");
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(payload).catch(() => {});
      }
    });

    if ("serviceWorker" in navigator) {
      window.addEventListener("load", () => {
        navigator.serviceWorker.register("./sw.js");
      });
    }

    renderSelectors();
    renderResults();
  </script>
</body>
</html>
"""

SW_TEMPLATE = """const CACHE_VERSION = "{{CACHE_VERSION}}";
const CACHE_NAME = `metro-exit-${CACHE_VERSION}`;
const ASSETS = [
  "./",
  "./index.html",
  "./app.js",
  "./manifest.webmanifest",
  "./sw.js",
  "./icons/icon-192.svg",
  "./icons/icon-512.svg",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(ASSETS))
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) => Promise.all(
      keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))
    ))
  );
});

self.addEventListener("fetch", (event) => {
  event.respondWith(
    caches.match(event.request).then((cached) => {
      if (cached) {
        return cached;
      }
      return fetch(event.request);
    })
  );
});
"""

MANIFEST_TEMPLATE = """{
  "name": "Metro Exit Guide",
  "short_name": "Exit Guide",
  "start_url": ".",
  "display": "standalone",
  "background_color": "#f4f1e6",
  "theme_color": "#0f4c4b",
  "icons": [
    {
      "src": "./icons/icon-192.svg",
      "sizes": "192x192",
      "type": "image/svg+xml"
    },
    {
      "src": "./icons/icon-512.svg",
      "sizes": "512x512",
      "type": "image/svg+xml"
    }
  ]
}
"""

ICON_192 = """<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"192\" height=\"192\" viewBox=\"0 0 192 192\">
  <rect width=\"192\" height=\"192\" rx=\"36\" fill=\"#0f4c4b\"/>
  <rect x=\"30\" y=\"36\" width=\"132\" height=\"120\" rx=\"22\" fill=\"#f4f1e6\"/>
  <path d=\"M54 124l30-44 26 28 28-36 26 52H54z\" fill=\"#f08a24\"/>
  <circle cx=\"64\" cy=\"72\" r=\"10\" fill=\"#0f4c4b\"/>
</svg>
"""

ICON_512 = """<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"512\" height=\"512\" viewBox=\"0 0 512 512\">
  <rect width=\"512\" height=\"512\" rx=\"96\" fill=\"#0f4c4b\"/>
  <rect x=\"80\" y=\"96\" width=\"352\" height=\"320\" rx=\"56\" fill=\"#f4f1e6\"/>
  <path d=\"M144 330l88-132 76 84 82-108 74 156H144z\" fill=\"#f08a24\"/>
  <circle cx=\"170\" cy=\"188\" r=\"26\" fill=\"#0f4c4b\"/>
</svg>
"""


def fail(message):
    print(f"Error: {message}", file=sys.stderr)
    raise SystemExit(1)


def read_csv(path):
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def load_meta(path):
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


def parse_float(value, field_name, file_label):
    try:
        return float(value)
    except (TypeError, ValueError):
        fail(f"Invalid {field_name} in {file_label}: {value}")


def parse_int(value, field_name, file_label):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def is_true(value):
    return str(value).strip().upper() in {"TRUE", "T", "YES", "1"}


def build_doors(door_rows):
    entries = []
    for idx, row in enumerate(door_rows):
        car_raw = (row.get("Car") or "").strip()
        car_num = parse_int(car_raw, "Car", "Doors.csv") if car_raw else None
        x_value = parse_float(row.get("x"), "x", "Doors.csv")
        entries.append({
            "id": idx,
            "car_raw": car_raw,
            "car_num": car_num,
            "x": x_value,
        })

    car_keys = []
    for entry in entries:
        key = entry["car_num"] if entry["car_num"] is not None else entry["car_raw"]
        if key not in car_keys:
            car_keys.append(key)

    car_index_map = {}
    if all(entry["car_num"] is not None for entry in entries):
        for key in sorted(car_keys):
            car_index_map[key] = int(key)
    else:
        for order, key in enumerate(car_keys, start=1):
            car_index_map[key] = order

    by_car = defaultdict(list)
    for entry in entries:
        car_key = entry["car_num"] if entry["car_num"] is not None else entry["car_raw"]
        by_car[car_key].append(entry)

    for car_key, items in by_car.items():
        items.sort(key=lambda item: (item["x"], item["id"]))
        for door_in_car, item in enumerate(items, start=1):
            item["door_in_car"] = door_in_car
            item["car_index"] = car_index_map[car_key]

    entries.sort(key=lambda item: (item["x"], item["car_index"], item["door_in_car"]))
    for door_index, item in enumerate(entries, start=1):
        item["door_index"] = door_index

    counts = [len(items) for items in by_car.values()]
    counter = Counter(counts)
    doors_per_car = counter.most_common(1)[0][0] if counter else 0

    doors = [
        {
            "door_index": entry["door_index"],
            "car_index": entry["car_index"],
            "door_in_car": entry["door_in_car"],
            "x": round(entry["x"], 3),
        }
        for entry in entries
    ]

    meta = {
        "door_count": len(doors),
        "car_count": len(by_car),
        "doors_per_car": doors_per_car,
        "doors_per_car_min": min(counts) if counts else 0,
        "doors_per_car_max": max(counts) if counts else 0,
    }

    return doors, meta


def build_exit_map(exit_rows):
    exit_map = defaultdict(dict)
    for row in exit_rows:
        station = (row.get("nameStd") or "").strip()
        label = (row.get("exitLabel") or "").strip()
        description = (row.get("description") or "").strip()
        if station and label:
            exit_map[station][label] = description
    return exit_map


def platform_is_side(platform_type):
    platform = (platform_type or "").strip().lower()
    return platform in {"side", "gap island"}


def nearest_doors(doors, x_value, tie_threshold=0.25):
    positions = [door["x"] for door in doors]
    left = 0
    right = len(positions)
    while left < right:
        mid = (left + right) // 2
        if positions[mid] < x_value:
            left = mid + 1
        else:
            right = mid
    idx = left

    candidates = []
    if idx < len(doors):
        candidates.append(idx)
    if idx > 0:
        candidates.append(idx - 1)

    if not candidates:
        return [], None

    candidates = sorted(set(candidates))
    distances = {i: abs(positions[i] - x_value) for i in candidates}

    closest = min(candidates, key=lambda i: distances[i])
    closest_distance = distances[closest]

    if len(candidates) == 2:
        other = candidates[0] if candidates[1] == closest else candidates[1]
        if abs(distances[other] - closest_distance) <= tie_threshold:
            chosen = sorted([closest, other])
            return [doors[i] for i in chosen], round(closest_distance, 3)

    return [doors[closest]], round(closest_distance, 3)


def build_data():
    ensure_inputs_exist()

    meta = load_meta(INPUT_FILES["meta"])

    door_rows = read_csv(INPUT_FILES["doors"])
    station_rows = read_csv(INPUT_FILES["stations"])
    exit_rows = read_csv(INPUT_FILES["exits"])
    egress_rows = read_csv(INPUT_FILES["egresses"])

    if not door_rows:
        fail("Doors.csv has no data rows.")
    if not station_rows:
        fail("Stations.csv has no data rows.")
    if not egress_rows:
        fail("Egresses.csv has no data rows.")

    ensure_columns(meta, "Doors", door_rows[0].keys() if door_rows else [], REQUIRED_COLUMNS["Doors"])
    ensure_columns(meta, "Stations", station_rows[0].keys() if station_rows else [], REQUIRED_COLUMNS["Stations"])
    ensure_columns(meta, "Exits", exit_rows[0].keys() if exit_rows else [], REQUIRED_COLUMNS["Exits"])
    ensure_columns(meta, "Egresses", egress_rows[0].keys() if egress_rows else [], REQUIRED_COLUMNS["Egresses"])

    doors, door_meta = build_doors(door_rows)
    exit_map = build_exit_map(exit_rows)

    stations = []
    station_map = {}
    for row in station_rows:
        name = (row.get("nameStd") or "").strip()
        if not name:
            continue
        lines = [code for code, col in LINE_COLS.items() if is_true(row.get(col))]
        lines.sort(key=lambda code: [c[0] for c in LINE_DEFS].index(code))

        wb_dir = (row.get("WBDir") or "").strip()
        eb_dir = (row.get("EBDir") or "").strip()
        directions = [
            {
                "key": "WB",
                "label": f"Toward {wb_dir}" if wb_dir else "Direction A",
            },
            {
                "key": "EB",
                "label": f"Toward {eb_dir}" if eb_dir else "Direction B",
            },
        ]

        station = {
            "name": name,
            "alt": (row.get("nameAlt") or "").strip(),
            "subtitle": (row.get("subtitile") or "").strip(),
            "platform_type": (row.get("platformType") or "").strip(),
            "lines": lines,
            "directions": directions,
            "egress_by_dir": {
                "WB": {"escalator": [], "stairs": [], "elevator": [], "other": []},
                "EB": {"escalator": [], "stairs": [], "elevator": [], "other": []},
            },
        }
        stations.append(station)
        station_map[name] = station

    unknown_stations = set()

    for row in egress_rows:
        station_name = (row.get("nameStd") or "").strip()
        if not station_name:
            continue
        station = station_map.get(station_name)
        if station is None:
            unknown_stations.add(station_name)
            continue

        icon = (row.get("icon") or "").strip()
        egress_type = EGRESS_TYPE_MAP.get(icon, "other")
        x_value = parse_float(row.get("x"), "x", "Egresses.csv")
        y_value = (row.get("y") or "").strip()
        y_int = parse_int(y_value, "y", "Egresses.csv") if y_value else None

        exit_label = (row.get("exitLabel") or "").strip()
        exit_desc = exit_map.get(station_name, {}).get(exit_label, "")
        if exit_label and exit_desc:
            label = f"Exit {exit_label}: {exit_desc}"
        elif exit_label:
            label = f"Exit {exit_label}"
        elif exit_desc:
            label = exit_desc
        else:
            label = ""

        door_matches, delta = nearest_doors(doors, x_value)
        if not door_matches:
            continue

        egress_entry = {
            "type": egress_type,
            "label": label,
            "x": round(x_value, 3),
            "delta": delta,
            "doors": [
                {
                    "door_index": door["door_index"],
                    "car_index": door["car_index"],
                    "door_in_car": door["door_in_car"],
                }
                for door in door_matches
            ],
        }

        if platform_is_side(station["platform_type"]) and y_int in {1, 2}:
            dirs = ["EB"] if y_int == 1 else ["WB"]
        else:
            dirs = ["WB", "EB"]

        for dir_key in dirs:
            station["egress_by_dir"][dir_key][egress_type].append(egress_entry)

    if unknown_stations:
        fail(f"Egresses reference unknown stations: {', '.join(sorted(unknown_stations))}")

    for station in stations:
        for dir_key in ["WB", "EB"]:
            for egress_type in station["egress_by_dir"][dir_key]:
                station["egress_by_dir"][dir_key][egress_type].sort(
                    key=lambda item: (item["x"], item["label"])
                )

    stations.sort(key=lambda station: station["name"])

    line_defs = {
        code: {"name": name, "color": color}
        for code, name, color in LINE_DEFS
    }

    data = {
        "meta": door_meta,
        "lines": line_defs,
        "stations": stations,
    }

    data_json = json.dumps(data, ensure_ascii=True, sort_keys=True, separators=(",", ":"))

    return data, data_json


def write_file(path, content):
    path.write_text(content, encoding="utf-8")


def build_site():
    data, data_json = build_data()
    cache_seed = data_json + HTML_TEMPLATE
    cache_version = hashlib.sha1(cache_seed.encode("ascii")).hexdigest()[:10]

    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    ICONS_DIR.mkdir(parents=True, exist_ok=True)

    html = HTML_TEMPLATE.replace("{{DATA_JSON}}", data_json)
    html = html.replace("{{CACHE_VERSION}}", cache_version)

    script_pattern = re.compile(
        r'(<script id="app-data" type="application/json">.*?</script>)\s*<script>(.*?)</script>',
        re.S,
    )
    match = script_pattern.search(html)
    if not match:
        fail("Failed to extract app script from HTML template.")
    app_js = match.group(2).strip() + "\n"
    html = script_pattern.sub(r'\1\n  <script src="./app.js"></script>', html, count=1)

    write_file(DOCS_DIR / "index.html", html)
    write_file(DOCS_DIR / "app.js", app_js)

    sw_js = SW_TEMPLATE.replace("{{CACHE_VERSION}}", cache_version)
    write_file(DOCS_DIR / "sw.js", sw_js)

    write_file(DOCS_DIR / "manifest.webmanifest", MANIFEST_TEMPLATE)
    write_file(ICONS_DIR / "icon-192.svg", ICON_192)
    write_file(ICONS_DIR / "icon-512.svg", ICON_512)

    return data


if __name__ == "__main__":
    build_site()
