// Readings arrive in canonical units (°C, %); convert to °F for display here.
const cToF = (c) => (c * 9) / 5 + 32;
const round1 = (n) => Math.round(n * 10) / 10;

const COLORS = { temp: "#f97583", humidity: "#58a6ff", grid: "#2a2a2a", text: "#aaaaaa" };

Chart.defaults.color = COLORS.text;
Chart.defaults.borderColor = COLORS.grid;

function renderLatest(latest) {
  if (!latest) return;
  const el = (id) => document.getElementById(id);
  if (latest.temp_c !== null) {
    el("current-temp").textContent = round1(cToF(latest.temp_c)) + "°F";
    el("current-temp-c").textContent = round1(latest.temp_c) + "°C";
  }
  if (latest.humidity_pct !== null) {
    el("current-humidity").textContent = round1(latest.humidity_pct) + "%";
  }
  const when = new Date(latest.ts);
  el("last-updated").textContent = when.toLocaleTimeString([], {
    hour: "numeric",
    minute: "2-digit",
  });
  const note = el("last-updated-note");
  note.textContent = latest.stale
    ? "No recent data — sensor may be offline"
    : when.toLocaleDateString();
  note.classList.toggle("stat-stale", latest.stale);
}

function buildChart(canvasId, label, color, yTitle) {
  return new Chart(document.getElementById(canvasId), {
    type: "line",
    data: {
      datasets: [
        {
          label,
          data: [],
          borderColor: color,
          backgroundColor: color + "20",
          fill: true,
          tension: 0.3,
          pointRadius: 0,
          spanGaps: false,
        },
      ],
    },
    options: {
      responsive: true,
      interaction: { mode: "index", intersect: false },
      scales: {
        x: { type: "time", time: { tooltipFormat: "MMM d, h:mm a" } },
        y: { title: { display: true, text: yTitle } },
      },
    },
  });
}

const tempChart = buildChart("tempChart", "Temperature (°F)", COLORS.temp, "°F");
const humidityChart = buildChart("humidityChart", "Humidity (%)", COLORS.humidity, "%");

function updateCharts(readings) {
  const series = (key, fn) =>
    readings.map((r) => ({ x: r.ts, y: r[key] === null ? null : fn(r[key]) }));
  tempChart.data.datasets[0].data = series("temp_c", (v) => round1(cToF(v)));
  humidityChart.data.datasets[0].data = series("humidity_pct", round1);
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
