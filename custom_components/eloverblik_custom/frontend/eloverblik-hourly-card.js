class EloverblikHourlyCard extends HTMLElement {
  static async getConfigElement() {
    return document.createElement("eloverblik-hourly-card-editor");
  }

  static getStubConfig(hass) {
    const suggestedEntity = findSuggestedEntity(hass);
    return {
      entity: suggestedEntity || "",
      title: "Eloverblik Hourly API Data",
      hours_to_show: 24,
    };
  }

  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._config = undefined;
    this._hass = undefined;
    this._hoveredPoint = null;
    this._selectedHoursToShow = null;
  }

  setConfig(config) {
    if (!config || !config.entity) {
      throw new Error("Eloverblik hourly card requires an entity");
    }

    this._config = {
      hours_to_show: 24,
      ...config,
    };
    this._selectedHoursToShow = Number(this._config.hours_to_show) || 24;
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  getCardSize() {
    return 4;
  }

  _render() {
    if (!this.shadowRoot || !this._config) {
      return;
    }

    const stateObj = this._hass?.states?.[this._config.entity];
    const cardTitle =
      this._config.title ||
      stateObj?.attributes?.friendly_name ||
      "Eloverblik hourly consumption";

    if (!stateObj) {
      this.shadowRoot.innerHTML = this._buildFrame(cardTitle, "<div class=\"empty\">Entity not found.</div>");
      return;
    }

    const allPoints = this._getHourlyPoints(stateObj.attributes.hourly_data);
    const hoursToShow = this._selectedHoursToShow;
    const points =
      Number.isFinite(hoursToShow) && hoursToShow > 0
        ? allPoints.slice(-hoursToShow)
        : allPoints;

    if (!points.length) {
      this.shadowRoot.innerHTML = this._buildFrame(
        cardTitle,
        "<div class=\"empty\">No hourly data available.</div>",
      );
      return;
    }

    const chart = this._buildChart(points);
    const latestPoint = points[points.length - 1];
    const tooltipHtml = this._buildTooltip(points);
    const hoursOptions = this._buildHoursOptions(allPoints.length);
    const summaryHtml = `
      <div class="summary">
        <div>
          <div class="summary-label">Latest API hour</div>
          <div class="summary-value">${this._escapeHtml(this._formatLocalDateTime(latestPoint.localStartMs, latestPoint.apiStartMs))}</div>
        </div>
        <div>
          <div class="summary-label">Consumption</div>
          <div class="summary-value">${this._formatKwh(latestPoint.kwh)}</div>
        </div>
        <div>
          <div class="summary-label">Hours to show</div>
          <label class="hours-select-label">
            <select id="hours-to-show-select" class="hours-select">
              ${hoursOptions}
            </select>
          </label>
        </div>
      </div>
    `;

    this.shadowRoot.innerHTML = this._buildFrame(
      cardTitle,
      `
        ${summaryHtml}
        <div class="chart-shell">
          ${chart}
          ${tooltipHtml}
        </div>
      `,
    );

    this._attachPointHandlers(points);
    this._attachHoursSelector();
  }

  _buildFrame(title, body) {
    return `
      <style>
        :host {
          display: block;
        }

        ha-card {
          overflow: hidden;
        }

        .card-content {
          padding: 16px;
        }

        .summary {
          display: grid;
          gap: 16px;
          grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
          margin-bottom: 16px;
        }

        .summary-label {
          color: var(--secondary-text-color);
          font-size: 0.85rem;
          margin-bottom: 4px;
        }

        .summary-value {
          font-size: 1rem;
          font-weight: 600;
          line-height: 1.4;
        }

        .hours-select-label {
          display: inline-block;
          width: 100%;
        }

        .hours-select {
          background: var(--card-background-color);
          border: 1px solid var(--divider-color);
          border-radius: 10px;
          color: var(--primary-text-color);
          font: inherit;
          padding: 8px 10px;
          width: 100%;
        }

        .chart-shell {
          position: relative;
        }

        .empty {
          color: var(--secondary-text-color);
          padding: 12px 0;
        }

        .axis-label {
          fill: var(--secondary-text-color);
          font-size: 11px;
        }

        .grid-line {
          stroke: var(--divider-color);
          stroke-width: 1;
        }

        .plot-line {
          fill: none;
          stroke: var(--primary-color);
          stroke-linecap: round;
          stroke-linejoin: round;
          stroke-width: 3;
        }

        .plot-area {
          fill: color-mix(in srgb, var(--primary-color) 18%, transparent);
        }

        .point {
          cursor: pointer;
          fill: var(--card-background-color);
          stroke: var(--primary-color);
          stroke-width: 2;
        }

        .point.active {
          fill: var(--primary-color);
        }

        .hitbox {
          fill: transparent;
          cursor: pointer;
        }

        .tooltip {
          position: absolute;
          pointer-events: none;
          background: var(--ha-card-background, var(--card-background-color));
          border: 1px solid var(--divider-color);
          border-radius: 12px;
          box-shadow: var(--ha-card-box-shadow, 0 2px 8px rgba(0, 0, 0, 0.25));
          color: var(--primary-text-color);
          font-size: 0.85rem;
          left: var(--tooltip-left, 12px);
          max-width: 260px;
          opacity: var(--tooltip-opacity, 0);
          padding: 10px 12px;
          top: var(--tooltip-top, 12px);
          transform: translate(-50%, calc(-100% - 12px));
          transition: opacity 120ms ease-in-out;
          z-index: 1;
        }

        .tooltip strong {
          display: block;
          font-size: 0.9rem;
          margin-bottom: 6px;
        }

        .tooltip-row {
          display: flex;
          gap: 8px;
          justify-content: space-between;
          margin-top: 4px;
        }

        .tooltip-label {
          color: var(--secondary-text-color);
        }
      </style>
      <ha-card header="${this._escapeHtml(title)}">
        <div class="card-content">
          ${body}
        </div>
      </ha-card>
    `;
  }

  _buildChart(points) {
    const width = 720;
    const height = 280;
    const padding = { top: 18, right: 18, bottom: 34, left: 52 };
    const plotWidth = width - padding.left - padding.right;
    const plotHeight = height - padding.top - padding.bottom;

    const minX = points[0].apiStartMs;
    const maxX = points[points.length - 1].apiStartMs;
    const rawMinY = Math.min(...points.map((point) => point.kwh));
    const rawMaxY = Math.max(...points.map((point) => point.kwh));
    const minY = 0;
    const maxY = rawMaxY === rawMinY ? rawMaxY + 1 : rawMaxY * 1.1;

    const mapX = (value) => {
      if (maxX === minX) {
        return padding.left + plotWidth / 2;
      }
      return padding.left + ((value - minX) / (maxX - minX)) * plotWidth;
    };

    const mapY = (value) => {
      const range = maxY - minY || 1;
      return padding.top + plotHeight - ((value - minY) / range) * plotHeight;
    };

    const pathPoints = points.map((point) => `${mapX(point.apiStartMs)},${mapY(point.kwh)}`);
    const linePath = this._buildLinePath(points, mapX, mapY);
    const areaPath = this._buildAreaPath(points, mapX, mapY, padding.top + plotHeight);
    const xTickIndexes = this._buildTickIndexes(points.length, 4);
    const yTicks = this._buildYTicks(minY, maxY, 4);

    const xAxis = xTickIndexes
      .map((index) => {
        const point = points[index];
        const x = mapX(point.apiStartMs);
        return `
          <line class="grid-line" x1="${x}" x2="${x}" y1="${padding.top}" y2="${padding.top + plotHeight}" />
          <text class="axis-label" x="${x}" y="${height - 10}" text-anchor="middle">
            ${this._escapeHtml(this._formatAxisLabel(point.localStartMs, point.apiStartMs))}
          </text>
        `;
      })
      .join("");

    const yAxis = yTicks
      .map((value) => {
        const y = mapY(value);
        return `
          <line class="grid-line" x1="${padding.left}" x2="${width - padding.right}" y1="${y}" y2="${y}" />
          <text class="axis-label" x="${padding.left - 8}" y="${y + 4}" text-anchor="end">
            ${this._escapeHtml(value.toFixed(2))}
          </text>
        `;
      })
      .join("");

    const pointsHtml = points
      .map((point, index) => {
        const x = mapX(point.apiStartMs);
        const y = mapY(point.kwh);
        const isActive = this._hoveredPoint?.index === index;
        return `
          <rect
            class="hitbox"
            data-index="${index}"
            x="${x - 10}"
            y="${padding.top}"
            width="20"
            height="${plotHeight}"
          ></rect>
          <circle
            class="point${isActive ? " active" : ""}"
            data-index="${index}"
            cx="${x}"
            cy="${y}"
            r="${isActive ? 5 : 4}"
          ></circle>
        `;
      })
      .join("");

    return `
      <svg viewBox="0 0 ${width} ${height}" role="img" aria-label="Hourly Eloverblik consumption">
        ${yAxis}
        ${xAxis}
        <path class="plot-area" d="${areaPath}"></path>
        <path class="plot-line" d="${linePath}"></path>
        ${pointsHtml}
      </svg>
    `;
  }

  _buildTooltip(points) {
    if (!this._hoveredPoint) {
      return '<div class="tooltip" style="--tooltip-opacity: 0;"></div>';
    }

    const point = points[this._hoveredPoint.index];
    if (!point) {
      return '<div class="tooltip" style="--tooltip-opacity: 0;"></div>';
    }

    return `
      <div
        class="tooltip"
        style="--tooltip-left: ${this._hoveredPoint.x}px; --tooltip-top: ${this._hoveredPoint.y}px; --tooltip-opacity: 1;"
      >
        <strong>${this._escapeHtml(this._formatKwh(point.kwh))}</strong>
        <div class="tooltip-row">
          <span class="tooltip-label">Local start</span>
          <span>${this._escapeHtml(this._formatLocalDateTime(point.localStartMs, point.apiStartMs))}</span>
        </div>
        <div class="tooltip-row">
          <span class="tooltip-label">Local end</span>
          <span>${this._escapeHtml(this._formatLocalDateTime(point.localEndMs, point.apiEndMs))}</span>
        </div>
      </div>
    `;
  }

  _attachPointHandlers(points) {
    if (!this.shadowRoot) {
      return;
    }

    const chartShell = this.shadowRoot.querySelector(".chart-shell");
    if (chartShell) {
      chartShell.addEventListener("mouseleave", () => {
        if (this._hoveredPoint !== null) {
          this._hoveredPoint = null;
          this._render();
        }
      });
    }

    this.shadowRoot.querySelectorAll("[data-index]").forEach((element) => {
      element.addEventListener("mousemove", (event) => {
        const index = Number(event.currentTarget.dataset.index);
        const shellRect = chartShell?.getBoundingClientRect();
        if (!shellRect || !Number.isFinite(index) || !points[index]) {
          return;
        }

        const x = Math.min(
          Math.max(event.clientX - shellRect.left, 80),
          shellRect.width - 80,
        );
        const y = Math.max(event.clientY - shellRect.top, 60);
        this._hoveredPoint = { index, x, y };
        this._render();
      });
    });
  }

  _attachHoursSelector() {
    if (!this.shadowRoot) {
      return;
    }

    this.shadowRoot
      .getElementById("hours-to-show-select")
      ?.addEventListener("change", (event) => {
        const selectedValue = event.target.value;
        if (selectedValue === "all") {
          this._selectedHoursToShow = null;
        } else {
          const parsedValue = Number(selectedValue);
          this._selectedHoursToShow =
            Number.isFinite(parsedValue) && parsedValue > 0 ? parsedValue : 24;
        }
        this._hoveredPoint = null;
        this._render();
      });
  }

  _getHourlyPoints(hourlyData) {
    if (!Array.isArray(hourlyData)) {
      return [];
    }

    return hourlyData
      .map((entry) => {
        const apiStartUtc = entry.api_start_utc || null;
        const apiEndUtc = entry.api_end_utc || null;
        const localStart = entry.start || null;
        const localEnd = entry.end || null;
        const apiStartMs = this._parseDate(apiStartUtc || localStart);
        const apiEndMs = this._parseDate(apiEndUtc || localEnd);
        const localStartMs = this._parseDate(localStart || apiStartUtc);
        const localEndMs = this._parseDate(localEnd || apiEndUtc);
        const kwh = Number(entry.kwh);

        return {
          apiStartUtc,
          apiEndUtc,
          apiStartMs,
          apiEndMs,
          localStart,
          localEnd,
          localStartMs,
          localEndMs,
          kwh,
        };
      })
      .filter(
        (point) => Number.isFinite(point.apiStartMs) && Number.isFinite(point.kwh),
      )
      .sort((left, right) => left.apiStartMs - right.apiStartMs);
  }

  _buildLinePath(points, mapX, mapY) {
    return points
      .map((point, index) => {
        const command = index === 0 ? "M" : "L";
        return `${command} ${mapX(point.apiStartMs)} ${mapY(point.kwh)}`;
      })
      .join(" ");
  }

  _buildAreaPath(points, mapX, mapY, baselineY) {
    if (!points.length) {
      return "";
    }

    const linePath = this._buildLinePath(points, mapX, mapY);
    const lastPoint = points[points.length - 1];
    const firstPoint = points[0];
    return `${linePath} L ${mapX(lastPoint.apiStartMs)} ${baselineY} L ${mapX(firstPoint.apiStartMs)} ${baselineY} Z`;
  }

  _buildTickIndexes(length, tickCount) {
    if (length <= tickCount) {
      return Array.from({ length }, (_, index) => index);
    }

    const step = (length - 1) / (tickCount - 1);
    return Array.from({ length: tickCount }, (_, index) =>
      Math.round(index * step),
    );
  }

  _buildYTicks(min, max, count) {
    const step = (max - min) / count;
    return Array.from({ length: count + 1 }, (_, index) => min + index * step);
  }

  _buildHoursOptions(totalPoints) {
    const presets = [6, 12, 24, 48, 72, 168].filter(
      (value) => value < totalPoints,
    );
    const currentValue = this._selectedHoursToShow;
    const optionValues = [...new Set([...presets, currentValue].filter(Boolean))].sort(
      (left, right) => left - right,
    );

    const numericOptions = optionValues
      .map(
        (value) => `
          <option value="${value}" ${
            currentValue === value ? "selected" : ""
          }>
            ${value} hours
          </option>
        `,
      )
      .join("");

    return `
      ${numericOptions}
      <option value="all" ${currentValue === null ? "selected" : ""}>
        All available
      </option>
    `;
  }

  _formatAxisLabel(localStartMs, apiStartMs) {
    const date = Number.isFinite(localStartMs) ? localStartMs : apiStartMs;
    return new Intl.DateTimeFormat(undefined, {
      month: "short",
      day: "numeric",
      hour: "numeric",
    }).format(date);
  }

  _formatLocalDateTime(localMs, fallbackMs) {
    const date = Number.isFinite(localMs) ? localMs : fallbackMs;
    if (!Number.isFinite(date)) {
      return "n/a";
    }

    return new Intl.DateTimeFormat(undefined, {
      month: "short",
      day: "numeric",
      hour: "numeric",
      minute: "2-digit",
    }).format(date);
  }

  _formatKwh(value) {
    return `${Number(value).toFixed(3)} kWh`;
  }

  _parseDate(value) {
    if (!value) {
      return Number.NaN;
    }

    const parsed = Date.parse(value);
    return Number.isFinite(parsed) ? parsed : Number.NaN;
  }

  _escapeHtml(value) {
    return String(value)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");
  }
}

