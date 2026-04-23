# ASmap Historical Analysis Dashboard

A static analysis tool for the Bitcoin Core ASmap project that tracks how autonomous system maps evolve over time, detects anomalies, and visualises historical churn.

## Purpose

Bitcoin Core uses ASmap files to diversify peer connections across autonomous systems (ASes). This dashboard helps researchers and operators understand:

- How many prefixes change between consecutive ASmap runs
- Whether observed churn is within a normal baseline or suspicious
- Which ASNs are involved in the most transitions
- Long-term trends in total prefix and ASN counts

## Architecture

```
~/asmap-data/**/*.dat  (raw ASmap files, one per run)
        │
        ▼
 build_timeline.py     ← decodes each map, diffs consecutive pairs,
        │                 writes timeline.json
        ▼
 timeline.json         ← structured metrics for all maps and diffs
        │
        ▼
 index.html / app.js   ← static dashboard: charts, summary card, table
```

## Tech Stack

| Layer    | Technology                          |
|----------|-------------------------------------|
| Backend  | Python 3 (standard library only)    |
| Frontend | Vanilla HTML + JavaScript           |
| Charts   | Chart.js v4 (CDN)                   |
| Styling  | Pico.css v2 (CDN) + style.css       |
| Data     | timeline.json (generated)           |

## Directory Layout

```
asmap_dashboard/
├── build_timeline.py   # generates timeline.json from ASmap data
├── timeline.json       # generated — do not edit manually
├── index.html          # dashboard entry point
├── app.js              # frontend logic
├── style.css           # custom styles
├── data/               # legacy single-run artefacts
├── engine/
│   ├── diff_extractor.py
│   └── compare_runs.py
└── ui/                 # legacy single-run UI
```

## Usage

```bash
cd ~/asmap_dashboard

# Generate timeline.json from all maps under ~/asmap-data/
python3 build_timeline.py

# Serve the dashboard
python3 -m http.server 8000
```

Open `http://localhost:8000` in a browser.

## Data Requirements

- ASmap `.dat` files under `~/asmap-data/` (organised in year subdirectories)
- `~/bitcoin/contrib/asmap/asmap-tool.py` must be present
- Files named `latest_asmap.dat` or containing "unfilled" are automatically skipped
- At least 2 maps are required to compute any diffs

## Output: timeline.json

```json
{
  "maps": [
    {
      "epoch": 1767888000,
      "date": "2026-01-08",
      "total_prefixes": 500000,
      "ipv4_prefixes": 400000,
      "ipv6_prefixes": 100000,
      "total_asns": 12345,
      "top_asns": [{"asn": 4134, "count": 2345}, ...]
    }
  ],
  "diffs": [
    {
      "from_date": "2026-01-08",
      "to_date": "2026-02-05",
      "ipv4_changes": 15319,
      "ipv6_changes": 5949,
      "churn_ratio": 0.038,
      "baseline": {"mean": 14000, "lower_bound": 11200, "upper_bound": 16800},
      "classification": "normal",
      "top_asn_pairs": [["AS14618", "AS16509"], ...]
    }
  ]
}
```
