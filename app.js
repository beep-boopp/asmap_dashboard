/**
 * app.js
 *
 * Fetches timeline.json produced by build_timeline.py and renders
 * charts, summary card, and map table for the ASmap historical dashboard.
 *
 * No frameworks — vanilla JS + Chart.js only.
 */

const charts = {};

async function loadTimeline() {
  try {
    const res = await fetch("timeline.json");
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    render(data);
  } catch (err) {
    setBanner(
      "Run <code>python3 build_timeline.py</code> first, then refresh.",
      "banner-err"
    );
  }
}

function setBanner(html, cls) {
  const el = document.getElementById("alert-banner");
  el.innerHTML = html;
  el.className = cls;
}

// ── Charts ────────────────────────────────────────────────────────────────

function makeChart(id, label, labels, values, color) {
  if (charts[id]) charts[id].destroy();
  const ctx = document.getElementById(id).getContext("2d");
  charts[id] = new Chart(ctx, {
    type: "line",
    data: {
      labels,
      datasets: [{
        label,
        data: values,
        borderColor: color,
        backgroundColor: color + "22",
        borderWidth: 2,
        pointRadius: 4,
        tension: 0.3,
        fill: true,
      }],
    },
    options: {
      responsive: true,
      plugins: { legend: { display: false } },
      scales: {
        x: { ticks: { font: { size: 11 } } },
        y: { ticks: { font: { size: 11 } } },
      },
    },
  });
}

function renderCharts(diffs) {
  const labels       = diffs.map(d => d.to_date);
  const ipv4Values   = diffs.map(d => d.ipv4_changes);
  const ratioValues  = diffs.map(d => +(d.churn_ratio * 100).toFixed(4));

  makeChart("chart-ipv4-churn",  "IPv4 Changes",  labels, ipv4Values,  "#2980b9");
  makeChart("chart-churn-ratio", "Churn Ratio %", labels, ratioValues, "#8e44ad");
}

function renderAsnChart(maps) {
  const labels = maps.map(m => m.date);
  const values = maps.map(m => m.total_asns);
  makeChart("chart-asns", "Total ASNs", labels, values, "#27ae60");
}

// ── Summary card ──────────────────────────────────────────────────────────

function renderSummary(diff) {
  const cls = diff.classification;

  const clsEl = document.getElementById("latest-classification");
  const badgeClass =
    cls === "normal"     ? "badge badge-normal"     :
    cls === "suspicious" ? "badge badge-suspicious" :
                           "badge badge-unknown";
  const label =
    cls === "normal"              ? "Normal"           :
    cls === "suspicious"          ? "Suspicious"       :
    cls === "insufficient_data"   ? "First diff"       : cls;

  clsEl.innerHTML = `<span class="${badgeClass}">${label}</span>`;

  document.getElementById("latest-ipv4").textContent =
    diff.ipv4_changes.toLocaleString();

  if (diff.baseline) {
    document.getElementById("latest-baseline").textContent =
      `${diff.baseline.lower_bound.toLocaleString()} – ${diff.baseline.upper_bound.toLocaleString()}`;
  } else {
    document.getElementById("latest-baseline").textContent = "—";
  }

  document.getElementById("latest-churn-ratio").textContent =
    `${(diff.churn_ratio * 100).toFixed(3)}%`;

  document.getElementById("latest-period").textContent =
    `${diff.from_date} → ${diff.to_date}`;
}

// ── Map table ─────────────────────────────────────────────────────────────

function renderTable(maps, diffs) {
  // Build lookup: to_date → diff
  const diffByToDate = {};
  diffs.forEach(d => { diffByToDate[d.to_date] = d; });

  const tbody = document.getElementById("map-table-body");
  tbody.innerHTML = "";

  maps.forEach(m => {
    const diff = diffByToDate[m.date];
    let churnCell = '<td class="churn-na">—</td>';
    if (diff) {
      const cls =
        diff.classification === "normal"     ? "churn-normal"     :
        diff.classification === "suspicious" ? "churn-suspicious" :
                                               "churn-na";
      churnCell = `<td class="${cls}">${diff.ipv4_changes.toLocaleString()}</td>`;
    }
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${m.date}</td>
      <td>${m.total_asns.toLocaleString()}</td>
      <td>${m.total_prefixes.toLocaleString()}</td>
      <td>${m.ipv4_prefixes.toLocaleString()}</td>
      <td>${m.ipv6_prefixes.toLocaleString()}</td>
      ${churnCell}
    `;
    tbody.appendChild(tr);
  });
}

// ── Main render ───────────────────────────────────────────────────────────

function render(data) {
  const { maps, diffs } = data;

  if (!maps.length || !diffs.length) {
    setBanner("timeline.json loaded but contains no data.", "banner-warn");
    return;
  }

  const suspicious = diffs.filter(d => d.classification === "suspicious").length;
  if (suspicious > 0) {
    setBanner(`⚠ ${suspicious} suspicious diff(s) detected — review the table below.`, "banner-warn");
  } else {
    setBanner("✔ All diffs within normal baseline range.", "banner-ok");
  }

  renderSummary(diffs[diffs.length - 1]);
  renderCharts(diffs);
  renderAsnChart(maps);
  renderTable(maps, diffs);
}

// ── Init ──────────────────────────────────────────────────────────────────

document.getElementById("refresh-btn").addEventListener("click", loadTimeline);
loadTimeline();
