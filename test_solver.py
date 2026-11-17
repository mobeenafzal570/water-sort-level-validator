"""Behavioral checks for inventory errors, move legality, search, and replay."""

import copy
import json
from pathlib import Path
import unittest

from solver import Puzzle
from validate import audit_level, inventory_issues


def bottle(colors, capacity=4, receiver=False, goal="", locked=False, unlock=""):
    return dict(colors=colors, capacity=capacity, fixedReceiver=receiver,
                receiverColor=goal, lockEnabled=locked, unlockColor=unlock, noLockColor="")


def level(bottles, special=False):
    return dict(level=1, special=special, bottles=bottles)


class InventoryTests(unittest.TestCase):
    def test_insufficient_normal_color_is_rejected(self):
        result = audit_level(level([bottle(["Red"] * 3), bottle([])]))
        self.assertEqual(result["status"], "invalid_inventory")
        self.assertEqual(result["issues"][0]["kind"], "incomplete_color_set")

    def test_insufficient_collector_color_is_rejected(self):
        result = audit_level(level([bottle(["Red"] * 4),
                                    bottle([], 5, True, "Red")], True))
        self.assertIn("insufficient_goal_color", [i["kind"] for i in result["issues"]])

    def test_missing_unlock_color_is_rejected(self):
        result = audit_level(level([bottle(["Red"] * 4),
                                    bottle([], locked=True, unlock="Blue")]))
        self.assertIn("missing_unlock_color", [i["kind"] for i in result["issues"]])

    def test_overfilled_bottle_is_rejected(self):
        issues, _ = inventory_issues(level([bottle(["Red"] * 8)]))
        self.assertIn("overfilled_bottle", [i["kind"] for i in issues])

    def test_special_requires_one_receiver(self):
        issues, _ = inventory_issues(level([bottle(["Red"] * 4)], True))
        self.assertIn("expected_one_receiver", [i["kind"] for i in issues])


class SolverTests(unittest.TestCase):
    def setUp(self):
        self.data = level([bottle(["Red", "Blue", "Red", "Blue"]),
                           bottle(["Blue", "Red", "Blue", "Red"]),
                           bottle([]), bottle([])])

    def test_solution_replays_and_input_is_unchanged(self):
        before = copy.deepcopy(self.data)
        puzzle = Puzzle(self.data)
        result = puzzle.solve()
        self.assertEqual(result["status"], "solved")
        self.assertTrue(puzzle.won(puzzle.replay(result["moves"])))
        self.assertEqual(self.data, before)

    def test_wrong_top_color_is_not_a_move(self):
        puzzle = Puzzle(self.data)
        assignments = puzzle.assignments(puzzle.initial, (-1,) * puzzle.n)
        self.assertNotIn((0, 1), [(m[0], m[1]) for m, _, _ in puzzle.moves(
            puzzle.initial, assignments)])

    def test_illegal_replay_is_rejected(self):
        with self.assertRaises(ValueError):
            Puzzle(self.data).replay([(0, 1, 1)])

    def test_receiver_accepts_only_its_goal_color(self):
        puzzle = Puzzle(level([bottle(["Red", "Blue"]), bottle(["Red"] * 3),
                               bottle([], 4, True, "Red")], True))
        assignments = puzzle.assignments(puzzle.initial, (-1,) * puzzle.n)
        destinations = [(m[0], m[1]) for m, _, _ in puzzle.moves(puzzle.initial, assignments)]
        self.assertNotIn((0, 2), destinations)
        self.assertIn((1, 2), destinations)

    def test_node_limit_is_inconclusive(self):
        result = Puzzle(self.data).solve(max_nodes=0)
        self.assertEqual(result["status"], "search_limit")

    def test_dead_end_is_distinct_from_search_limit(self):
        data = level([bottle(["Red", "Blue", "Red", "Blue"]),
                      bottle(["Blue", "Red", "Blue", "Red"])])
        self.assertEqual(Puzzle(data).solve()["status"], "unsolvable")


class SnapshotTests(unittest.TestCase):
    def test_all_fifty_exported_levels_solve_and_replay(self):
        levels = json.loads(Path(__file__).with_name("levels.json").read_text())
        self.assertEqual(len(levels), 50)
        self.assertEqual([l["level"] for l in levels if l["special"]], [10, 20, 30])
        for data in levels:
            with self.subTest(level=data["level"]):
                result = audit_level(data)
                self.assertEqual(result["status"], "solved")
                self.assertTrue(result["replayVerified"])


if __name__ == "__main__":
    unittest.main()
