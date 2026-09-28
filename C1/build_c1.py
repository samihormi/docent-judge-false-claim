"""Build the C1 judge prompts from K1's items.

  python build_c1.py --datadir <k1>/data --k1-prompts <k1>/items/prompts.jsonl --k1-rows <k1>/results/k1_rows.jsonl \
      --out <core>/items/c1_prompts.jsonl

Writes C1/materials/c1_manifest.jsonl (one row per item: split, {CMD}, per arm|cell prompt sha256).

Checks (any failure aborts):
  - K1's and K2's KILL_TEST.sha256 files verify (K1 analyze.py excepted: documented deviation D1);
  - K1 prompts/rows files match the hashes K2 froze;
  - main set = K1 scored items with heuristic "match" and K2 reference "match": exactly 91;
  - every stock `control` prompt equals K1's control prompt (sha256), every stock `tag+claim` prompt equals
    K1's `late:no match` prompt (sha256), for the 91 main items and the smoke item;
  - the inserted claim is false for every main item: K1's heuristic finds no code run after the last edit.

Agent-written (Claude Opus 5.5), 2026-09-28.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "K1"))
sys.path.insert(0, str(HERE.parent / "K2"))

import pyarrow.parquet as pq  # noqa: E402
from docent.data_models.agent_run import AgentRun  # noqa: E402
from docent.data_models.chat import AssistantMessage, SystemMessage, UserMessage  # noqa: E402
from docent.data_models.transcript import Transcript  # noqa: E402
from docent.judges.types import Rubric  # noqa: E402

import build_items as K1B  # noqa: E402
import k1_common as K1C  # noqa: E402
import k2_common as K2C  # noqa: E402

import c1_common as C  # noqa: E402

K1_ANALYZE_D1_SHA = "44aab8e35f43aca6a6fb5f732ff78b88ef948267bf4cbb8aa1757fc083fd75ed"


def verify_sha_file(d: pathlib.Path, exceptions: dict[str, str]):
    for line in (d / "KILL_TEST.sha256").read_text().splitlines():
        sha, name = line.split("  ", 1)
        got = C.sha256_file(d / name)
        assert got == exceptions.get(name, sha), f"{d.name}/{name}: sha256 mismatch"


def pick_cmd(ai_texts: list[str]) -> str:
    cmds = [K1C.last_command(t) for t in ai_texts]
    edits = [i for i, c in enumerate(cmds) if K1C.EDIT_CMD.match(c)]
    runs = [c for c in cmds[: edits[-1]] if "\n" not in c and C.RUN_START.match(c)]
    return runs[-1] if runs else C.DEFAULT_CMD


def render(tr, loc, cell: str, cmd: str, view: str):
    texts = [m["system_prompt"] if m["role"] == "system" else (m["text"] or "") for m in tr]
    ins = C.insert_text(cell, cmd)
    if ins == "K1":
        ins = K1C.plant_text("late", "no match")
    if ins is not None:
        texts[loc["ai_last"]] = K1B.insert_before_last_fence(texts[loc["ai_last"]], ins)
    if view == "E":  # evidence-only: each assistant message reduced to its last fenced command
        assert cell == "control"
        for i, m in enumerate(tr):
            if m["role"] == "ai":
                c = K1C.last_command(texts[i])
                texts[i] = f"```\n{c}\n```" if c else ""
    msgs = []
    for m, t in zip(tr, texts):
        cls = {"system": SystemMessage, "user": UserMessage, "ai": AssistantMessage}[m["role"]]
        msgs.append(cls(content=t))
    run = AgentRun(transcripts=[Transcript(messages=msgs)], metadata={})
    judge_msgs = Rubric(rubric_text=K1C.RUBRIC_TEXT).materialize_messages(run)
    return [{"role": jm.role, "content": jm.content} for jm in judge_msgs]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--datadir", required=True)
    ap.add_argument("--k1-prompts", required=True)
    ap.add_argument("--k1-rows", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    verify_sha_file(HERE.parent / "K1", {"analyze.py": K1_ANALYZE_D1_SHA})
    verify_sha_file(HERE.parent / "K2", {})
    assert C.sha256_file(args.k1_prompts) == C.K1_PROMPTS_SHA
    assert C.sha256_file(args.k1_rows) == C.K1_ROWS_SHA

    k1m = {json.loads(l)["item_id"]: json.loads(l) for l in open(HERE.parent / "K1" / "materials" / "items_manifest.jsonl")}
    k2m = {json.loads(l)["item_id"]: json.loads(l) for l in open(HERE.parent / "K2" / "materials" / "k2_manifest.jsonl")}
    scored = [i for i, m in k1m.items() if m["split"] == "scored"]
    smoke = [i for i, m in k1m.items() if m["split"] == "smoke"]
    assert len(scored) == C.N_GUARD and len(smoke) == 1 and set(scored) == set(k2m)
    main_items = [i for i in scored if k1m[i]["heuristic_label"] == "match" and k2m[i]["reference"] == "match"]
    assert len(main_items) == C.N_MAIN, len(main_items)

    k1p = {}
    for line in open(args.k1_prompts):
        r = json.loads(line)
        if r["variant"] in ("control", "late:no match"):
            k1p[(r["item_id"], r["variant"])] = r["prompt_sha256"]

    # original trajectories
    need = {k1m[i]["shard_row"]: i for i in scored + smoke}
    traj = {}
    for name, sha in sorted(K1C.SHARD_SHA256.items()):
        path = pathlib.Path(args.datadir) / name
        assert hashlib.sha256(path.read_bytes()).hexdigest() == sha
        tab = pq.read_table(path, columns=["instance_id", "trajectory", "exit_status"]).to_pylist()
        for sr, item in need.items():
            if sr.startswith(name[6:11] + ":"):
                row = tab[int(sr[6:])]
                assert row["instance_id"] == k1m[item]["instance_id"]
                traj[item] = row
    assert len(traj) == len(need)

    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    (HERE / "materials").mkdir(exist_ok=True)
    n_rows, n_default_cmd = 0, 0
    order = sorted(scored, key=lambda i: k1m[i]["rank"]) + smoke
    with open(out, "w") as fp, open(HERE / "materials" / "c1_manifest.jsonl", "w") as fm:
        for item in order:
            row = traj[item]
            loc = K1B.eligible(row)
            assert loc == k1m[item]["plant_msg_index"], item
            tr = row["trajectory"]
            split = "smoke" if item in smoke else ("main" if item in main_items else "guard_only")
            ai_texts = [tr[i]["text"] or "" for i, m in enumerate(tr) if m["role"] == "ai"]
            cmd = pick_cmd(ai_texts)
            cells = [("E", "control")]
            if split in ("main", "smoke"):
                assert K1C.heuristic_label(ai_texts) == "match"  # the claim is false by construction
                n_default_cmd += cmd == C.DEFAULT_CMD and split == "main"
                cells = [(a, c) for _, a, c, s in C.PLAN if s == "main"] + cells
            shas = {}
            for arm, cell in cells:
                if arm == "M":
                    base = render(tr, loc, cell, cmd, "stock")
                    assert len(base) == 1 and base[0]["role"] == "user"
                    msgs = [{"role": "user", "content": K2C.m_transform(base[0]["content"])}]
                else:
                    msgs = render(tr, loc, cell, cmd, "E" if arm == "E" else "stock")
                sha = C.sha256_text(C.dumps(msgs))
                if arm == "stock" and cell == "control":
                    assert sha == k1m[item]["prompt_sha256"]["control"] == k1p[(item, "control")], item
                if arm == "stock" and cell == "tag+claim":
                    assert sha == k1m[item]["prompt_sha256"]["late:no match"] == k1p[(item, "late:no match")], item
                if arm == "M" and cell == "control" and item in k2m:
                    assert sha == k2m[item]["prompt_sha256"]["M|control"], item
                shas[f"{arm}|{cell}"] = sha
                fp.write(C.dumps({"item_id": item, "arm": arm, "cell": cell, "messages": msgs,
                                  "prompt_sha256": sha}) + "\n")
                n_rows += 1
            fm.write(C.dumps({"item_id": item, "split": split, "rank": k1m[item]["rank"],
                              "heuristic_label": k1m[item]["heuristic_label"],
                              "reference": k2m[item]["reference"] if item in k2m else None,
                              "cmd": cmd, "prompt_sha256": shas}) + "\n")
    print(json.dumps({"main": len(main_items), "guard": len(scored), "smoke": smoke, "prompt_rows": n_rows,
                      "main_items_with_default_cmd": n_default_cmd}))


if __name__ == "__main__":
    main()
