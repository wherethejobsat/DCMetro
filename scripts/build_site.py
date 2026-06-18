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

STATION_REFERENCE_TRANSLATION = str.maketrans(
    {
        "\u2018": "'",
        "\u2019": "'",
        "\u201b": "'",
        "\u2032": "'",
        "\uff07": "'",
        "\u02bc": "'",
    }
)
AMBIGUOUS_STATION_REFERENCE = object()
MISSING_STATION_REFERENCE = object()


def normalize_station_reference(value):
    cleaned = (value or "").strip().translate(STATION_REFERENCE_TRANSLATION)
    return " ".join(cleaned.split())


def add_station_reference(lookup, reference_name, station_name):
    key = normalize_station_reference(reference_name)
    if not key:
        return
    existing = lookup.get(key, MISSING_STATION_REFERENCE)
    if existing is MISSING_STATION_REFERENCE:
        lookup[key] = station_name
    elif existing is AMBIGUOUS_STATION_REFERENCE:
        return
    elif existing != station_name:
        lookup[key] = AMBIGUOUS_STATION_REFERENCE


def build_station_reference_lookup(station_rows):
    lookup = {}
    for row in station_rows:
        station_name = (row.get("nameStd") or "").strip()
        if not station_name:
            continue
        add_station_reference(lookup, station_name, station_name)
        add_station_reference(lookup, row.get("nameAlt"), station_name)
    return lookup


def resolve_station_reference(station_name, station_lookup, file_label):
    raw_station_name = (station_name or "").strip()
    if not raw_station_name:
        return ""
    resolved = station_lookup.get(normalize_station_reference(raw_station_name))
    if resolved is None:
        fail(f"{file_label} references unknown station: {raw_station_name}")
    if resolved is AMBIGUOUS_STATION_REFERENCE:
        fail(f"{file_label} has ambiguous station reference: {raw_station_name}")
    return resolved


# WMATA rail station codes used by public APIs. Split-level transfer rows use
# the code for the level that serves that row's lines.
WMATA_STATION_CODES = {
    "Addison Road": "G03",
    "Anacostia": "F06",
    "Archives": "F02",
    "Arlington Cemetery": "C06",
    "Ashburn": "N12",
    "Ballston-MU": "K04",
    "Benning Road": "G01",
    "Bethesda": "A09",
    "Braddock Road": "C12",
    "Branch Avenue": "F11",
    "Brookland-CUA": "B05",
    "Capitol Heights": "G02",
    "Capitol South": "D05",
    "Cheverly": "D11",
    "Clarendon": "K02",
    "Cleveland Park": "A05",
    "College Park-U of Md": "E09",
    "Columbia Heights": "E04",
    "Congress Heights": "F07",
    "Court House": "K01",
    "Crystal City": "C09",
    "Deanwood": "D10",
    "Downtown Largo": "G05",
    "Dunn Loring": "K07",
    "Dupont Circle": "A03",
    "East Falls Church": "K05",
    "Eastern Market": "D06",
    "Eisenhower Avenue": "C14",
    "Farragut North": "A02",
    "Farragut West": "C03",
    "Federal Center SW": "D04",
    "Federal Triangle": "D01",
    "Foggy Bottom-GWU": "C04",
    "Forest Glen": "B09",
    "Fort Totten (Lower Level)": "E06",
    "Fort Totten (Upper Level)": "B06",
    "Franconia-Springfield": "J03",
    "Friendship Heights": "A08",
    "Gallery Place (Lower Level)": "F01",
    "Gallery Place (Upper Level)": "B01",
    "Georgia Avenue-Petworth": "E05",
    "Glenmont": "B11",
    "Greenbelt": "E10",
    "Greensboro": "N03",
    "Grosvenor-Strathmore": "A11",
    "Herndon": "N08",
    "Huntington": "C15",
    "Hyattsville Crossing": "E08",
    "Innovation Center": "N09",
    "Judiciary Square": "B02",
    "King Street-Old Town": "C13",
    "L'Enfant Plaza (Lower Level)": "D03",
    "L'Enfant Plaza (Upper Level)": "F03",
    "Landover": "D12",
    "Loudoun Gateway": "N11",
    "McLean": "N01",
    "McPherson Square": "C02",
    "Medical Center": "A10",
    "Metro Center (Lower Level)": "C01",
    "Metro Center (Upper Level)": "A01",
    "Minnesota Avenue": "D09",
    "Morgan Boulevard": "G04",
    "Mount Vernon Square": "E01",
    "Navy Yard-Ballpark": "F05",
    "Naylor Road": "F09",
    "New Carrollton": "D13",
    "NoMa-Gallaudet U": "B35",
    "North Bethesda": "A12",
    "Pentagon": "C07",
    "Pentagon City": "C08",
    "Potomac Avenue": "D07",
    "Potomac Yard": "C11",
    "Reston Town Center": "N07",
    "Rhode Island Avenue": "B04",
    "Rockville": "A14",
    "Rosslyn": "C05",
    "Shady Grove": "A15",
    "Shaw-Howard U": "E02",
    "Silver Spring": "B08",
    "Smithsonian": "D02",
    "Southern Avenue": "F08",
    "Spring Hill": "N04",
    "Stadium-Armory": "D08",
    "Suitland": "F10",
    "Takoma": "B07",
    "Tenleytown-AU": "A07",
    "Twinbrook": "A13",
    "Tysons": "N02",
    "U Street": "E03",
    "Union Station": "B03",
    "Van Dorn Street": "J02",
    "Van Ness-UDC": "A06",
    "Vienna": "K08",
    "Virginia Square-GMU": "K03",
    "Washington Dulles International Airport": "N10",
    "Washington National Airport": "C10",
    "Waterfront": "F04",
    "West Falls Church": "K06",
    "West Hyattsville": "E07",
    "Wheaton": "B10",
    "Wiehle-Reston East": "N06",
    "Woodley Park": "A04",
}

