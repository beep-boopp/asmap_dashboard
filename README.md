# ASMap Analysis Dashboard

Historical analysis and investigation tool for Bitcoin Core ASMap files.  
Built as the MVP for the **Summer of Bitcoin 2026** proposal.

---

## Quick Start

```bash
# 1. Generate timeline data from your local asmap-data
python3 build_timeline.py

# 2. Serve the dashboard
python3 -m http.server 8000

# 3. Open in browser
#    http://localhost:8000
```

---

## What It Does

### Real data pipeline
`build_timeline.py` processes all `.dat` files in `~/asmap-data/`:

1. **Discovers** maps chronologically by epoch timestamp in filename — skips `latest` and `unfilled` files
2. **Decodes** each map with `asmap-tool.py decode` → extracts IPv4/IPv6 prefix counts, unique ASN count, top 15 ASNs by prefix share
3. **Diffs** consecutive pairs with `asmap-tool.py diff` → extracts IPv4/IPv6 change counts, top 10 ASN transition pairs (with counts), ASNs gained/lost
4. **Normalizes** churn by time gap (`ipv4_changes × 30 / days_between`) so a 146-day diff is comparable to a 28-day diff
5. **Classifies** each diff using a rolling median baseline ±30% — first two diffs are `insufficient_data`, the rest are `normal` or `anomalous`
6. **Generates** mock run manifests (structurally accurate Kartograf schema) with one intentional RouteViews fallback to demonstrate the April 2 divergence scenario
7. **Outputs** `timeline.json` with all maps, diffs, baselines, and manifests

Current dataset: **8 maps** (2025-03-21 → 2026-03-05), **7 diffs**, **1 anomalous** diff (Dec 4 → Jan 8 at ~21,052/month normalized, outside the ±30% baseline).

### Interactive dashboard (`index.html`)
Single HTML file — no build step, no frameworks, no dependencies beyond Chart.js via CDN.

**4 charts:**
- **IPv4 Churn Over Time** — monthly-normalized values with a shaded baseline band (±30%); anomalous points colored amber, normal points green; click any point to open the investigation panel
- **Churn Ratio %** — monthly-normalized churn / total IPv4 prefixes
- **Total ASNs Over Time** — unique ASN count per map snapshot
- **ASN Turnover Per Diff** — grouped bar: ASNs gained (green) vs lost (red)

**Investigation panel** (the key feature):  
Click a point on the churn chart → a panel expands showing:
- Top ASN transitions table with known-pattern labels (e.g. `AS14618 ↔ AS16509` → "Amazon AWS internal reorganization")
- Side-by-side provenance comparison between the two run manifests, with mismatches highlighted red
- Natural-language verdict: raw changes + normalized rate + baseline position + data source status

**Map history table:**  
All 8 maps with Date, Epoch, Total ASNs, Prefixes, IPv4, IPv6, Gap (days — amber badge if >45 days), raw Churn, Normalized/month, Classification. Click any row to highlight the corresponding chart point and open the investigation panel.

**Manifest inspector:**  
Collapsible accordion per map showing full mock manifest JSON. Runs with `fallback_triggered: true` show a warning badge.

---

## What Is Real vs Mock

| Component | Status |
|---|---|
| Map statistics (ASNs, prefix counts) | **Real** — decoded from `.dat` files |
| Churn metrics (IPv4/IPv6 changes) | **Real** — from `asmap-tool.py diff` |
| ASN transition pairs | **Real** — parsed from diff output |
| Time-gap normalization | **Real** — epoch arithmetic |
| Baseline classification | **Real** — rolling median ±30% |
| Run manifests | **Mock** — structurally accurate Kartograf schema |
| Provenance comparison | **Mock** — demonstrates future real-manifest workflow |
| RouteViews fallback scenario | **Mock** — one manifest has `fallback_triggered: true` |

The mock-to-real migration path requires only patching Kartograf to emit `run_manifest.json` alongside each `.dat` — the dashboard ingests this format already.

---

## Architecture

```
~/asmap-data/**/*_asmap.dat
        │
        ▼
build_timeline.py        ← Python 3, stdlib only
        │  decode + diff via asmap-tool.py
        │  normalize, classify, generate manifests
        ▼
timeline.json            ← single data file
        │
        ▼
index.html               ← vanilla JS + Chart.js (CDN)
                            embedded CSS + JS, no build step
```

---

## File Structure

```
asmap_dashboard/
├── build_timeline.py      # data pipeline — generates timeline.json
├── index.html             # dashboard — single file, everything embedded
├── timeline.json          # generated output — do not edit manually
├── README.md
├── engine/                # earlier single-run analysis scripts
│   ├── diff_extractor.py
│   └── compare_runs.py
└── data/                  # earlier single-run data artefacts
```

---

## Requirements

| Requirement | Notes |
|---|---|
| Python 3.7+ | stdlib only — no pip installs |
| `~/asmap-data/` | at least 2 `*_asmap.dat` files |
| `~/bitcoin/contrib/asmap/asmap-tool.py` | for decode and diff operations |

---

## Known ASN Patterns

The dashboard labels these transitions automatically:

| Pair | Label |
|---|---|
| AS14618 ↔ AS16509 | Amazon AWS internal reorganization |
| AS4134 ↔ AS4837 | China Telecom / China Unicom reallocation |
| AS3356 ↔ AS174 | Lumen / Cogent routing change |
