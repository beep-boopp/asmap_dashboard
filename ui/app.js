/**
 * app.js
 *
 * Front-end entry point for the ASmap Dashboard.
 * Fetches data/result.json and renders verdict, metrics, and provenance
 * information produced by engine/compare_runs.py.
 *
 * No frameworks — vanilla JS only.
 */

async function loadResult() {
  try {
    const res = await fetch("../data/result.json");
    if (!res.ok) throw new Error("Non-OK response");
    const data = await res.json();
    render(data);
  } catch {
    document.getElementById("alert-banner").textContent =
      "Unable to load result.json. Run python3 engine/compare_runs.py and serve via HTTP.";
    document.getElementById("alert-banner").style.background = "#c0392b";
    document.getElementById("alert-banner").style.color = "#fff";
  }
}

function render(data) {
  const { baseline, current, provenance_mismatches, expected_patterns_detected, verdict, explanation } = data;

  // Verdict
  const verdictEl = document.getElementById("verdict");
  verdictEl.textContent = verdict === "normal" ? "Normal" : "Suspicious";
  verdictEl.style.background = verdict === "normal" ? "#27ae60" : "#e67e22";
  verdictEl.style.color = "#fff";

  // Explanation
  document.getElementById("explanation").textContent = explanation;

  // IPv4 changes
  document.getElementById("ipv4-changes").textContent = current.ipv4_changes.toLocaleString();

  // Baseline range
  document.getElementById("baseline-range").textContent =
    `${baseline.lower_bound.toLocaleString()} – ${baseline.upper_bound.toLocaleString()}`;

  // Deviation
  const deviation = ((current.ipv4_changes - baseline.mean) / baseline.mean) * 100;
  document.getElementById("deviation").textContent =
    `${deviation >= 0 ? "+" : ""}${deviation.toFixed(1)}% from baseline`;

  // Provenance mismatches
  const mismatchEl = document.getElementById("mismatches");
  if (provenance_mismatches.length === 0) {
    mismatchEl.textContent = "None";
  } else {
    mismatchEl.innerHTML = "";
    const ul = document.createElement("ul");
    provenance_mismatches.forEach(m => {
      const li = document.createElement("li");
      li.textContent = m;
      ul.appendChild(li);
    });
    mismatchEl.appendChild(ul);
  }

  // Integrity score
  const passed = 3 - provenance_mismatches.length;
  document.getElementById("integrity").textContent = `${passed} / 3 checks passed`;

  // AWS pattern status
  document.getElementById("aws-status").textContent =
    expected_patterns_detected.length > 0 ? "Yes" : "No";

  // Alert banner
  const banner = document.getElementById("alert-banner");
  if (provenance_mismatches.length > 0) {
    banner.textContent = "⚠️ Data source mismatch detected — results may be inconsistent";
    banner.style.background = "#e67e22";
    banner.style.color = "#fff";
  } else {
    banner.textContent = "✔ Data sources consistent";
    banner.style.background = "#27ae60";
    banner.style.color = "#fff";
  }

  // Bar comparison
  const max = Math.max(current.ipv4_changes, baseline.mean);
  const scale = v => Math.round((v / max) * 100);

  document.getElementById("bar-current").style.width = `${scale(current.ipv4_changes)}%`;
  document.getElementById("bar-current").title = `Current: ${current.ipv4_changes}`;

  document.getElementById("bar-baseline").style.width = `${scale(baseline.mean)}%`;
  document.getElementById("bar-baseline").title = `Baseline: ${baseline.mean}`;
}

document.getElementById("refresh-btn").addEventListener("click", loadResult);

loadResult();
