"""Checks for the no-GPU re-run path (Oct 2026): docs/rows.md and the bundled re-score sample.

Standard library only.
"""
import json
import pathlib
import subprocess
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]


class TestRescore(unittest.TestCase):
    def test_rows_page_is_current(self):
        before = (ROOT / "docs/rows.md").read_bytes()
        subprocess.run([sys.executable, str(ROOT / "docs/make_rows.py")], check=True, capture_output=True)
        self.assertEqual((ROOT / "docs/rows.md").read_bytes(), before)

    def test_offline_rescore_of_the_bundled_sample(self):
        out = subprocess.run([sys.executable, str(ROOT / "scripts/rescore_sample.py")], check=True, capture_output=True, text=True).stdout
        self.assertIn("2 of  60", out)       # unchanged transcript, sample
        self.assertIn("22 of  60", out)      # with the false sentence, sample
        rows = [json.loads(l) for l in open(ROOT / "data/sample/rescore_sample.jsonl")]
        self.assertEqual(len(rows), 40)
        self.assertEqual(len({r["item_id"] for r in rows}), 20)

    def test_api_mode_makes_no_call_without_being_asked(self):
        # --api needs explicit --model and --prompts; without them the script exits before any import of a client
        r = subprocess.run([sys.executable, str(ROOT / "scripts/rescore_sample.py"), "--api"], capture_output=True, text=True)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("--api needs --model and --prompts", r.stderr)


if __name__ == "__main__":
    unittest.main()
