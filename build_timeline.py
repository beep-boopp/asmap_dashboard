"""
build_timeline.py

Discovers ASmap .dat files under ~/asmap-data/, decodes each map to extract
prefix and ASN metrics, computes diffs between consecutive maps, and writes
timeline.json for the dashboard.

Usage (from ~/asmap_dashboard/):
    python3 build_timeline.py
"""

import os
import re
import json
import subprocess
import datetime
from collections import Counter

ASMAP_DATA_DIR = os.path.expanduser("~/asmap-data")
ASMAP_TOOL = os.path.expanduser("~/bitcoin/contrib/asmap/asmap-tool.py")
OUTPUT_FILE = "timeline.json"

ASN_TRANSITION_RE = re.compile(r'(AS\d+)\s*#\s*was\s+(AS\d+)')


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
        print(f"  Warning: tool stderr: {result.stderr[:300]}")
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
            try:
                asn_counts[int(asn_str[2:])] += 1
            except ValueError:
                pass

    return {
        'total_prefixes': ipv4_prefixes + ipv6_prefixes,
        'ipv4_prefixes': ipv4_prefixes,
        'ipv6_prefixes': ipv6_prefixes,
        'total_asns': len(asn_counts),
        'top_asns': [{'asn': asn, 'count': cnt} for asn, cnt in asn_counts.most_common(10)],
    }


def compute_diff(prev_path, next_path):
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
        'top_asn_pairs': [list(pair) for pair, _ in pair_counts.most_common(5)],
    }


if __name__ == "__main__":
    print("Discovering maps...")
    maps = discover_maps()
    print(f"Found {len(maps)} maps")

    if len(maps) < 2:
        print("Need at least 2 maps to compute diffs. Exiting.")
        raise SystemExit(1)

    print("\nDecoding maps...")
    map_records = []
    for mp in maps:
        print(f"  {mp['date']}  {os.path.basename(mp['path'])}")
        metrics = decode_map(mp['path'])
        map_records.append({'epoch': mp['epoch'], 'date': mp['date'], **metrics})

    print("\nComputing diffs...")
    diff_records = []
    for i in range(1, len(maps)):
        prev, curr = maps[i - 1], maps[i]
        print(f"  {prev['date']} → {curr['date']}")
        diff = compute_diff(prev['path'], curr['path'])

        prev_ipv4 = map_records[i - 1]['ipv4_prefixes']
        churn_ratio = round(diff['ipv4_changes'] / prev_ipv4, 6) if prev_ipv4 > 0 else 0.0

        prior_ipv4_changes = [d['ipv4_changes'] for d in diff_records]
        if not prior_ipv4_changes:
            baseline = None
            classification = 'insufficient_data'
        else:
            mean = sum(prior_ipv4_changes) / len(prior_ipv4_changes)
            lower = int(mean * 0.8)
            upper = int(mean * 1.2)
            baseline = {'mean': int(mean), 'lower_bound': lower, 'upper_bound': upper}
            classification = 'normal' if lower <= diff['ipv4_changes'] <= upper else 'suspicious'

        diff_records.append({
            'from_date': prev['date'],
            'to_date': curr['date'],
            'ipv4_changes': diff['ipv4_changes'],
            'ipv6_changes': diff['ipv6_changes'],
            'churn_ratio': churn_ratio,
            'baseline': baseline,
            'classification': classification,
            'top_asn_pairs': diff['top_asn_pairs'],
        })

    timeline = {'maps': map_records, 'diffs': diff_records}
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(timeline, f, indent=2)

    print(f"\nWrote {OUTPUT_FILE}  ({len(map_records)} maps, {len(diff_records)} diffs)")
