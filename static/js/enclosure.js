// Readings arrive in canonical units (°C, %); convert to °F for display here.
const cToF = (c) => (c * 9) / 5 + 32;
const round1 = (n) => Math.round(n * 10) / 10;

const COLORS = { grid: "#2a2a2a", text: "#aaaaaa" };
// One line per zone; the empty zone is history recorded before sensors had zones.
const ZONE_COLORS = { hot: "#f97583", cool: "#58a6ff", "": "#aaaaaa" };
const EXTRA_COLORS = ["#d2a8ff", "#7ee787", "#ffa657"];

Chart.defaults.color = COLORS.text;
Chart.defaults.borderColor = COLORS.grid;

function zoneColor(zone, i) {
  return ZONE_COLORS[zone] || EXTRA_COLORS[i % EXTRA_COLORS.length];
}

function statCard(label, value, note, stale) {
  const card = document.createElement("div");
  card.className = "stat-card";
  const parts = [
    ["stat-label", label],
    ["stat-value", value],
    ["stat-note", note],
  ];
  for (const [cls, text] of parts) {
    const span = document.createElement("span");
    span.className = cls;
    span.textContent = text;
    card.appendChild(span);
  }
  card.lastChild.classList.toggle("stat-stale", stale);
  return card;
}

function renderLatest(latest) {
  if (!latest || !latest.length) return;
  const stats = document.getElementById("enclosure-stats");
  const lastCard = document.getElementById("last-updated-card");
  for (const r of latest) {
    const value = r.temp_c === null ? "--" : round1(cToF(r.temp_c)) + "°F";
    const note = [
      r.temp_c === null ? null : round1(r.temp_c) + "°C",
      r.humidity_pct === null ? null : round1(r.humidity_pct) + "% humidity",
    ]
      .filter(Boolean)
      .join(" · ");
    const label = latest.length > 1 || r.zone ? r.zone_label : "Temperature";
    stats.insertBefore(statCard(label, value, r.stale ? "Offline? " + note : note, r.stale), lastCard);
  }
  const newest = new Date(Math.max(...latest.map((r) => new Date(r.ts))));
  document.getElementById("last-updated").textContent = newest.toLocaleTimeString([], {
    hour: "numeric",
    minute: "2-digit",
  });
  const stale = latest.filter((r) => r.stale);
  const note = document.getElementById("last-updated-note");
  note.textContent = stale.length
    ? "No recent data from " + stale.map((r) => r.zone_label.toLowerCase()).join(", ")
    : newest.toLocaleDateString();
  note.classList.toggle("stat-stale", stale.length > 0);
}

function buildChart(canvasId, yTitle) {
  return new Chart(document.getElementById(canvasId), {
    type: "line",
    data: { datasets: [] },
    options: {
      responsive: true,
      interaction: { mode: "nearest", axis: "x", intersect: false },
      plugins: { title: { display: true, text: yTitle === "°F" ? "Temperature" : "Humidity" } },
      scales: {
        x: { type: "time", time: { tooltipFormat: "MMM d, h:mm a" } },
        y: { title: { display: true, text: yTitle } },
      },
    },
  });
}

const tempChart = buildChart("tempChart", "°F");
const humidityChart = buildChart("humidityChart", "%");

function zoneDatasets(readings, key, fn, label) {
  // Same order as the cards: hot, cool, other zones, then zone-less history.
  const rank = (z) => ({ hot: 0, cool: 1, "": 3 })[z] ?? 2;
  const zones = [...new Set(readings.map((r) => r.zone || ""))].sort(
    (a, b) => rank(a) - rank(b) || a.localeCompare(b),
  );
  return zones.map((zone, i) => {
    const color = zoneColor(zone, i);
    return {
      label: (zone ? zone.charAt(0).toUpperCase() + zone.slice(1) + " side " : "Enclosure ") + label,
      data: readings
        .filter((r) => (r.zone || "") === zone)
        .map((r) => ({ x: r.ts, y: r[key] === null ? null : fn(r[key]) })),
      borderColor: color,
      backgroundColor: color + "20",
      fill: zones.length === 1,
      tension: 0.3,
      pointRadius: 0,
      spanGaps: false,
    };
  });
}

function updateCharts(readings) {
  tempChart.data.datasets = zoneDatasets(readings, "temp_c", (v) => round1(cToF(v)), "(°F)");
  humidityChart.data.datasets = zoneDatasets(readings, "humidity_pct", round1, "(%)");
  tempChart.update();
  humidityChart.update();
  document.getElementById("chart-empty").hidden = readings.length > 0;
}

async function load(hours) {
  const resp = await fetch(`/api/enclosures/${ENCLOSURE.subject}/readings?hours=${hours}`);
  updateCharts(await resp.json());
}

document.querySelectorAll(".chart-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelector(".chart-btn.active").classList.remove("active");
    btn.classList.add("active");
    load(btn.dataset.hours);
  });
});

renderLatest(ENCLOSURE.latest);
load(24);

// Tabs (only rendered for subjects with plans). The URL hash keeps a tab linkable.
const tabs = [...document.querySelectorAll(".tab")];

function showTab(name) {
  tabs.forEach((tab) => {
    const on = tab.dataset.panel === name;
    tab.classList.toggle("active", on);
    tab.setAttribute("aria-selected", on);
    tab.tabIndex = on ? 0 : -1;
    document.getElementById("panel-" + tab.dataset.panel).hidden = !on;
  });
}

if (tabs.length) {
  tabs.forEach((tab, i) => {
    tab.addEventListener("click", () => {
      showTab(tab.dataset.panel);
      history.replaceState(null, "", "#" + tab.dataset.panel);
    });
    tab.addEventListener("keydown", (e) => {
      const step = { ArrowRight: 1, ArrowLeft: -1 }[e.key];
      if (!step) return;
      const next = tabs[(i + step + tabs.length) % tabs.length];
      next.focus();
      next.click();
    });
  });
  const wanted = location.hash.slice(1);
  if (tabs.some((t) => t.dataset.panel === wanted)) showTab(wanted);
}