EGRESS_TYPE_MAP = {
    "esc": "escalator",
    "el": "elevator",
    "stair": "stairs",
}

ACCESS_LABELS = {
    "elevator": "Elevator",
    "escalator": "Escalator",
    "other": "Path",
    "stairs": "Stairs",
}

REVERSE_DOORS_FOR_DIR = "EB"
LEVEL_SUFFIX_RE = re.compile(r" \((Lower|Upper) Level\)$")
TRANSFER_LINE_RE = re.compile(
    r"\b(?:All\s+)?((?:RD|GR|YL|BL|OR|SV)(?:/(?:RD|GR|YL|BL|OR|SV))*)\s+Trains\b"
)
TRANSFER_TOWARD_RE = re.compile(r"\bTrains to ([^,]+)")

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
  <meta name=\"theme-color\" content=\"#111722\">
  <meta name=\"description\" content=\"A fast, offline-friendly DC Metro exit guide that shows the train car and door closest to station exits.\">
  <meta property=\"og:title\" content=\"DC Metro Exit Guide\">
  <meta property=\"og:description\" content=\"Find the right car and door before you board. Works offline after first load.\">
  <meta property=\"og:type\" content=\"website\">
  <meta property=\"og:url\" content=\"https://wherethejobsat.github.io/DCMetro/\">
  <meta property=\"og:image\" content=\"https://wherethejobsat.github.io/DCMetro/social-preview.svg\">
  <meta name=\"twitter:card\" content=\"summary_large_image\">
  <link rel=\"manifest\" href=\"./manifest.webmanifest\">
  <title>DC Metro Exit Guide</title>
  <style>
    :root {
      --font-sans: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      --font-serif: ui-serif, Georgia, Cambria, "Times New Roman", serif;
      --bg: #111722;
      --ink: #f3efe6;
      --muted: #b9c0cc;
      --card: #182131;
      --accent: #8fb9dc;
      --accent-warm: #e0a15f;
      --accent-soft: #202a3b;
      --border: #334155;
      --on-accent: #111722;
      --shadow: 0 12px 34px rgba(0, 0, 0, 0.32);
      --radius: 8px;
    }

    * {
      box-sizing: border-box;
    }

    body {
      margin: 0;
      min-height: 100vh;
      font-family: var(--font-sans);
      line-height: 1.6;
      color: var(--ink);
      background:
        linear-gradient(90deg, rgba(143, 185, 220, 0.08) 1px, transparent 1px),
        linear-gradient(180deg, rgba(224, 161, 95, 0.05) 1px, transparent 1px),
        var(--bg);
      background-size: 72px 72px, 72px 72px, auto;
    }

    header {
      padding: 24px 20px 8px;
      text-align: left;
    }

    header h1 {
      margin: 0 0 6px;
      font-family: var(--font-serif);
      font-size: 1.6rem;
      letter-spacing: 0;
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
      border: 1px solid var(--border);
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

    [hidden] {
      display: none !important;
    }

    input, select, button {
      width: 100%;
      min-height: 44px;
      border-radius: var(--radius);
      border: 1px solid var(--border);
      padding: 10px 12px;
      font-size: 1rem;
      font-family: inherit;
      background: var(--card);
      color: var(--ink);
    }

    input:focus, select:focus, button:focus {
      outline: 3px solid rgba(224, 161, 95, 0.4);
      outline-offset: 3px;
    }

    .static-select {
      width: 100%;
      min-height: 44px;
      border-radius: var(--radius);
      border: 1px solid var(--border);
      padding: 10px 12px;
      background: var(--accent-soft);
      color: var(--ink);
      display: flex;
      align-items: center;
      font-size: 1rem;
      font-weight: 700;
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
      border-color: var(--border);
      color: var(--accent);
      cursor: pointer;
      font-weight: 600;
    }

    .suggestions {
      margin-top: 8px;
      border-radius: var(--radius);
      overflow: hidden;
      border: 1px solid var(--border);
      background: var(--card);
    }

    .suggestions button {
      border: none;
      border-bottom: 1px solid var(--border);
      text-align: left;
      width: 100%;
      padding: 12px 14px;
      background: var(--card);
      cursor: pointer;
    }

    .suggestions button:last-child {
      border-bottom: none;
    }

    .quick-examples {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-top: 10px;
    }

    .example-btn {
      width: auto;
      min-height: 40px;
      padding: 8px 10px;
      background: var(--accent-soft);
      color: var(--accent);
      border-color: var(--border);
      cursor: pointer;
      font-weight: 600;
    }

    .helper {
      margin: 6px 0 0;
      color: var(--muted);
      font-size: 0.85rem;
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
      color: var(--ink);
      background: var(--accent-soft);
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
      color: var(--on-accent);
      border: none;
      font-weight: 700;
      cursor: pointer;
    }

    .copy-wrap {
      display: grid;
      gap: 6px;
    }

    .copy-feedback {
      min-height: 1.2em;
      color: var(--muted);
      font-size: 0.85rem;
      text-align: right;
    }

    .notice {
      margin: 0 0 14px;
      color: var(--muted);
      font-size: 0.88rem;
      border-left: 3px solid var(--accent-warm);
      padding-left: 10px;
    }

    .egress-block {
      margin-bottom: 16px;
      animation: fadeIn 0.6s ease both;
    }

    .egress-block h3 {
      margin: 0 0 8px;
      font-size: 1.1rem;
      font-family: var(--font-serif);
    }

    .egress-item {
      background: var(--accent-soft);
      border-radius: var(--radius);
      padding: 12px 14px;
      margin-bottom: 8px;
      border: 1px solid var(--border);
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

    .about a {
      color: var(--accent);
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
    <h1>DC Metro Exit Guide</h1>
    <p>Pick a station, line, and direction to see the closest car and door.</p>
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
        <p class=\"helper\">Try one:</p>
        <div class=\"quick-examples\" aria-label=\"Example stations\">
          <button class=\"example-btn\" type=\"button\" data-station-example=\"Metro Center (Upper Level)\">Metro Center (Upper Level)</button>
          <button class=\"example-btn\" type=\"button\" data-station-example=\"Rosslyn\">Rosslyn</button>
          <button class=\"example-btn\" type=\"button\" data-station-example=\"Anacostia\">Anacostia</button>
        </div>
      </div>
      <div class=\"field\">
        <label id=\"lineLabel\" for=\"lineSelect\">Line</label>
        <select id=\"lineSelect\" disabled></select>
        <div id=\"lineStatic\" class=\"static-select\" aria-labelledby=\"lineLabel\" hidden></div>
        <div id=\"lineTags\" class=\"tags\"></div>
      </div>
      <div class=\"field\">
        <label for=\"directionSelect\">Direction</label>
        <select id=\"directionSelect\" disabled></select>
        <p id=\"platformNote\" class=\"helper\" hidden></p>
      </div>
    </section>

    <section class=\"card\">
      <div class=\"results-header\">
        <div>
          <div id=\"resultsTitle\" class=\"meta\">Select a station to see results.</div>
          <div id=\"resultsSub\" class=\"meta\"></div>
        </div>
        <div class=\"copy-wrap\">
          <button id=\"copyBtn\" class=\"copy-btn\" type=\"button\" disabled>Copy</button>
          <div id=\"copyFeedback\" class=\"copy-feedback\" aria-live=\"polite\"></div>
        </div>
      </div>
      <div id=\"results\"></div>
    </section>

    <section class=\"card\">
      <h2>About</h2>
      <p class=\"about\">
        Uses the 2025 Metro Station Platform Exit Guide data. Works offline after first load.
        No account, no ads, no tracking. Not affiliated with, endorsed by, or maintained by WMATA.
        <a href=\"https://github.com/wherethejobsat/DCMetro\">Source on GitHub</a>.
        <a href=\"https://github.com/wherethejobsat/DCMetro/issues/new\">Report a station correction</a>.
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
    const lineStatic = document.getElementById("lineStatic");
    const directionSelect = document.getElementById("directionSelect");
    const results = document.getElementById("results");
    const resultsTitle = document.getElementById("resultsTitle");
    const resultsSub = document.getElementById("resultsSub");
    const copyBtn = document.getElementById("copyBtn");
    const copyFeedback = document.getElementById("copyFeedback");
    const lineTags = document.getElementById("lineTags");
    const platformNote = document.getElementById("platformNote");
    const exampleButtons = document.querySelectorAll("[data-station-example]");

    let selectedStation = null;
    let copyFeedbackTimer = null;
    const SHARED_PLATFORM_NOTE = "At shared-platform stations, recommendations are based on platform direction; changing line may not change the result.";

    const normalize = (value) => String(value || "")
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, " ")
      .trim();

    const stations = DATA.stations.map((station) => {
      const tokens = [
        station.name,
        station.alt || "",
        station.subtitle || "",
        station.station_code || "",
      ].join(" ");
      return {
        ...station,
        search: normalize(tokens),
        nameLower: station.name.toLowerCase(),
        altLower: (station.alt || "").toLowerCase(),
        codeLower: (station.station_code || "").toLowerCase(),
      };
    });

    const lineName = (code) => (DATA.lines[code] ? DATA.lines[code].name : code);

    const levelLineHint = (station) => {
      if (!/\\((Lower|Upper) Level\\)$/.test(station.name)) {
        return "";
      }
      return ` [${station.lines.map(lineName).join(", ")}]`;
    };

    const baseStationName = (station) => station.name.replace(/ \\((Lower|Upper) Level\\)$/, "");

    const findLineCode = (station, value) => {
      const requested = normalize(value);
      if (!station || !requested) {
        return "";
      }
      return station.lines.find((code) => (
        normalize(code) === requested || normalize(lineName(code)) === requested
      )) || "";
    };

    const findDirectionKey = (station, value) => {
      const requested = normalize(value);
      if (!station || !requested) {
        return "";
      }
      const match = station.directions.find((dir) => (
        normalize(dir.key) === requested ||
        normalize(dir.label) === requested ||
        normalize(dir.label.replace(/^Toward\\s+/i, "")) === requested
      ));
      return match ? match.key : "";
    };

    const stationMatchScore = (station, value) => {
      const requested = normalize(value);
      if (!requested) {
        return 0;
      }
      const aliases = [
        { value: station.name, score: 6 },
        { value: station.station_code, score: 6 },
        { value: baseStationName(station), score: 5 },
        { value: station.alt, score: 4 },
        { value: station.subtitle, score: 3 },
      ];
      const exact = aliases.find((alias) => normalize(alias.value) === requested);
      if (exact) {
        return exact.score;
      }
      if (station.search.includes(requested)) {
        return 1;
      }
      return 0;
    };

    const findStationByParam = (stationValue, lineValue) => {
      const matches = stations
        .map((station) => ({ station, score: stationMatchScore(station, stationValue) }))
        .filter((entry) => entry.score > 0);
      if (!matches.length) {
        return null;
      }

      const lineMatches = lineValue
        ? matches.filter((entry) => findLineCode(entry.station, lineValue))
        : [];
      const candidates = lineMatches.length ? lineMatches : matches;
      candidates.sort((a, b) => {
        if (b.score !== a.score) {
          return b.score - a.score;
        }
        return a.station.name.localeCompare(b.station.name);
      });
      return candidates[0].station;
    };

    const renderLineTags = (station) => {
      lineTags.innerHTML = "";
      if (!station) {
        return;
      }
      station.lines.forEach((code) => {
        const tag = document.createElement("span");
        tag.className = "tag";
        tag.style.background = DATA.lines[code] ? DATA.lines[code].color : "#202a3b";
        tag.style.color = ["RD", "BL"].includes(code) ? "#fff" : "#111";
        tag.textContent = lineName(code);
        lineTags.appendChild(tag);
      });
    };

    const buildSuggestionButton = (station) => {
      const button = document.createElement("button");
      const subtitle = station.subtitle ? ` - ${station.subtitle}` : "";
      button.textContent = `${station.name}${levelLineHint(station)}${subtitle}`;
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
        if (station.codeLower && station.codeLower.startsWith(query.toLowerCase())) {
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

    const hasSharedPlatformLineChoice = (station) => {
      return Boolean(station && station.lines.length > 1);
    };

    const showLineDropdown = () => {
      lineSelect.hidden = false;
      lineStatic.hidden = true;
      lineStatic.textContent = "";
    };

    const showStaticLine = (lineCode) => {
      lineSelect.hidden = true;
      lineSelect.disabled = true;
      lineStatic.textContent = lineCode ? `${lineName(lineCode)} Line` : "";
      lineStatic.hidden = false;
    };

    const directionOptionsForLine = (station, lineCode) => {
      // The source data gives platform direction geometry. At shared-platform
      // stations, a selected line labels the trip, but it does not create a
      // separate line-specific door recommendation.
      const sharedPlatform = hasSharedPlatformLineChoice(station);
      return station.directions.map((dir) => ({
        value: dir.key,
        label: sharedPlatform ? `${dir.label} (platform direction)` : dir.label,
      }));
    };

    const renderPlatformNote = () => {
      if (!hasSharedPlatformLineChoice(selectedStation)) {
        platformNote.textContent = "";
        platformNote.hidden = true;
        return;
      }
      platformNote.textContent = SHARED_PLATFORM_NOTE;
      platformNote.hidden = false;
    };

    const renderDirectionSelector = (preferredDirection) => {
      const lineCode = lineSelect.value || selectedStation.lines[0] || "";
      const dirOptions = directionOptionsForLine(selectedStation, lineCode);
      fillSelect(directionSelect, dirOptions, "Select a direction");
      directionSelect.disabled = false;
      const requestedDirection = findDirectionKey(selectedStation, preferredDirection);
      directionSelect.value = requestedDirection || (dirOptions.length ? dirOptions[0].value : "");
      renderPlatformNote();
    };

    const renderSelectors = (preferredLine, preferredDirection) => {
      if (!selectedStation) {
        lineSelect.disabled = true;
        directionSelect.disabled = true;
        showLineDropdown();
        fillSelect(lineSelect, [], "Select a station first");
        fillSelect(directionSelect, [], "Select a station first");
        renderLineTags(null);
        renderPlatformNote();
        return;
      }

      const lineOptions = selectedStation.lines.map((code) => ({
        value: code,
        label: `${lineName(code)} Line`,
      }));

      const requestedLine = findLineCode(selectedStation, preferredLine);
      const selectedLine = requestedLine || (lineOptions.length ? lineOptions[0].value : "");

      fillSelect(
        lineSelect,
        lineOptions,
        selectedStation.lines.length > 1 ? "Select a line" : ""
      );
      lineSelect.value = selectedLine;
      if (selectedStation.lines.length === 1) {
        showStaticLine(selectedLine);
      } else {
        showLineDropdown();
        lineSelect.disabled = false;
      }

      renderDirectionSelector(preferredDirection);

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
      if (egress.note) {
        const note = document.createElement("div");
        note.className = "muted";
        note.textContent = egress.note;
        wrapper.appendChild(note);
      }
      wrapper.appendChild(doorLine);
      wrapper.appendChild(details);
      return wrapper;
    };

    const clearCopyFeedback = () => {
      if (copyFeedbackTimer) {
        window.clearTimeout(copyFeedbackTimer);
        copyFeedbackTimer = null;
      }
      copyFeedback.textContent = "";
    };

    const showCopyFeedback = (message) => {
      copyFeedback.textContent = message;
      if (copyFeedbackTimer) {
        window.clearTimeout(copyFeedbackTimer);
      }
      copyFeedbackTimer = window.setTimeout(() => {
        copyFeedback.textContent = "";
        copyFeedbackTimer = null;
      }, 2500);
    };

    const updateUrlFromSelection = () => {
      if (!window.history || !window.history.replaceState) {
        return;
      }
      const params = new URLSearchParams();
      if (selectedStation) {
        params.set("station", selectedStation.name);
        if (lineSelect.value) {
          params.set("line", lineSelect.value);
        }
        if (directionSelect.value) {
          params.set("direction", directionSelect.value);
        }
      }
      const query = params.toString();
      const nextUrl = `${window.location.pathname}${query ? `?${query}` : ""}${window.location.hash}`;
      window.history.replaceState(null, "", nextUrl);
    };

    const renderResults = (options = {}) => {
      const shouldUpdateUrl = options.updateUrl !== false;
      results.innerHTML = "";
      results.classList.remove("animate");
      clearCopyFeedback();

      if (!selectedStation) {
        resultsTitle.textContent = "Select a station to see results.";
        resultsSub.textContent = "";
        copyBtn.disabled = true;
        if (shouldUpdateUrl) {
          updateUrlFromSelection();
        }
        return;
      }

      const lineCode = lineSelect.value || selectedStation.lines[0];
      const directionKey = directionSelect.value || selectedStation.directions[0].key;
      const directionLabel = findDirectionLabel(selectedStation, directionKey);

      resultsTitle.textContent = `${selectedStation.name} - ${lineName(lineCode)} Line`;
      resultsSub.textContent = directionLabel;
      copyBtn.disabled = false;

      const transfersForDir = selectedStation.transfers_by_dir
        ? (selectedStation.transfers_by_dir[directionKey] || [])
        : [];
      const groups = [
        { key: "transfers", label: "Transfers", list: transfersForDir },
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

        const list = group.list || egressForDir[group.key] || [];
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
      if (shouldUpdateUrl) {
        updateUrlFromSelection();
      }
    };

    const selectStation = (station, options = {}) => {
      if (!station) {
        return false;
      }
      selectedStation = station;
      stationInput.value = station.name;
      stationSuggestions.hidden = true;
      renderSelectors(options.line, options.direction);
      renderResults({ updateUrl: options.updateUrl !== false });
      return true;
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

    lineSelect.addEventListener("change", () => {
      renderDirectionSelector(directionSelect.value);
      renderResults();
    });
    directionSelect.addEventListener("change", () => {
      renderResults();
    });

    exampleButtons.forEach((button) => {
      button.addEventListener("click", () => {
        const station = findStationByParam(button.dataset.stationExample || "", "");
        if (station) {
          selectStation(station);
        }
      });
    });

    const buildCopyPayload = () => {
      if (!selectedStation) {
        return "";
      }
      const lineCode = lineSelect.value || selectedStation.lines[0];
      const directionKey = directionSelect.value || selectedStation.directions[0].key;
      const directionLabel = findDirectionLabel(selectedStation, directionKey);
      const egressForDir = selectedStation.egress_by_dir[directionKey] || {};
      const transfersForDir = selectedStation.transfers_by_dir
        ? (selectedStation.transfers_by_dir[directionKey] || [])
        : [];

      const lines = [];
      lines.push(`Station: ${selectedStation.name}`);
      lines.push(`Line: ${lineName(lineCode)} Line`);
      lines.push(`Direction: ${directionLabel}`);
      lines.push("");

      const groups = [
        { key: "transfers", label: "Transfers", list: transfersForDir },
        { key: "escalator", label: "Escalators" },
        { key: "stairs", label: "Stairs" },
        { key: "elevator", label: "Elevators" },
        { key: "other", label: "Other" },
      ];

      groups.forEach((group) => {
        lines.push(`${group.label}:`);
        const list = group.list || egressForDir[group.key] || [];
        if (!list.length) {
          lines.push("- None");
        } else {
          list.forEach((egress, idx) => {
            const label = egress.label || `Egress ${idx + 1}`;
            const doorLabels = egress.doors.map(formatDoorLabel).join(" or ");
            const delta = egress.delta != null ? ` (delta ${egress.delta})` : "";
            const indexLabel = formatDoorIndex(egress.doors);
            const note = egress.note ? `; ${egress.note}` : "";
            lines.push(`- ${label}: ${doorLabels}, ${indexLabel}${delta}${note}`);
          });
        }
        lines.push("");
      });

      return lines.join("\\n");
    };

    copyBtn.addEventListener("click", async () => {
      const payload = buildCopyPayload();
      if (!payload) {
        return;
      }
      if (!navigator.clipboard || !navigator.clipboard.writeText) {
        showCopyFeedback("Copy failed; select and copy the text manually.");
        return;
      }
      try {
        await navigator.clipboard.writeText(payload);
        showCopyFeedback("Copied.");
      } catch (error) {
        showCopyFeedback("Copy failed; select and copy the text manually.");
      }
    });

    if ("serviceWorker" in navigator) {
      let refreshingForUpdate = false;
      const reloadOnControllerChange = Boolean(navigator.serviceWorker.controller);

      navigator.serviceWorker.addEventListener("controllerchange", () => {
        if (!reloadOnControllerChange || refreshingForUpdate) {
          return;
        }
        refreshingForUpdate = true;
        window.location.reload();
      });

      window.addEventListener("load", () => {
        navigator.serviceWorker.register("./sw.js").then((registration) => {
          registration.update();
        }).catch(() => {});
      });
    }

    const initFromUrl = () => {
      const params = new URLSearchParams(window.location.search);
      const stationParam = params.get("station");
      if (!stationParam) {
        return false;
      }
      const lineParam = params.get("line");
      const station = findStationByParam(stationParam, lineParam);
      if (!station) {
        return false;
      }
      return selectStation(station, {
        line: lineParam,
        direction: params.get("direction"),
        updateUrl: true,
      });
    };

    if (!initFromUrl()) {
      renderSelectors();
      renderResults({ updateUrl: false });
    }
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
  "./social-preview.svg",
  "./icons/icon-192.svg",
  "./icons/icon-512.svg",
];

self.addEventListener("install", (event) => {
  self.skipWaiting();
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(ASSETS))
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(
        keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))
      ))
      .then(() => self.clients.claim())
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
  "name": "DC Metro Exit Guide",
  "short_name": "DC Exit Guide",
  "start_url": ".",
  "display": "standalone",
  "background_color": "#111722",
  "theme_color": "#111722",
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
  <rect width=\"192\" height=\"192\" rx=\"36\" fill=\"#111722\"/>
  <rect x=\"30\" y=\"36\" width=\"132\" height=\"120\" rx=\"22\" fill=\"#182131\"/>
  <path d=\"M54 124l30-44 26 28 28-36 26 52H54z\" fill=\"#e0a15f\"/>
  <circle cx=\"64\" cy=\"72\" r=\"10\" fill=\"#8fb9dc\"/>
</svg>
"""

ICON_512 = """<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"512\" height=\"512\" viewBox=\"0 0 512 512\">
  <rect width=\"512\" height=\"512\" rx=\"96\" fill=\"#111722\"/>
  <rect x=\"80\" y=\"96\" width=\"352\" height=\"320\" rx=\"56\" fill=\"#182131\"/>
  <path d=\"M144 330l88-132 76 84 82-108 74 156H144z\" fill=\"#e0a15f\"/>
  <circle cx=\"170\" cy=\"188\" r=\"26\" fill=\"#8fb9dc\"/>
</svg>
"""

SOCIAL_PREVIEW = """<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"1200\" height=\"630\" viewBox=\"0 0 1200 630\" role=\"img\" aria-labelledby=\"title desc\">
  <title id=\"title\">DC Metro Exit Guide</title>
  <desc id=\"desc\">Preview card showing station, line, direction, and a car-door result.</desc>
  <rect width=\"1200\" height=\"630\" fill=\"#111722\"/>
  <path d=\"M0 126H1200M0 252H1200M0 378H1200M0 504H1200\" stroke=\"#223149\" stroke-width=\"2\"/>
  <path d=\"M120 0V630M240 0V630M360 0V630M480 0V630M600 0V630M720 0V630M840 0V630M960 0V630M1080 0V630\" stroke=\"#1b2638\" stroke-width=\"2\"/>
  <rect x=\"86\" y=\"76\" width=\"1028\" height=\"478\" rx=\"28\" fill=\"#182131\" stroke=\"#334155\" stroke-width=\"3\"/>
  <text x=\"126\" y=\"158\" fill=\"#f3efe6\" font-family=\"Arial, Helvetica, sans-serif\" font-size=\"64\" font-weight=\"700\">DC Metro Exit Guide</text>
  <text x=\"128\" y=\"214\" fill=\"#b9c0cc\" font-family=\"Arial, Helvetica, sans-serif\" font-size=\"30\">Find the right car and door before you board</text>
  <g transform=\"translate(128 278)\">
    <rect width=\"944\" height=\"166\" rx=\"18\" fill=\"#202a3b\" stroke=\"#41516a\" stroke-width=\"2\"/>
    <text x=\"34\" y=\"54\" fill=\"#8fb9dc\" font-family=\"Arial, Helvetica, sans-serif\" font-size=\"28\" font-weight=\"700\">Station</text>
    <text x=\"34\" y=\"102\" fill=\"#f3efe6\" font-family=\"Arial, Helvetica, sans-serif\" font-size=\"40\">Metro Center</text>
    <circle cx=\"402\" cy=\"82\" r=\"28\" fill=\"#c60c30\"/>
    <text x=\"402\" y=\"94\" text-anchor=\"middle\" fill=\"#ffffff\" font-family=\"Arial, Helvetica, sans-serif\" font-size=\"28\" font-weight=\"700\">RD</text>
    <text x=\"460\" y=\"72\" fill=\"#b9c0cc\" font-family=\"Arial, Helvetica, sans-serif\" font-size=\"25\">Toward Shady Grove</text>
    <text x=\"460\" y=\"112\" fill=\"#f3efe6\" font-family=\"Arial, Helvetica, sans-serif\" font-size=\"32\">Car 4, Door 2</text>
    <rect x=\"716\" y=\"42\" width=\"190\" height=\"80\" rx=\"14\" fill=\"#e0a15f\"/>
    <text x=\"811\" y=\"92\" text-anchor=\"middle\" fill=\"#111722\" font-family=\"Arial, Helvetica, sans-serif\" font-size=\"28\" font-weight=\"700\">Door 11</text>
  </g>
  <text x=\"128\" y=\"505\" fill=\"#b9c0cc\" font-family=\"Arial, Helvetica, sans-serif\" font-size=\"24\">Offline after first load. No account. No ads. No tracking.</text>
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


def build_exit_map(exit_rows, station_lookup):
    exit_map = defaultdict(dict)
    for row in exit_rows:
        station = resolve_station_reference(
            row.get("nameStd"),
            station_lookup,
            "Exits.csv",
        )
        label = (row.get("exitLabel") or "").strip()
        description = (row.get("description") or "").strip()
        if station and label:
            exit_map[station][label] = description
    return exit_map


def platform_is_side(platform_type):
    platform = (platform_type or "").strip().lower()
    return platform in {"side", "gap island"}


def base_station_name(station_name):
    return LEVEL_SUFFIX_RE.sub("", station_name)


def is_split_level_station(station_name):
    return bool(LEVEL_SUFFIX_RE.search(station_name))


def line_order_index(line_code):
    return [code for code, _name, _color in LINE_DEFS].index(line_code)


def format_line_group(line_codes):
    names = [name for code, name, _color in LINE_DEFS if code in set(line_codes)]
    if not names:
        return ""
    suffix = "Line" if len(names) == 1 else "Lines"
    return f"{'/'.join(names)} {suffix}"


def transfer_target_lines(description):
    match = TRANSFER_LINE_RE.search(description or "")
    if not match:
        return []
    codes = [code for code in match.group(1).split("/") if code in LINE_COLS]
    return sorted(set(codes), key=line_order_index)


def transfer_label_parts(description, target_lines, egress_type):
    line_group = format_line_group(target_lines)
    label = f"To {line_group}" if line_group else "Transfer"
    toward = TRANSFER_TOWARD_RE.search(description or "")
    if toward:
        label = f"{label} toward {toward.group(1).strip()}"

    note_parts = [ACCESS_LABELS.get(egress_type, "Path")]
    if "," in description:
        note_parts.append(description.split(",", 1)[1].strip())
    return label, ". ".join(part for part in note_parts if part)


def has_transfer_entries(station):
    return any(station["transfers_by_dir"][dir_key] for dir_key in ("WB", "EB"))


def copy_transfer_entry(source, label, note, target_lines):
    return {
        "type": source["type"],
        "label": label,
        "note": note,
        "target_lines": target_lines,
        "x": source["x"],
        "delta": source["delta"],
        "doors": source["doors"],
    }


def add_split_level_transfer_fallbacks(stations):
    by_base_name = defaultdict(list)
    for station in stations:
        if is_split_level_station(station["name"]):
            by_base_name[base_station_name(station["name"])].append(station)

    for level_stations in by_base_name.values():
        if len(level_stations) < 2:
            continue
        for station in level_stations:
            if has_transfer_entries(station):
                continue
            target_lines = sorted(
                {
                    line
                    for other in level_stations
                    if other is not station
                    for line in other["lines"]
                },
                key=line_order_index,
            )
            if not target_lines:
                continue
            label = f"To {format_line_group(target_lines)}"
            for dir_key in ("WB", "EB"):
                for egress_type in ("stairs", "escalator", "elevator"):
                    for source in station["egress_by_dir"][dir_key][egress_type]:
                        note = ACCESS_LABELS.get(egress_type, "Path")
                        station["transfers_by_dir"][dir_key].append(
                            copy_transfer_entry(source, label, note, target_lines)
                        )


def sort_transfer_entries(station):
    for dir_key in ("WB", "EB"):
        station["transfers_by_dir"][dir_key].sort(
            key=lambda item: (
                [line_order_index(code) for code in item["target_lines"]],
                item["x"],
                item["label"],
                item.get("note", ""),
            )
        )


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
    door_by_index = {door["door_index"]: door for door in doors}
    total_doors = len(doors)

    station_names = {
        (row.get("nameStd") or "").strip()
        for row in station_rows
        if (row.get("nameStd") or "").strip()
    }
    station_lookup = build_station_reference_lookup(station_rows)
    exit_map = build_exit_map(exit_rows, station_lookup)
    missing_station_codes = sorted(station_names - set(WMATA_STATION_CODES))
    if missing_station_codes:
        fail(f"Missing WMATA station codes: {', '.join(missing_station_codes)}")

    extra_station_codes = sorted(set(WMATA_STATION_CODES) - station_names)
    if extra_station_codes:
        fail(f"WMATA station code map has unknown stations: {', '.join(extra_station_codes)}")

    stations = []
    station_map = {}
    for row in station_rows:
        name = (row.get("nameStd") or "").strip()
        if not name:
            continue
        station_code = WMATA_STATION_CODES[name]
        if not re.fullmatch(r"[A-Z][0-9]{2}", station_code):
            fail(f"Invalid WMATA station code for {name}: {station_code}")
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
            "station_code": station_code,
            "alt": (row.get("nameAlt") or "").strip(),
            "subtitle": (row.get("subtitile") or "").strip(),
            "platform_type": (row.get("platformType") or "").strip(),
            "lines": lines,
            "directions": directions,
            "egress_by_dir": {
                "WB": {"escalator": [], "stairs": [], "elevator": [], "other": []},
                "EB": {"escalator": [], "stairs": [], "elevator": [], "other": []},
            },
            "transfers_by_dir": {
                "WB": [],
                "EB": [],
            },
        }
        stations.append(station)
        station_map[name] = station

    for row in egress_rows:
        station_name = resolve_station_reference(
            row.get("nameStd"),
            station_lookup,
            "Egresses.csv",
        )
        if not station_name:
            continue
        station = station_map.get(station_name)

        icon = (row.get("icon") or "").strip()
        egress_type = EGRESS_TYPE_MAP.get(icon, "other")
        x_value = parse_float(row.get("x"), "x", "Egresses.csv")
        y_value = (row.get("y") or "").strip()
        y_int = parse_int(y_value, "y", "Egresses.csv") if y_value else None

        exit_label = (row.get("exitLabel") or "").strip()
        exit_desc = exit_map.get(station_name, {}).get(exit_label, "")
        target_lines = transfer_target_lines(exit_desc)
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

        if platform_is_side(station["platform_type"]) and y_int in {1, 2}:
            dirs = ["EB"] if y_int == 1 else ["WB"]
        else:
            dirs = ["WB", "EB"]

        def map_doors_for_direction(direction_key):
            if direction_key != REVERSE_DOORS_FOR_DIR:
                mapped = door_matches
            else:
                mapped = []
                for door in door_matches:
                    rev_index = total_doors - door["door_index"] + 1
                    mapped.append(door_by_index[rev_index])
                mapped.sort(key=lambda item: item["door_index"])
            return [
                {
                    "door_index": door["door_index"],
                    "car_index": door["car_index"],
                    "door_in_car": door["door_in_car"],
                }
                for door in mapped
            ]

        for dir_key in dirs:
            egress_entry = {
                "type": egress_type,
                "label": label,
                "x": round(x_value, 3),
                "delta": delta,
                "doors": map_doors_for_direction(dir_key),
            }
            station["egress_by_dir"][dir_key][egress_type].append(egress_entry)
            if target_lines and any(code not in station["lines"] for code in target_lines):
                transfer_label, transfer_note = transfer_label_parts(
                    exit_desc,
                    target_lines,
                    egress_type,
                )
                station["transfers_by_dir"][dir_key].append(
                    {
                        "type": egress_type,
                        "label": transfer_label,
                        "note": transfer_note,
                        "target_lines": target_lines,
                        "x": round(x_value, 3),
                        "delta": delta,
                        "doors": map_doors_for_direction(dir_key),
                    }
                )

    add_split_level_transfer_fallbacks(stations)
    for station in stations:
        sort_transfer_entries(station)
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
    cache_seed = data_json + HTML_TEMPLATE + SW_TEMPLATE + MANIFEST_TEMPLATE + SOCIAL_PREVIEW
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
    write_file(DOCS_DIR / "social-preview.svg", SOCIAL_PREVIEW)
    write_file(ICONS_DIR / "icon-192.svg", ICON_192)
    write_file(ICONS_DIR / "icon-512.svg", ICON_512)

    return data


if __name__ == "__main__":
    build_site()
