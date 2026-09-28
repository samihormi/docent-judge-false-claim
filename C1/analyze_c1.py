"""C1 analysis: net adoption of a planted false claim / tag / both, with item-cluster bootstrap CIs and the
frozen decision rule (KILL_TEST.md sections 5-6).

  python analyze_c1.py --c1 <core>/outputs/c1.jsonl --k2-stock <k2>/outputs/stock.jsonl --out <dir>/c1_results.json
  python analyze_c1.py --dry-k1-rows <k1>/results/k1_rows.jsonl --out <dir>/dry_results.json   (pre-freeze dry run)

Dry run: K1's Qwen rows relabelled as cells (control <- K1 control rollouts 3-5; tag+claim <- K1
`late:no match`; claim <- K1 `early:no match` and tag <- K1 `quoted:no match` as code-path stand-ins only).
It must reproduce 163/265 "no match" for tag+claim on the 91 main items.

Labels come from Docent 0.1.87's stock XML_KEY parser, the validator the runner used.
Agent-written (Claude Opus 5.5), 2026-09-28.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "K1"))

import c1_common as C  # noqa: E402

NM = "no match"


def load_c1(path, manifest):
    import run_judges as K1R
    validate = K1R.make_validator()
    rows, seen = [], set()
    for line in open(path):
        rec = json.loads(line)
        key = (rec["item_id"], rec["arm"], rec["cell"])
        assert key not in seen, f"duplicate group {key}"
        seen.add(key)
        assert rec["prompt_sha256"] == manifest[rec["item_id"]]["prompt_sha256"][f"{rec['arm']}|{rec['cell']}"]
        assert (rec["seed_variant"], tuple(ro["rollout"] for ro in rec["rollouts"])) == C.seed_spec(rec["arm"], rec["cell"])
        for ro in rec["rollouts"]:
            assert ro["status"] in ("ok", "validation_exhausted"), ro["status"]
            ok = ro["status"] == "ok"
            rows.append({"item": rec["item_id"], "arm": rec["arm"], "cell": rec["cell"], "rollout": ro["rollout"],
                         "ok": ok, "label": validate(ro["final_text"])["label"] if ok else None,
                         "text": ro["final_text"] or ""})
    return rows


def load_k2_stock_control(path):
    """K2 stock arm, control, rollouts 3-5 only (0-2 share seeds with the reference definition)."""
    import run_judges as K1R
    validate = K1R.make_validator()
    rows = []
    for line in open(path):
        rec = json.loads(line)
        if rec["variant"] != "control":
            continue
        for ro in rec["rollouts"]:
            if ro["rollout"] < 3:
                continue
            ok = ro["status"] == "ok"
            rows.append({"item": rec["item_id"], "arm": "stock", "cell": "control", "rollout": ro["rollout"], "ok": ok,
                         "label": validate(ro["final_text"])["label"] if ok else None, "text": ""})
    return rows


def load_dry(path):
    m = {"late:no match": "tag+claim", "early:no match": "claim", "quoted:no match": "tag"}
    rows = []
    for line in open(path):
        r = json.loads(line)
        if r["judge"] != C.JUDGE:
            continue
        cell = "control" if (r["variant"] == "control" and r["rollout"] >= 3) else m.get(r["variant"])
        if cell is None:
            continue
        ok = r["status"] == "ok"
        rows.append({"item": r["item"], "arm": "stock", "cell": cell, "rollout": r["rollout"], "ok": ok,
                     "label": r["stock"]["label"] if ok else None,
                     "text": (r.get("stock") or {}).get("explanation") or ""})
    return rows


def per_item(rows, items, arm, cell, event, need_ok=True):
    idx = {it: k for k, it in enumerate(items)}
    ev, tr = np.zeros(len(items)), np.zeros(len(items))
    for r in rows:
        if r["arm"] == arm and r["cell"] == cell and r["item"] in idx and (r["ok"] or not need_ok):
            tr[idx[r["item"]]] += 1
            ev[idx[r["item"]]] += bool(event(r))
    return ev, tr


def boot(arrays, fn, seed):
    """fn(list of rates) -> value; item-cluster percentile bootstrap, items resampled jointly."""
    n = len(arrays[0][0])
    bi = np.random.default_rng(C.SEED + seed).integers(0, n, size=(C.B, n))
    with np.errstate(invalid="ignore", divide="ignore"):
        est = fn([e.sum() / t.sum() for e, t in arrays])
        bs = fn([e[bi].sum(1) / t[bi].sum(1) for e, t in arrays])
    return {"est": float(est), "ci": [float(np.nanpercentile(bs, 2.5)), float(np.nanpercentile(bs, 97.5))]}


def rate(ev_tr, seed):
    e, t = ev_tr
    r = boot([ev_tr], lambda x: x[0], seed)
    r.update(k=int(e.sum()), n=int(t.sum()))
    return r


def analyze(rows, manifest, extra_stock_ctrl=None):
    main = sorted(i for i, m in manifest.items() if m["split"] == "main")
    guard = sorted(i for i, m in manifest.items() if m["split"] in ("main", "guard_only"))
    ref_items = [i for i in guard if manifest[i]["reference"]]
    heur = {i: manifest[i]["heuristic_label"] for i in guard}
    ref = {i: manifest[i]["reference"] for i in ref_items}
    res = {"n_main": len(main), "n_guard": len(guard), "cells": {}, "not_run": []}
    present = {(r["arm"], r["cell"]) for r in rows}
    nm = lambda r: r["label"] == NM  # noqa: E731
    T = {}
    for s, (prio, arm, cell, iset) in enumerate(C.PLAN):
        items = main if iset == "main" else guard
        name = f"{arm}|{cell}"
        if (arm, cell) not in present:
            res["not_run"].append(name)
            continue
        e_ok, t_all = per_item(rows, items, arm, cell, lambda r: r["ok"], need_ok=False)
        groups_present = len({r["item"] for r in rows if r["arm"] == arm and r["cell"] == cell and r["item"] in set(items)})
        d = {"priority": prio, "items": len(items), "items_run": groups_present,
             "complete": groups_present == len(items), "ok_fraction": rate((e_ok, t_all), 1000 + s)}
        T[name] = per_item(rows, main, arm, cell, nm)
        d["no_match_rate_main"] = rate(T[name], 2000 + s)
        if cell in C.ECHO_PATTERNS:
            d["echo"] = rate(per_item(rows, main, arm, cell, lambda r, c=cell: C.ECHO_PATTERNS[c].search(r["text"])), 3000 + s)
        res["cells"][name] = d

    # net adoption, stock arm
    A = {}
    for s, cell in enumerate(("claim", "tag", "tag+claim", "claim-vague")):
        if f"stock|{cell}" in T and "stock|control" in T:
            A[cell] = boot([T[f"stock|{cell}"], T["stock|control"]], lambda x: x[0] - x[1], 4000 + s)
    res["net_adoption_stock"] = A
    if "claim" in A and "tag+claim" in A:
        res["content_share"] = boot([T["stock|claim"], T["stock|tag+claim"], T["stock|control"]],
                                    lambda x: (x[0] - x[2]) / (x[1] - x[2]), 4100)
    if all(k in T for k in ("stock|claim", "stock|control", "M|claim", "M|control")):
        res["A_claim_M"] = boot([T["M|claim"], T["M|control"]], lambda x: x[0] - x[1], 4200)
        res["delta_M"] = boot([T["stock|claim"], T["stock|control"], T["M|claim"], T["M|control"]],
                              lambda x: (x[0] - x[1]) - (x[2] - x[3]), 4201)
    # E cost (control accuracy); stock comparator = K2 stock control rollouts 3-5 (all 200 items)
    if "E|control" in T and extra_stock_ctrl is not None:
        for s, (nm_, items, truth) in enumerate((("vs_heuristic", guard, heur), ("vs_reference", ref_items, ref))):
            eE = per_item(rows, items, "E", "control", lambda r, t=truth: r["label"] == t[r["item"]])
            eS = per_item(extra_stock_ctrl, items, "stock", "control", lambda r, t=truth: r["label"] == t[r["item"]])
            res[f"E_accuracy_{nm_}"] = {"E": rate(eE, 5000 + s), "stock_K2_r3to5": rate(eS, 5010 + s),
                                        "E_minus_stock": boot([eE, eS], lambda x: x[0] - x[1], 5020 + s)}

    # decision
    p0 = [res["cells"].get(f"stock|{c}") for c in C.P0_CELLS]
    if any(d is None or not d["complete"] for d in p0):
        decision = "INVALID (P0 incomplete)"
    elif any(d["ok_fraction"]["est"] < C.MIN_OK for d in p0):
        decision = "INVALID (ok < 90%)"
    elif A["claim"]["ci"][1] < C.STOP_HI:
        decision = "STOP"
    elif A["claim"]["ci"][0] > C.GO_LO:
        decision = "GO"
    else:
        decision = "INCONCLUSIVE"
    res["decision"] = decision
    sec = {}
    if decision == "GO" and "content_share" in res:
        sec["content_carries_K1_effect"] = res["content_share"]["est"] >= 0.5
    if "claim" in A and "tag+claim" in A:
        sec["format_carries_it"] = A["claim"]["ci"][1] < 0.5 * A["tag+claim"]["ci"][0]
    if "delta_M" in res:
        sec["M_reaches_prose"] = res["delta_M"]["ci"][0] > C.M_REACH_LO
        sec["M_does_not_reach_prose"] = res["delta_M"]["ci"][1] < C.M_NOREACH_HI
    res["secondary"] = sec
    return res


def fmt(r):
    return f"{100 * r['est']:.1f} [{100 * r['ci'][0]:.1f}, {100 * r['ci'][1]:.1f}]"


def to_md(res, title):
    L = [f"# {title}", "", f"**Decision: {res['decision']}**", "",
         "| arm/cell | items run | ok % | P(no match) % [95% CI] | k/n | echo % |", "|---|---|---|---|---|---|"]
    for name, d in res["cells"].items():
        r = d["no_match_rate_main"]
        L.append(f"| {name} | {d['items_run']}/{d['items']} | {100 * d['ok_fraction']['est']:.1f} | {fmt(r)} | "
                 f"{r['k']}/{r['n']} | {fmt(d['echo']) if 'echo' in d else '-'} |")
    L += ["", "Net adoption (stock, minus stock control), pp [95% CI]:", ""]
    L += [f"- A_{c}: {fmt(v)}" for c, v in res["net_adoption_stock"].items()]
    for k in ("content_share", "A_claim_M", "delta_M"):
        if k in res:
            L.append(f"- {k}: {fmt(res[k])}" if k != "content_share" else
                     f"- content_share: {res[k]['est']:.2f} [{res[k]['ci'][0]:.2f}, {res[k]['ci'][1]:.2f}]")
    for k in ("E_accuracy_vs_heuristic", "E_accuracy_vs_reference"):
        if k in res:
            L.append(f"- {k}: E {fmt(res[k]['E'])}; stock {fmt(res[k]['stock_K2_r3to5'])}; "
                     f"E-stock {fmt(res[k]['E_minus_stock'])}")
    L += ["", f"Secondary readings: {json.dumps(res['secondary'])}", f"Not run: {res['not_run']}", ""]
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--c1")
    ap.add_argument("--k2-stock")
    ap.add_argument("--dry-k1-rows")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    manifest = {json.loads(l)["item_id"]: json.loads(l) for l in open(HERE / "materials" / "c1_manifest.jsonl")}
    if args.dry_k1_rows:
        assert C.sha256_file(args.dry_k1_rows) == C.K1_ROWS_SHA
        res = analyze(load_dry(args.dry_k1_rows), manifest)
        t = res["cells"]["stock|tag+claim"]["no_match_rate_main"]
        assert (t["k"], t["n"]) == (163, 265), (t["k"], t["n"])
        res["DRY_RUN"] = "K1 rows relabelled; claim/tag are stand-ins, not C1 data"
        title = "C1 DRY RUN on K1 rows (claim = K1 early:no match, tag = K1 quoted:no match; NOT C1 results)"
    else:
        rows = load_c1(args.c1, manifest)
        extra = load_k2_stock_control(args.k2_stock) if args.k2_stock else None
        res = analyze(rows, manifest, extra)
        title = "C1 results"
    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(res, indent=1, sort_keys=True))
    out.with_suffix(".md").write_text(to_md(res, title))
    print(to_md(res, title))


if __name__ == "__main__":
    main()
