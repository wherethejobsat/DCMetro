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
      if (!/\((Lower|Upper) Level\)$/.test(station.name)) {
        return "";
      }
      return ` [${station.lines.map(lineName).join(", ")}]`;
    };

    const baseStationName = (station) => station.name.replace(/ \((Lower|Upper) Level\)$/, "");

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
        normalize(dir.label.replace(/^Toward\s+/i, "")) === requested
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

      return lines.join("\n");
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
