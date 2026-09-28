"""Collect C1 judge outputs. Resumable: finished (item, arm, cell) groups are skipped, groups with a
transport error are redone. Groups are launched in PLAN priority order (P0 first).

Each rollout is K1's run_judges.one_rollout, unchanged: Docent 0.1.87 retry_with_feedback (<= 3 attempts,
stock XML_KEY validator), temperature 1.0, max_tokens 8192, per-request seed from item|variant|rollout|attempt.
Seed variants and rollout ids come from c1_common.seed_spec.

  python run_c1.py --base-url http://127.0.0.1:8111/v1 --prompts <core>/items/c1_prompts.jsonl \
      --out <core>/outputs/c1.jsonl [--split scored|smoke] [--stop-at-utc 2026-09-28T10:50]

--stop-at-utc: no new group starts after this time; groups in flight finish. Unstarted groups are simply
absent from the output (reported as not run by analyze_c1.py).

Agent-written (Claude Opus 5.5), 2026-09-28.
"""
from __future__ import annotations

import argparse
import asyncio
import datetime as dt
import json
import pathlib
import sys
import time
from types import SimpleNamespace

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "K1"))

from openai import AsyncOpenAI  # noqa: E402

import k1_common as K1C  # noqa: E402
import run_judges as K1R  # noqa: E402

import c1_common as C  # noqa: E402


async def run_group(client, rargs, row, validate, sem, out_fp, lock, stop_at):
    async with sem:
        if stop_at and time.time() > stop_at:
            return "skipped"
        seedvar, rollout_ids = C.seed_spec(row["arm"], row["cell"])
        t0 = time.monotonic_ns()
        done_order: list[int] = []

        async def _one(r):
            res = await K1R.one_rollout(client, rargs, None, row["messages"],
                                        K1C.row_key(row["item_id"], seedvar, r), validate)
            res["rollout"] = r
            res["t_done_ms"] = (time.monotonic_ns() - t0) / 1e6
            done_order.append(r)
            return res

        results = await asyncio.gather(*[_one(r) for r in rollout_ids])
        rec = {"judge": C.JUDGE, "item_id": row["item_id"], "arm": row["arm"], "cell": row["cell"],
               "seed_variant": seedvar, "prompt_sha256": row["prompt_sha256"], "k": len(rollout_ids),
               "completion_order": done_order, "rollouts": sorted(results, key=lambda x: x["rollout"])}
        async with lock:
            out_fp.write(json.dumps(rec, ensure_ascii=False) + "\n")
            out_fp.flush()
        return "done"


async def main_async(args):
    manifest = {json.loads(l)["item_id"]: json.loads(l) for l in open(HERE / "materials" / "c1_manifest.jsonl")}
    splits = {"scored": ("main", "guard_only"), "smoke": ("smoke",)}[args.split]
    prio = {(a, c): k for k, (_, a, c, _) in enumerate(C.PLAN)}
    rows = []
    for r in map(json.loads, open(args.prompts)):
        m = manifest[r["item_id"]]
        if m["split"] not in splits:
            continue
        assert C.sha256_text(C.dumps(r["messages"])) == r["prompt_sha256"] == m["prompt_sha256"][f"{r['arm']}|{r['cell']}"]
        rows.append(r)
    if args.split == "scored":
        assert len(rows) == C.N_MAIN * (len(C.PLAN) - 1) + C.N_GUARD, len(rows)
    rows.sort(key=lambda r: (prio[(r["arm"], r["cell"])], manifest[r["item_id"]]["rank"]))

    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    done, kept = set(), []
    if out.exists():
        for line in out.read_text().splitlines():
            rec = json.loads(line)
            if all(x["status"] != "transport_error" for x in rec["rollouts"]):
                done.add((rec["item_id"], rec["arm"], rec["cell"]))
                kept.append(line)
        out.write_text("".join(l + "\n" for l in kept))
    todo = [r for r in rows if (r["item_id"], r["arm"], r["cell"]) not in done]
    stop_at = None
    if args.stop_at_utc:
        stop_at = dt.datetime.fromisoformat(args.stop_at_utc).replace(tzinfo=dt.timezone.utc).timestamp()
    print(json.dumps({"split": args.split, "groups_total": len(rows), "groups_done": len(done), "todo": len(todo),
                      "stop_at_utc": args.stop_at_utc}), flush=True)

    client = AsyncOpenAI(base_url=args.base_url, api_key="EMPTY", timeout=1800, max_retries=0)
    rargs = SimpleNamespace(backend="vllm", model=C.JUDGE, judge=C.JUDGE)
    validate = K1R.make_validator()
    sem, lock = asyncio.Semaphore(args.group_concurrency), asyncio.Lock()
    with open(out, "a") as fp:
        tasks = [asyncio.create_task(run_group(client, rargs, r, validate, sem, fp, lock, stop_at)) for r in todo]
        n = skipped = 0
        for fut in asyncio.as_completed(tasks):
            st = await fut
            if st == "skipped":
                skipped += 1
                continue
            n += 1
            if n % 25 == 0:
                print(json.dumps({"groups_written": n, "of": len(todo), "utc": time.strftime("%H:%M:%S", time.gmtime())}),
                      flush=True)
    print(json.dumps({"finished": True, "groups_written": n, "skipped_after_stop": skipped}), flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", required=True)
    ap.add_argument("--prompts", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--split", default="scored", choices=["scored", "smoke"])
    ap.add_argument("--group-concurrency", type=int, default=24)
    ap.add_argument("--stop-at-utc")
    asyncio.run(main_async(ap.parse_args()))


if __name__ == "__main__":
    main()
