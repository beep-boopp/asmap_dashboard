"""
diff_extractor.py

Ingests raw ASmap diff output produced by asmap-tool and extracts structured
metrics from it (e.g., prefix additions/removals, ASN-level changes).

Inputs:  raw diff text or JSON from asmap-tool
Outputs: normalised metrics dict written to data/diff_metrics.json
"""

import re
import json
import sys
from collections import Counter

IPV4_RE = re.compile(r'^\d+\.\d+\.\d+\.\d+/\d+')
IPV6_RE = re.compile(r'^[0-9a-fA-F:]+/\d+')
ASN_TRANSITION_RE = re.compile(r'(AS\d+)\s*#\s*was\s+(AS\d+)')


def extract_metrics(lines):
    ipv4_changes = 0
    ipv6_changes = 0
    pair_counts = Counter()

    for line in lines:
        line = line.strip()
        if not line or line.startswith('#') or 'AS' not in line:
            continue

        if IPV4_RE.match(line):
            ipv4_changes += 1
        elif IPV6_RE.match(line):
            ipv6_changes += 1

        m = ASN_TRANSITION_RE.search(line)
        if m:
            new_asn, old_asn = m.group(1), m.group(2)
            pair_counts[(old_asn, new_asn)] += 1

    top_asn_pairs = [list(pair) for pair, _ in pair_counts.most_common(3)]

    return {
        "ipv4_changes": ipv4_changes,
        "ipv6_changes": ipv6_changes,
        "top_asn_pairs": top_asn_pairs,
    }


if __name__ == "__main__":
    input_path = sys.argv[1] if len(sys.argv) > 1 else "data/diff_jan_feb.txt"
    output_path = "data/diff_metrics.json"

    with open(input_path) as f:
        lines = f.readlines()

    metrics = extract_metrics(lines)

    with open(output_path, "w") as f:
        json.dump(metrics, f, indent=2)

    print(f"Wrote metrics to {output_path}: {metrics}")
