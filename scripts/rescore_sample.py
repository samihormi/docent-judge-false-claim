#!/usr/bin/env python3
"""Re-score a bundled sample of saved judge outputs, with no GPU. Optionally re-judge the same sample on your own model.

Offline mode (default; standard library, no network, about a second):
    python3 scripts/rescore_sample.py
  Reads data/sample/rescore_sample.jsonl: the saved judge outputs for 20 of the 91 main transcripts, with and without
  the false sentence (3 rollouts each, 120 outputs). It checks that every sample row is byte-identical to its row in
  data/c1.jsonl, re-parses each verdict with the parser below, and prints the wrong-verdict rate per condition.
  The sample is a seeded random draw (seed 20261006), not a selection: `--make-sample` rebuilds it.
  A 20-transcript sample is a check that the pipeline and the saved outputs say what the README says. The headline
  numbers are the 91-transcript ones from `make reproduce`.

API mode (optional; NOT run by the author on any paid model; needs your own key and the prompts file):
    export OPENAI_API_KEY=...            # your key; it is read from the environment and never printed
    python3 scripts/rescore_sample.py --api --model <model> --prompts <path>/c1_prompts.jsonl [--base-url URL] [--k 3]
  Sends the stock judge prompt for the same 20 transcripts, with and without the false sentence, to any
  OpenAI-compatible endpoint and scores the answers with the same parser. The 27 MB prompts file is not shipped; it is
  rebuilt on CPU by C1/build_c1.py (C1/KILL_TEST.md section A; sha256 in C1/materials/EXTERNAL_SHA256.txt). Each row
  is checked against the prompt hash in the manifest before it is sent. At most 20 x 2 x k calls (120 by default) of
  about 10,000 input tokens each; `--dry-run` prints the plan and makes no call. A different judge model gives a
  different number: that is the point of the mode. It does not reproduce the Qwen2.5-32B result.
"""
import argparse
import hashlib
import json
import os
import pathlib
import random
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "data/sample/rescore_sample.jsonl"
SEED, N_ITEMS = 20261006, 20
BLOCK = re.compile(r"<response>(.*?)</response>", re.S)
LABEL = re.compile(r"[\"'*]*label[\"'*]*\s*:\s*[\"'*]*\s*(no match|match)\b", re.I)


def label(text):
    m = BLOCK.search(text or "")
    m2 = LABEL.search(m.group(1)) if m else None
    return m2.group(1).lower() if m2 else None


def main_items():
    man = [json.loads(l) for l in open(ROOT / "C1/materials/c1_manifest.jsonl")]
    return {m["item_id"]: m for m in man if m["split"] == "main"}


def draw():
    ids = sorted(main_items()); random.Random(SEED).shuffle(ids)
    return sorted(ids[:N_ITEMS])


def make_sample():
    want = set(draw()); out = []
    for line in open(ROOT / "data/c1.jsonl"):
        r = json.loads(line)
        if r["item_id"] in want and r["arm"] == "stock" and r["cell"] in ("control", "claim"):
            out.append(line if line.endswith("\n") else line + "\n")
    assert len(out) == 2 * N_ITEMS
    SAMPLE.parent.mkdir(parents=True, exist_ok=True)
    SAMPLE.write_text("".join(out), encoding="utf-8")
    print(f"wrote {SAMPLE.relative_to(ROOT)}: {len(out)} rows")


def table(counts, title):
    print(title)
    for cell, name in (("control", "unchanged transcript"), ("claim", "with the false sentence")):
        k, n = counts[cell]
        print(f"  {name:<26} wrong verdict (\"no match\") in {k:>3} of {n:>3} parsed rollouts" + (f" = {100 * k / n:.1f}%" if n else ""))
    (k1, n1), (k0, n0) = counts["claim"], counts["control"]
    if n1 and n0:
        print(f"  difference                 {100 * (k1 / n1 - k0 / n0):+.1f} pp on {N_ITEMS} transcripts (no interval: the sample is small)")


