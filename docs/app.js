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
