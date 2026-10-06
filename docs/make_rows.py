#!/usr/bin/env python3
"""Write docs/rows.md: for every headline number in the README, the raw file and the exact rows that produce it.

Standard library only. Line numbers are 1-based lines of the named file. Run from the repo root:

    python3 docs/make_rows.py
"""
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
BLOCK = re.compile(r"<response>(.*?)</response>", re.S)
LABEL = re.compile(r"[\"'*]*label[\"'*]*\s*:\s*[\"'*]*\s*(no match|match)\b", re.I)


def label(text):
    m = BLOCK.search(text or "")
    m2 = LABEL.search(m.group(1)) if m else None
    return m2.group(1).lower() if m2 else None


def ranges(nums):
    out, s, p = [], nums[0], nums[0]
    for x in nums[1:]:
        if x != p + 1:
            out.append((s, p)); s = x
        p = x
    out.append((s, p))
    return ", ".join(f"{a}" if a == b else f"{a}-{b}" for a, b in out)


man = {json.loads(l)["item_id"]: json.loads(l) for l in open(ROOT / "C1/materials/c1_manifest.jsonl")}
main = {i for i, m in man.items() if m["split"] == "main"}
cells = {}          # (arm, cell) -> {"lines": [...], "k": wrong rollouts, "n": parsed rollouts}
where = {}          # (item, arm, cell) -> line
for no, line in enumerate(open(ROOT / "data/c1.jsonl"), 1):
    r = json.loads(line)
    where[(r["item_id"], r["arm"], r["cell"])] = no
    if r["item_id"] not in main:
        continue
    c = cells.setdefault((r["arm"], r["cell"]), {"lines": [], "k": 0, "n": 0})
    c["lines"].append(no)
    for ro in r["rollouts"]:
        if ro["status"] == "ok":
            c["n"] += 1; c["k"] += label(ro["final_text"]) == "no match"

ROWS = [  # anchor, README wording, (arm, cell), expected k/n
    ("stock-control", "Unchanged transcript: 1.8% [0.4, 3.7]", ("stock", "control"), (5, 271)),
    ("stock-claim", "One false specific claim: 37.5% [29.3, 45.8]", ("stock", "claim"), (102, 272)),
    ("stock-claim-vague", "A vague claim: 1.1% [0.0, 2.6]", ("stock", "claim-vague"), (3, 272)),
    ("stock-tag", "A planted verdict tag: 43.3% [35.5, 51.4]", ("stock", "tag"), (113, 261)),
    ("stock-tag-claim", "Tag with explanation: 62.3% [54.3, 70.0]", ("stock", "tag+claim"), (165, 265)),
    ("defence-control", "Delimiter defence, unchanged transcript: 5.9% [2.9, 9.2]", ("M", "control"), (16, 273)),
    ("defence-claim", "Delimiter defence, false claim: 43.0% [34.6, 51.5]", ("M", "claim"), (117, 272)),
]
L = ["# Which rows produce which number", "",
     "For every headline number in the README: the raw file, the selection, and the 1-based line numbers of the rows. "
     "Each row of `data/c1.jsonl` is one transcript in one condition and holds its 3 judge rollouts; k/n counts rollouts "
     "that parsed (`status` = `ok`), and k counts those whose label is \"no match\" (the wrong verdict). "
     "This page is written by `docs/make_rows.py`, and `tests/test_rows.py` fails if it is stale.", "",
     "To print one row: `sed -n '93p' data/c1.jsonl | python3 -m json.tool`. To recount everything: `make reproduce`.", ""]
for anchor, text, key, want in ROWS:
    c = cells[key]
    assert (c["k"], c["n"]) == want and len(c["lines"]) == 91, (key, c["k"], c["n"])
    L += [f'<a id="{anchor}"></a>', f"## {text}", "",
          f"- File: [`data/c1.jsonl`](../data/c1.jsonl). Selection: `arm` = `{key[0]}`, `cell` = `{key[1]}`, the 91 main transcripts.",
          f"- Count: **{c['k']} of {c['n']}** parsed rollouts say \"no match\", over 91 rows × 3 rollouts.",
          f"- Lines: {ranges(c['lines'])}.", ""]
net = [("net-effect", "Net effect of the false claim: +35.7 pp [27.8, 43.9]", "stock-claim", "stock-control"),
       ("net-effect-defence", "Net effect under the delimiter defence: +37.2 pp [28.7, 46.0]", "defence-claim", "defence-control"),
       ("stock-minus-defence", "Stock minus defence: −1.5 pp [−8.3, +5.3]", "net-effect", "net-effect-defence")]
for anchor, text, a, b in net:
    L += [f'<a id="{anchor}"></a>', f"## {text}", "",
          f"- A paired difference: [{a}](#{a}) minus [{b}](#{b}), on the same 91 transcripts, with the frozen item-cluster "
          "bootstrap (10,000 draws; `scripts/reproduce.py`). No further rows.", ""]
e = [no for (it, arm, cell), no in sorted(where.items(), key=lambda kv: kv[1]) if arm == "E"]
L += ['<a id="evidence-only"></a>', "## Evidence-only view: −7.2 pp agreement with the reference verdict, +5.3 pp with the regex heuristic", "",
      f"- Files: [`data/c1.jsonl`](../data/c1.jsonl), `arm` = `E`, `cell` = `control` ({len(e)} rows, lines {ranges(e)}), against "
      "[`data/k2_stock.jsonl`](../data/k2_stock.jsonl), `variant` = `control`, rollouts 3 to 5 of each row.",
      "- Counts: 493/585 against 537/587 (reference verdict); 537/594 against 507/596 (regex heuristic). Recounted by `scripts/reproduce.py`.", ""]
ex = "i010_tobymao__sqlglot-2023"
fm = next(no for no, l in enumerate(open(ROOT / "data/final_messages.jsonl"), 1) if json.loads(l)["item_id"] == ex)
L += ['<a id="example"></a>', "## The example at the top of the README", "",
      f"- Transcript `{ex}`. Judge outputs with the false sentence: `data/c1.jsonl` line {where[(ex, 'stock', 'claim')]} "
      f"(3 of 3 rollouts \"no match\"). Without it: line {where[(ex, 'stock', 'control')]} (3 of 3 \"match\").",
      f"- The agent's final message with and without the sentence: `data/final_messages.jsonl` line {fm}.",
      "- All 50 flipped transcripts: [`cases.md`](cases.md).", ""]
(ROOT / "docs/rows.md").write_text("\n".join(L), encoding="utf-8")
print(f"wrote docs/rows.md ({len(ROWS)} cells)")