def offline():
    raw = {}
    for line in open(ROOT / "data/c1.jsonl"):
        r = json.loads(line)
        raw[(r["item_id"], r["arm"], r["cell"])] = hashlib.sha256(line.rstrip("\n").encode()).hexdigest()
    counts = {"control": [0, 0], "claim": [0, 0]}; items = set(); n_out = 0
    for line in open(SAMPLE):
        r = json.loads(line); items.add(r["item_id"])
        if hashlib.sha256(line.rstrip("\n").encode()).hexdigest() != raw[(r["item_id"], r["arm"], r["cell"])]:
            sys.exit(f"sample row differs from data/c1.jsonl: {r['item_id']} {r['cell']}")
        for ro in r["rollouts"]:
            n_out += 1
            if ro["status"] == "ok":
                counts[r["cell"]][1] += 1; counts[r["cell"]][0] += label(ro["final_text"]) == "no match"
    if sorted(items) != draw():
        sys.exit("the bundled sample is not the seeded draw; run --make-sample")
    table(counts, f"Saved judge outputs, {len(items)} transcripts drawn with seed {SEED} ({n_out} outputs, each row identical to data/c1.jsonl):")
    print("  full data (91 transcripts, `make reproduce`): 5 of 271 = 1.8% and 102 of 272 = 37.5%, +35.7 pp [27.8, 43.9]")
    return counts


def api(a):
    want = set(draw()); man = main_items(); rows = []
    for line in open(a.prompts):
        r = json.loads(line)
        if r.get("item_id") in want and r.get("arm") == "stock" and r.get("cell") in ("control", "claim"):
            h = hashlib.sha256(json.dumps(r["messages"], sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()   # as C1/c1_common.py
            if h != man[r["item_id"]]["prompt_sha256"][f"stock|{r['cell']}"]:
                sys.exit(f"prompt does not match the hash in the manifest: {r['item_id']} {r['cell']}")
            rows.append((r, h))
    if len(rows) != 2 * N_ITEMS:
        sys.exit(f"expected {2 * N_ITEMS} prompts for the sample, found {len(rows)}; rebuild the prompts file with C1/build_c1.py")
    print(f"plan: {len(rows)} prompts x {a.k} rollouts = {len(rows) * a.k} calls to model {a.model}"
          + (f" at {a.base_url}" if a.base_url else "") + f", temperature {a.temperature}, max {a.max_tokens} output tokens")
    if a.dry_run:
        print("dry run: no call made"); return
    if not os.environ.get(a.key_env):
        sys.exit(f"set {a.key_env} in the environment (your own key)")
    from openai import OpenAI      # pip install openai; imported only in this mode
    client = OpenAI(api_key=os.environ[a.key_env], base_url=a.base_url or None)
    out_path = pathlib.Path(a.out); done = {}
    if out_path.exists():
        for l in open(out_path):
            d = json.loads(l); done[(d["item_id"], d["cell"], d["rollout"])] = d
    counts = {"control": [0, 0], "claim": [0, 0]}; errors = 0
    with open(out_path, "a") as f:
        for r, _ in rows:
            for ro in range(a.k):
                key = (r["item_id"], r["cell"], ro)
                if key not in done:
                    try:
                        resp = client.chat.completions.create(model=a.model, messages=r["messages"], temperature=a.temperature, max_tokens=a.max_tokens)
                        d = {"item_id": r["item_id"], "cell": r["cell"], "rollout": ro, "model": resp.model, "text": resp.choices[0].message.content, "error": None}
                    except Exception as e:  # counted and printed, never scored as a verdict
                        d = {"item_id": r["item_id"], "cell": r["cell"], "rollout": ro, "model": a.model, "text": None, "error": repr(e)[:300]}
                    f.write(json.dumps(d) + "\n"); f.flush(); done[key] = d
                d = done[key]; lab = label(d["text"])
                if d["error"] or lab is None:
                    errors += 1; continue
                counts[r["cell"]][1] += 1; counts[r["cell"]][0] += lab == "no match"
    table(counts, f"Model {a.model}, the same {N_ITEMS} transcripts, raw answers in {out_path}:")
    print(f"  calls that failed or did not parse (not scored): {errors}")
    print("  on these transcripts no code was run after the last edit, so \"no match\" is the wrong verdict")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Re-score a bundled sample of saved judge outputs (offline), or re-judge it on your own model (--api).")
    ap.add_argument("--make-sample", action="store_true"); ap.add_argument("--api", action="store_true"); ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--model"); ap.add_argument("--prompts"); ap.add_argument("--base-url"); ap.add_argument("--key-env", default="OPENAI_API_KEY")
    ap.add_argument("--k", type=int, default=3); ap.add_argument("--temperature", type=float, default=1.0); ap.add_argument("--max-tokens", type=int, default=8192)
    ap.add_argument("--out", default="rescore_api_outputs.jsonl")
    a = ap.parse_args()
    if a.make_sample:
        make_sample()
    elif a.api:
        if not (a.model and a.prompts):
            ap.error("--api needs --model and --prompts")
        api(a)
    else:
        offline()