class EloverblikHourlyCardEditor extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._config = {
      entity: "",
      title: "Eloverblik Hourly API Data",
      hours_to_show: 24,
    };
    this._hass = undefined;
  }

  setConfig(config) {
    this._config = {
      entity: "",
      title: "Eloverblik Hourly API Data",
      hours_to_show: 24,
      ...config,
    };
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    if (!this._config.entity) {
      const suggestedEntity = findSuggestedEntity(hass);
      if (suggestedEntity) {
        this._config = {
          ...this._config,
          entity: suggestedEntity,
        };
        this._emitConfigChanged();
      }
    }
    this._render();
  }

  _render() {
    if (!this.shadowRoot) {
      return;
    }

    const entityOptions = getEntityOptions(this._hass, this._config.entity);

    this.shadowRoot.innerHTML = `
      <style>
        :host {
          display: block;
        }

        .form {
          display: grid;
          gap: 16px;
        }

        label {
          color: var(--primary-text-color);
          display: grid;
          font-size: 0.9rem;
          gap: 6px;
        }

        .hint {
          color: var(--secondary-text-color);
          font-size: 0.8rem;
        }

        input,
        select {
          background: var(--card-background-color);
          border: 1px solid var(--divider-color);
          border-radius: 10px;
          color: var(--primary-text-color);
          font: inherit;
          padding: 10px 12px;
        }
      </style>
      <div class="form">
        <label>
          Entity
          <select id="entity">
            ${entityOptions
              .map(
                (option) => `
                  <option value="${escapeHtml(option.value)}" ${
                    option.value === this._config.entity ? "selected" : ""
                  }>
                    ${escapeHtml(option.label)}
                  </option>
                `,
              )
              .join("")}
          </select>
          <span class="hint">Choose the Eloverblik "Latest hourly consumption" entity.</span>
        </label>

        <label>
          Title
          <input
            id="title"
            type="text"
            value="${escapeHtml(this._config.title || "")}"
            placeholder="Eloverblik Hourly API Data"
          />
        </label>

        <label>
          Hours to show
          <input
            id="hours_to_show"
            type="number"
            min="1"
            step="1"
            value="${escapeHtml(String(this._config.hours_to_show || 24))}"
          />
          <span class="hint">Defaults to the latest 24 hourly points.</span>
        </label>
      </div>
    `;

    this.shadowRoot.getElementById("entity")?.addEventListener("change", (event) => {
      this._updateConfig("entity", event.target.value);
    });
    this.shadowRoot.getElementById("title")?.addEventListener("input", (event) => {
      const value = event.target.value.trim();
      this._updateConfig("title", value || "Eloverblik Hourly API Data");
    });
    this.shadowRoot
      .getElementById("hours_to_show")
      ?.addEventListener("change", (event) => {
        const parsed = Number(event.target.value);
        this._updateConfig(
          "hours_to_show",
          Number.isFinite(parsed) && parsed > 0 ? parsed : 24,
        );
      });
  }

  _updateConfig(key, value) {
    this._config = {
      ...this._config,
      [key]: value,
    };
    this._emitConfigChanged();
  }

  _emitConfigChanged() {
    this.dispatchEvent(
      new CustomEvent("config-changed", {
        detail: { config: this._config },
        bubbles: true,
        composed: true,
      }),
    );
  }
}

