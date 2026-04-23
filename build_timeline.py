"""
build_timeline.py

Discovers ASmap .dat files, decodes each map, diffs consecutive pairs,
generates mock manifests, and writes timeline.json for the dashboard.

Usage (from ~/asmap_dashboard/):
    python3 build_timeline.py
"""

import os
import re
import json
import hashlib
import subprocess
import datetime
from collections import Counter

ASMAP_DATA_DIR = os.path.expanduser("~/asmap-data")
ASMAP_TOOL = os.path.expanduser("~/bitcoin/contrib/asmap/asmap-tool.py")
OUTPUT_FILE = "timeline.json"

ASN_TRANSITION_RE = re.compile(r'(AS\d+)\s*#\s*was\s+(AS\d+)')


def median(values):
    s = sorted(values)
    n = len(s)
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2


def discover_maps():
    maps = []
    for root, _dirs, files in os.walk(ASMAP_DATA_DIR):
        for fname in files:
            if not fname.endswith('.dat'):
                continue
            if 'latest' in fname.lower() or 'unfilled' in fname.lower():
                continue
            m = re.match(r'^(\d+)_', fname)
            if not m:
                continue
            epoch = int(m.group(1))
            date = datetime.datetime.utcfromtimestamp(epoch).strftime('%Y-%m-%d')
            maps.append({'epoch': epoch, 'date': date, 'path': os.path.join(root, fname)})
    maps.sort(key=lambda x: x['epoch'])
    return maps


def run_tool(args):
    result = subprocess.run(
        ['python3', ASMAP_TOOL] + args,
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"  Warning: {result.stderr[:200]}")
    return result.stdout


def decode_map(path):
    output = run_tool(['decode', path])
    ipv4_prefixes = 0
    ipv6_prefixes = 0
    asn_counts = Counter()

    for line in output.splitlines():
        parts = line.strip().split()
        if len(parts) < 2:
            continue
        prefix, asn_str = parts[0], parts[1]
        if '.' in prefix:
            ipv4_prefixes += 1
        elif ':' in prefix:
            ipv6_prefixes += 1
        if asn_str.startswith('AS'):
            asn_counts[asn_str] += 1

    asn_set = set(asn_counts.keys())
    return {
        'total_prefixes': ipv4_prefixes + ipv6_prefixes,
        'ipv4_prefixes': ipv4_prefixes,
        'ipv6_prefixes': ipv6_prefixes,
        'total_asns': len(asn_set),
        'top_asns': [{'asn': asn, 'count': cnt} for asn, cnt in asn_counts.most_common(15)],
        '_asn_set': asn_set,
    }


def compute_diff(prev_path, next_path, prev_asn_set, next_asn_set):
    output = run_tool(['diff', prev_path, next_path])
    ipv4_changes = 0
    ipv6_changes = 0
    pair_counts = Counter()

    for line in output.splitlines():
        line = line.strip()
        if not line or line.startswith('#') or 'AS' not in line:
            continue
        parts = line.split()
        if parts:
            prefix = parts[0]
            if '.' in prefix:
                ipv4_changes += 1
            elif ':' in prefix:
                ipv6_changes += 1
        m = ASN_TRANSITION_RE.search(line)
        if m:
            new_asn, old_asn = m.group(1), m.group(2)
            pair_counts[(old_asn, new_asn)] += 1

    return {
        'ipv4_changes': ipv4_changes,
        'ipv6_changes': ipv6_changes,
        'top_asn_pairs': [[old, new, cnt] for (old, new), cnt in pair_counts.most_common(10)],
        'asns_gained': len(next_asn_set - prev_asn_set),
        'asns_lost': len(prev_asn_set - next_asn_set),
    }


def _h(s):
    return hashlib.sha256(s.encode()).hexdigest()[:16]


def make_manifest(epoch, date_str, mismatch=False):
    year, month = int(date_str[:4]), int(date_str[5:7])
    if mismatch:
        rv_month = month - 2
        rv_year = year
        if rv_month <= 0:
            rv_month += 12
            rv_year -= 1
        routeviews_month = f"{rv_year:04d}-{rv_month:02d}"
        fallback = True
    else:
        routeviews_month = date_str[:7]
        fallback = False

    v = epoch % 100
    return {
        "kartograf_version": "0.4.13",
        "rpki_client_version": "9.7",
        "epoch": epoch,
        "rpki": {
            "repos_total": 13,
            "repos_success": 13,
            "repos_failed": [],
            "cache_hash": _h(f"rpki_{epoch}"),
        },
        "irr": {
            "databases": ["afrinic", "apnic_route", "apnic_route6", "arin", "lacnic", "ripe_route", "ripe_route6"],
            "retries": 0,
            "fetch_duration_seconds": 45 + v // 10,
        },
        "routeviews": {
            "month_used": routeviews_month,
            "fallback_triggered": fallback,
            "ipv4_file_hash": _h(f"rv4_{epoch}"),
            "ipv6_file_hash": _h(f"rv6_{epoch}"),
        },
        "timing": {
            "rpki_fetch_seconds": 320 + v,
            "irr_fetch_seconds": 45 + v // 5,
            "routeviews_fetch_seconds": 12 + v // 20,
            "merge_seconds": 180 + v // 2,
            "total_seconds": 557 + v,
        },
    }


