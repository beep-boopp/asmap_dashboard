"""
compare_runs.py

Loads two run manifests and the extracted diff metrics, then produces a
verdict that distinguishes expected BGP churn (e.g. routine AWS ASN
re-announcements) from anomalies (e.g. data-source mismatch or unexpected
prefix hijacks).

Inputs:  data/diff_jan_feb.txt, data/diff_feb_mar.txt, two manifest files
Outputs: data/result.json containing the verdict and supporting evidence
"""

import json
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from diff_extractor import extract_metrics

AWS_ASNS = {"AS14618", "AS16509"}


def load_json(path):
    with open(path) as f:
        return json.load(f)


def compute_baseline(ipv4_changes):
    mean = ipv4_changes
    return {
        "mean": mean,
        "lower_bound": int(mean * 0.8),
        "upper_bound": int(mean * 1.2),
    }


def detect_provenance_mismatches(a, b):
    mismatches = []
    if a.get("routeviews_month") != b.get("routeviews_month"):
        mismatches.append("RouteViews month mismatch")
    if a.get("rpki_success") != b.get("rpki_success"):
        mismatches.append("RPKI success mismatch")
    if a.get("irr_retries") != b.get("irr_retries"):
        mismatches.append("IRR retry difference")
    return mismatches


def detect_expected_patterns(metrics):
    for pair in metrics.get("top_asn_pairs", []):
        if AWS_ASNS.intersection(pair):
            return ["large ASN churn pattern detected"]
    return []


def build_explanation(current_ipv4, baseline, provenance_mismatches, verdict):
    range_str = f"{baseline['lower_bound']}–{baseline['upper_bound']}"
    in_range = baseline["lower_bound"] <= current_ipv4 <= baseline["upper_bound"]
    position = "within baseline" if in_range else "outside baseline"

    if provenance_mismatches:
        mismatch = provenance_mismatches[0]
        return (
            f"~{current_ipv4} IPv4 changes observed ({position} {range_str}), "
            f"but {mismatch} detected, suggesting inconsistent data sources."
        )
    if verdict == "normal":
        return (
            f"~{current_ipv4} IPv4 changes observed (within baseline {range_str}), "
            f"no data source mismatch detected."
        )
    return (
        f"~{current_ipv4} IPv4 changes observed (outside baseline {range_str}), "
        f"churn level is unusual."
    )


if __name__ == "__main__":
    with open("data/diff_jan_feb.txt") as f:
        baseline_metrics = extract_metrics(f.readlines())

    with open("data/diff_feb_mar.txt") as f:
        current_metrics = extract_metrics(f.readlines())

    baseline = compute_baseline(baseline_metrics["ipv4_changes"])
    current_ipv4 = current_metrics["ipv4_changes"]

    manifest_jan = load_json("data/manifest_jan.json")
    manifest_feb = load_json("data/manifest_feb.json")

    provenance_mismatches = detect_provenance_mismatches(manifest_jan, manifest_feb)
    expected_patterns_detected = detect_expected_patterns(current_metrics)

    in_range = baseline["lower_bound"] <= current_ipv4 <= baseline["upper_bound"]

    if provenance_mismatches:
        verdict = "suspicious"
    elif not in_range:
        verdict = "suspicious"
    else:
        verdict = "normal"

    explanation = build_explanation(current_ipv4, baseline, provenance_mismatches, verdict)

    result = {
        "baseline": baseline,
        "current": {"ipv4_changes": current_ipv4},
        "provenance_mismatches": provenance_mismatches,
        "expected_patterns_detected": expected_patterns_detected,
        "verdict": verdict,
        "explanation": explanation,
    }

    with open("data/result.json", "w") as f:
        json.dump(result, f, indent=2)

    print(f"Wrote result to data/result.json")
    print(json.dumps(result, indent=2))
