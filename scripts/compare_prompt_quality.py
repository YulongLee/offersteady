#!/usr/bin/env python3
from __future__ import annotations
import argparse
import json
from pathlib import Path

GATES = ("fabrication", "sourceIsolation", "privacy", "completeCodeAnswer")

def load(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"invalid_report:{path}")
    return value

def compare(baseline: dict, candidate: dict) -> dict:
    old, new = baseline.get("safetyGates", {}), candidate.get("safetyGates", {})
    regressions = [gate for gate in GATES if old.get(gate) in {"required", "pass", True} and new.get(gate) not in {"pass", True}]
    old_score = float(baseline.get("qualityScore", 0) or 0)
    new_score = float(candidate.get("qualityScore", 0) or 0)
    return {"eligible": not regressions and new_score >= old_score, "safetyRegressions": regressions, "qualityDelta": round(new_score - old_score, 4)}

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("baseline", type=Path)
    parser.add_argument("candidate", type=Path)
    args = parser.parse_args()
    result = compare(load(args.baseline), load(args.candidate))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result["eligible"] else 2)

if __name__ == "__main__":
    main()
