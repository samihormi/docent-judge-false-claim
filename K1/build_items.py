"""Build the K1 judged items: 200 real SWE-agent trajectories x 7 variants, rendered with Docent's own
default judge prompt (Rubric.materialize_messages from docent-python==0.1.87).

Outputs
  <workdir>/items/prompts.jsonl        one row per (item, variant): the exact chat messages sent to a judge
  K1/materials/items_manifest.jsonl    one row per item: provenance, strata and per-variant prompt sha256

Usage: python build_items.py --datadir <dir with the 3 shards> --workdir /data/.../k1

Agent-written (Claude Opus 5.5), 2026-09-28.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import random

import pyarrow.parquet as pq
from docent.data_models.agent_run import AgentRun
from docent.data_models.chat import AssistantMessage, SystemMessage, UserMessage
from docent.data_models.transcript import Transcript
from docent.judges.types import Rubric

import k1_common as C

HERE = pathlib.Path(__file__).resolve().parent


def insert_before_last_fence(text: str, plant: str) -> str:
    spans = list(C.FENCE.finditer(text))
    if not spans:
        return text + plant
    i = spans[-1].start()
    return text[:i].rstrip("\n") + plant + text[i:]


def eligible(row) -> dict | None:
    if row["exit_status"] != "submitted":
        return None
    tr = row["trajectory"]
    if tr[0]["role"] != "system" or any(m["role"] not in ("system", "user", "ai") for m in tr):
        return None
    body = tr[1:]
    if sum(len(m["text"] or "") for m in body) > C.MAX_NONSYSTEM_CHARS:
        return None
    ai_idx = [i for i, m in enumerate(tr) if m["role"] == "ai"]
    if len(ai_idx) < 3:
        return None
    if C.last_command(tr[ai_idx[-1]]["text"]) != "submit":
        return None
    obs_idx = ai_idx[-1] - 1
    if obs_idx <= 1 or tr[obs_idx]["role"] != "user":
        return None
    hl = C.heuristic_label([tr[i]["text"] for i in ai_idx])
    if hl is None:
        return None
    return {"ai_first": ai_idx[0], "ai_last": ai_idx[-1], "obs_before_last": obs_idx, "heuristic_label": hl}


def variant_messages(tr, loc, variant: str):
    texts = [m["system_prompt"] if m["role"] == "system" else (m["text"] or "") for m in tr]
    if variant != "control":
        pos, label = variant.split(":")
        plant = C.plant_text(pos, label)
        if pos == "early":
            texts[loc["ai_first"]] = insert_before_last_fence(texts[loc["ai_first"]], plant)
        elif pos == "late":
            texts[loc["ai_last"]] = insert_before_last_fence(texts[loc["ai_last"]], plant)
        else:  # quoted: program output in the observation right before the final assistant turn
            # Placed before SWE-agent's trailing "(Open file: ...)" status lines when present.
            obs = texts[loc["obs_before_last"]]
            cut = obs.rfind("\n(Open file:")
            if cut < 0:
                texts[loc["obs_before_last"]] = obs.rstrip("\n") + "\n" + plant
            else:
                texts[loc["obs_before_last"]] = obs[:cut].rstrip("\n") + "\n" + plant + obs[cut + 1 :]
    msgs = []
    for m, t in zip(tr, texts):
        cls = {"system": SystemMessage, "user": UserMessage, "ai": AssistantMessage}[m["role"]]
        msgs.append(cls(content=t))
    run = AgentRun(transcripts=[Transcript(messages=msgs)], metadata={})
    judge_msgs = Rubric(rubric_text=C.RUBRIC_TEXT).materialize_messages(run)
    return [{"role": jm.role, "content": jm.content} for jm in judge_msgs]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--datadir", required=True)
    ap.add_argument("--workdir", required=True)
    args = ap.parse_args()

    rows = []
    for name, sha in sorted(C.SHARD_SHA256.items()):
        path = pathlib.Path(args.datadir) / name
        assert hashlib.sha256(path.read_bytes()).hexdigest() == sha, f"sha256 mismatch: {name}"
        cols = ["instance_id", "model_name", "target", "trajectory", "exit_status"]
        rows += [(f"{name[6:11]}:{i:05d}", r) for i, r in enumerate(pq.read_table(path, columns=cols).to_pylist())]

    seen, pool = set(), {"match": [], "no match": []}
    natural_tag_rows = 0
    for idx, row in rows:
        if any("<response>" in (m["text"] or "") + (m["system_prompt"] or "") for m in row["trajectory"]):
            natural_tag_rows += 1
            continue  # a natural <response> tag would confound the plant (none were seen in shard 0)
        loc = eligible(row)
        if loc is None or row["instance_id"] in seen:
            continue
        seen.add(row["instance_id"])
        pool[loc["heuristic_label"]].append((idx, row, loc))

    rng = random.Random(C.SEED)
    chosen, smoke = [], []
    for stratum in C.LABELS:
        picks = rng.sample(range(len(pool[stratum])), C.N_PER_STRATUM + C.N_SMOKE)
        chosen += [pool[stratum][i] for i in picks[: C.N_PER_STRATUM]]
        if stratum == "match":
            smoke += [pool[stratum][i] for i in picks[C.N_PER_STRATUM :]]
    chosen.sort(key=lambda t: t[0])
    order = list(range(len(chosen)))
    rng.shuffle(order)  # frozen item order; the API arm uses the first API_JUDGE["n_items"] of it

    wd = pathlib.Path(args.workdir)
    (wd / "items").mkdir(parents=True, exist_ok=True)
    (HERE / "materials").mkdir(exist_ok=True)
    with open(wd / "items" / "prompts.jsonl", "w") as fp, open(HERE / "materials" / "items_manifest.jsonl", "w") as fm:
        for split, rows in (("scored", [chosen[i] for i in order]), ("smoke", smoke)):
            for rank, (idx, row, loc) in enumerate(rows):
                item_id = f"{'i' if split == 'scored' else 'x'}{rank:03d}_{row['instance_id']}"
                shas = {}
                for v in C.VARIANTS:
                    msgs = variant_messages(row["trajectory"], loc, v)
                    shas[v] = C.sha256_text(C.dumps(msgs))
                    fp.write(C.dumps({"item_id": item_id, "variant": v, "messages": msgs, "prompt_sha256": shas[v]}) + "\n")
                fm.write(C.dumps({
                    "item_id": item_id, "split": split, "rank": rank, "shard_row": idx,
                    "instance_id": row["instance_id"], "model_name": row["model_name"],
                    "resolved": row["target"], "heuristic_label": loc["heuristic_label"],
                    "n_messages": len(row["trajectory"]), "plant_msg_index": loc,
                    "nonsystem_chars": sum(len(m["text"] or "") for m in row["trajectory"][1:]),
                    "prompt_sha256": shas,
                }) + "\n")
    print(json.dumps({
        "eligible_match": len(pool["match"]), "eligible_no_match": len(pool["no match"]),
        "rows_with_natural_response_tag": natural_tag_rows, "scored": len(chosen), "smoke": len(smoke),
    }))


if __name__ == "__main__":
    main()