if __name__ == "__main__":
    print("Discovering maps...")
    maps = discover_maps()
    print(f"Found {len(maps)} maps")

    if len(maps) < 2:
        print("Need at least 2 maps to compute diffs. Exiting.")
        raise SystemExit(1)

    mismatch_idx = len(maps) // 2

    print("\nDecoding maps...")
    map_records = []
    for i, mp in enumerate(maps):
        print(f"  [{i+1}/{len(maps)}] {mp['date']}  {os.path.basename(mp['path'])}")
        metrics = decode_map(mp['path'])
        asn_set = metrics.pop('_asn_set')
        manifest = make_manifest(mp['epoch'], mp['date'], mismatch=(i == mismatch_idx))
        map_records.append({
            'epoch': mp['epoch'],
            'date': mp['date'],
            'manifest': manifest,
            **metrics,
            '_asn_set': asn_set,
        })

    print("\nComputing diffs...")
    diff_records = []
    for i in range(1, len(maps)):
        prev_rec, curr_rec = map_records[i - 1], map_records[i]
        print(f"  {prev_rec['date']} → {curr_rec['date']}")
        diff = compute_diff(
            maps[i - 1]['path'], maps[i]['path'],
            prev_rec['_asn_set'], curr_rec['_asn_set'],
        )

        days_between = round((maps[i]['epoch'] - maps[i - 1]['epoch']) / 86400, 1)
        monthly_normalized = round(diff['ipv4_changes'] * 30 / days_between, 1) if days_between > 0 else diff['ipv4_changes']

        prev_ipv4 = prev_rec['ipv4_prefixes']
        churn_ratio = round(diff['ipv4_changes'] / prev_ipv4, 6) if prev_ipv4 > 0 else 0.0
        monthly_churn_ratio = round(monthly_normalized / prev_ipv4, 6) if prev_ipv4 > 0 else 0.0

        # Baseline: median of all prior monthly-normalized values
        prior_normalized = [d['monthly_normalized_changes'] for d in diff_records]
        if len(prior_normalized) < 2:
            baseline_mean = None
            baseline_lower = None
            baseline_upper = None
            classification = 'insufficient_data'
        else:
            med = median(prior_normalized)
            lower = int(med * 0.7)
            upper = int(med * 1.3)
            baseline_mean = int(med)
            baseline_lower = lower
            baseline_upper = upper
            classification = 'normal' if lower <= monthly_normalized <= upper else 'anomalous'

        diff_records.append({
            'from_date': prev_rec['date'],
            'to_date': curr_rec['date'],
            'days_between': days_between,
            'ipv4_changes': diff['ipv4_changes'],
            'ipv6_changes': diff['ipv6_changes'],
            'monthly_normalized_changes': monthly_normalized,
            'churn_ratio': churn_ratio,
            'monthly_churn_ratio': monthly_churn_ratio,
            'asns_gained': diff['asns_gained'],
            'asns_lost': diff['asns_lost'],
            'top_asn_pairs': diff['top_asn_pairs'],
            'baseline_mean': baseline_mean,
            'baseline_lower': baseline_lower,
            'baseline_upper': baseline_upper,
            'classification': classification,
        })

    clean_maps = [{k: v for k, v in rec.items() if k != '_asn_set'} for rec in map_records]

    timeline = {
        'generated_at': datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
        'maps': clean_maps,
        'diffs': diff_records,
    }

    with open(OUTPUT_FILE, 'w') as f:
        json.dump(timeline, f, indent=2)

    print(f"\nWrote {OUTPUT_FILE}  ({len(clean_maps)} maps, {len(diff_records)} diffs)")
    anomalous = sum(1 for d in diff_records if d['classification'] == 'anomalous')
    normal    = sum(1 for d in diff_records if d['classification'] == 'normal')
    print(f"Classifications: {normal} normal, {anomalous} anomalous, {len(diff_records)-normal-anomalous} insufficient_data")
