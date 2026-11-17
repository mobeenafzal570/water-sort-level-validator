"""Audit an exported WaterSort level snapshot; no third-party dependencies."""

import argparse
import collections
import json
from pathlib import Path

from solver import Puzzle


def inventory_issues(level):
    """Check the four-unit normal-bottle rules used by this game snapshot."""
    bottles = level["bottles"]
    issues = []
    counts = collections.Counter(
        color for bottle in bottles for color in bottle["colors"]
        if color and color != "Empty"
    )
    for index, bottle in enumerate(bottles):
        capacity = bottle["capacity"]
        occupied = sum(bool(c) and c != "Empty" for c in bottle["colors"])
        if not isinstance(capacity, int) or isinstance(capacity, bool) or capacity <= 0:
            issues.append({"kind": "invalid_capacity", "bottle": index})
        elif occupied > capacity:
            issues.append({"kind": "overfilled_bottle", "bottle": index})
        if not bottle["fixedReceiver"] and capacity != 4:
            issues.append({"kind": "unsupported_normal_capacity", "bottle": index})

    if level["special"]:
        receivers = [b for b in bottles if b["fixedReceiver"]]
        if len(receivers) != 1:
            issues.append({"kind": "expected_one_receiver"})
        for receiver in receivers:
            color = receiver["receiverColor"]
            if not color or color == "Empty":
                issues.append({"kind": "invalid_receiver_color"})
            elif counts[color] < receiver["capacity"]:
                issues.append({"kind": "insufficient_goal_color", "color": color,
                               "required": receiver["capacity"], "available": counts[color]})
            if any(c and c not in ("Empty", color) for c in receiver["colors"]):
                issues.append({"kind": "wrong_color_in_receiver"})
    else:
        if any(b["fixedReceiver"] for b in bottles):
            issues.append({"kind": "receiver_in_normal_level"})
        for color, count in counts.items():
            if count % 4:
                issues.append({"kind": "incomplete_color_set", "color": color, "units": count})
        for index, bottle in enumerate(bottles):
            color = bottle["unlockColor"]
            if bottle["lockEnabled"] and color and color not in counts:
                issues.append({"kind": "missing_unlock_color", "bottle": index, "color": color})
    return issues, dict(counts)


def audit_level(level, max_nodes=500000, seconds=20):
    issues, counts = inventory_issues(level)
    result = {"level": level["level"], "colorCounts": counts, "issues": issues}
    if issues:
        return dict(result, status="invalid_inventory")
    puzzle = Puzzle(level)
    result.update(puzzle.solve(max_nodes=max_nodes, seconds=seconds))
    if result["status"] == "solved":
        puzzle.replay(result["moves"])
        result["replayVerified"] = True
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", nargs="?", default="levels.json")
    parser.add_argument("--output", default="report.json")
    parser.add_argument("--max-nodes", type=int, default=500000)
    parser.add_argument("--seconds", type=float, default=20)
    args = parser.parse_args()
    if args.max_nodes <= 0 or args.seconds <= 0:
        parser.error("search limits must be positive")
    try:
        levels = json.loads(Path(args.source).read_text())
        if not isinstance(levels, list) or not levels:
            raise ValueError("source must be a non-empty list of levels")
        results = []
        for level in levels:
            result = audit_level(level, args.max_nodes, args.seconds)
            results.append(result)
            print("Level {}: {} ({} moves)".format(
                result["level"], result["status"], len(result.get("moves", []))), flush=True)
        Path(args.output).write_text(json.dumps(results, indent=2) + "\n")
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.exit(2, "Input error: {}\n".format(error))
    return 0 if all(r["status"] == "solved" for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
