"""Checks for the result files of the two earlier tests (K1, K2) and the copy of the C1 write-up.

Standard library only. Agent-written (Claude), 2026-10-07.
"""
import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]


class TestEarlierTests(unittest.TestCase):
    def test_c1_result_copy_is_identical(self):
        self.assertEqual((ROOT / "C1/RESULT.md").read_bytes(), (ROOT / "docs/RESULT.md").read_bytes())

    def test_k1_numbers(self):
        r = json.load(open(ROOT / "K1/results/k1_results.json"))
        q = r["judges"]["qwen2.5-32b"]
        self.assertEqual(r["decision"], "STOP")
        self.assertEqual(r["judges_in_rule"], ["qwen2.5-32b"])
        self.assertEqual((q["H_stock"]["num"], q["H_stock"]["den"]), (1, 3494))
        self.assertEqual((q["H_patched"]["num"], q["H_patched"]["den"]), (1, 3494))
        self.assertEqual(q["status_counts"]["ok"], 4686)
        self.assertEqual((q["flip_opposite_stock"]["num"], q["flip_opposite_stock"]["den"]), (726, 1715))
        # the looser count exists only in the independent recount, which is prose
        v = (ROOT / "K1/VERIFY.md").read_text(encoding="utf-8")
        self.assertIn("568/3494 (16.3%) under both parsers", v)
        self.assertIn("4686/4686", v)
        self.assertIn("1/3494", (ROOT / "K1/RESULT.md").read_text(encoding="utf-8"))

    def test_k2_numbers(self):
        r = json.load(open(ROOT / "K2/results/k2_results.json"))
        self.assertEqual(r["decision"], "INCONCLUSIVE")
        self.assertFalse(r["guard_passed"])
        s, m = r["arms"]["stock"]["adoption"], r["arms"]["M"]["adoption"]
        self.assertEqual((s["k"], s["n"], m["k"], m["n"]), (728, 1720, 609, 1742))
        red = r["reduction"]
        self.assertEqual([round(100 * x, 1) for x in (red["est"], *red["ci"])], [7.4, 5.1, 9.7])
        self.assertEqual(round(100 * r["guard_agreement_M_minus_stock"]["est"], 1), -4.2)


if __name__ == "__main__":
    unittest.main()
