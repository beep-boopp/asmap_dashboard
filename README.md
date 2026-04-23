# ASMap Analysis Dashboard

Historical analysis and investigation tool for Bitcoin Core ASMap files.

## Quick Start

```bash
# Generate timeline data from local asmap-data
python3 build_timeline.py

# Serve the dashboard
python3 -m http.server 8000

# Open http://localhost:8000
```

## What This Shows

- **Real data**: All maps from the asmap-data repository, decoded and diffed
- **Churn trends**: How many IP prefix → ASN mappings change between runs
- **Anomaly detection**: Baseline-aware classification of each diff (±30% of historical mean)
- **Investigation flow**: Click any data point on the churn chart to drill into ASN transitions and run provenance
- **Mock manifests**: Simulated run metadata demonstrating what Kartograf could produce (one run intentionally shows a RouteViews fallback to demonstrate the April 2 divergence scenario)

## Architecture

- Backend: Python 3 (stdlib only), calls asmap-tool.py for decode/diff
- Frontend: Vanilla JS + Chart.js, single HTML file — no build step, no frameworks
- Data: `timeline.json` generated locally, served statically

## File Structure

```
asmap_dashboard/
├── build_timeline.py   # generates timeline.json
├── index.html          # single-file dashboard (CSS + JS embedded)
├── timeline.json       # generated — do not edit
└── README.md
```

## Requirements

- `~/asmap-data/` with at least 2 `*_asmap.dat` files (skip files named "latest" or "unfilled")
- `~/bitcoin/contrib/asmap/asmap-tool.py` present
- Python 3.7+
