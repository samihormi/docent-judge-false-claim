"""Checks for the reader-facing additions (Oct 2026): the final-message excerpts and docs/cases.md.

Standard library only. Agent-written (Claude), 2026-10-06.
"""
import json
import pathlib
import subprocess
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "C1"))
import c1_common as C  # noqa: E402


class TestCases(unittest.TestCase):
    def test_final_messages_match_manifest_and_construction(self):
        man = {json.loads(l)["item_id"]: json.loads(l) for l in open(ROOT / "C1/materials/c1_manifest.jsonl")}
        rows = [json.loads(l) for l in open(ROOT / "data/final_messages.jsonl")]
        self.assertEqual(sorted(r["item_id"] for r in rows), sorted(i for i, m in man.items() if m["split"] == "main"))
        for r in rows:
            m = man[r["item_id"]]
            self.assertEqual(r["prompt_sha256_control"], m["prompt_sha256"]["stock|control"])
            self.assertEqual(r["prompt_sha256_claim"], m["prompt_sha256"]["stock|claim"])
            sent = C.CLAIM_FMT.format(cmd=m["cmd"])
            ctl, clm = r["final_message_control"], r["final_message_claim"]
            self.assertNotIn(sent, ctl)
            self.assertEqual(clm.count(sent), 1)
            # the claim message is the control message plus the one sentence, placed before the last code fence
            self.assertEqual("".join(clm.replace(sent, "").split()), "".join(ctl.split()))
            self.assertLess(clm.index(sent), clm.rindex("submit"))

    def test_cases_page_is_current(self):
        before = (ROOT / "docs/cases.md").read_bytes()
        subprocess.run([sys.executable, str(ROOT / "docs/make_cases.py")], check=True, capture_output=True)
        self.assertEqual((ROOT / "docs/cases.md").read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