function findSuggestedEntity(hass) {
  const options = getEntityOptions(hass);
  return options[0]?.value || "";
}

function getEntityOptions(hass, selectedEntity = "") {
  const states = Object.entries(hass?.states || {});
  const options = states
    .filter(([, stateObj]) => hasHourlyData(stateObj))
    .map(([entityId, stateObj]) => ({
      value: entityId,
      label: stateObj.attributes.friendly_name
        ? `${stateObj.attributes.friendly_name} (${entityId})`
        : entityId,
    }))
    .sort((left, right) => left.label.localeCompare(right.label));

  if (!options.length) {
    return [
      {
        value: selectedEntity,
        label: selectedEntity || "No matching entities found",
      },
    ];
  }

  if (selectedEntity && !options.some((option) => option.value === selectedEntity)) {
    return [
      {
        value: selectedEntity,
        label: `${selectedEntity} (current)`,
      },
      ...options,
    ];
  }

  return options;
}

function hasHourlyData(stateObj) {
  if (!stateObj || !Array.isArray(stateObj.attributes?.hourly_data)) {
    return false;
  }

  return true;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

customElements.define("eloverblik-hourly-card", EloverblikHourlyCard);
customElements.define(
  "eloverblik-hourly-card-editor",
  EloverblikHourlyCardEditor,
);

window.customCards = window.customCards || [];
window.customCards.push({
  type: "eloverblik-hourly-card",
  name: "Eloverblik Hourly Card",
  description: "Plot Eloverblik hourly consumption using API timestamps.",
});
