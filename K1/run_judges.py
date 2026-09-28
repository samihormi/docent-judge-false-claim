"""Collect raw judge outputs for K1. Resumable: a (item, variant) group already written is skipped.

Each (item, variant) group launches its k rollouts concurrently, as Docent's MajorityVotingJudge does,
and records the order in which they completed. Each rollout reproduces Docent 0.1.87's
retry_with_feedback loop (up to 3 attempts, validated with the stock XML_KEY parser). Stock and
patched parsers accept exactly the same outputs (both return a value iff at least one block
validates), so one set of generations serves both parser arms; analyze.py asserts this.

  vLLM (local judge):  python run_judges.py --judge qwen2.5-32b --backend vllm --base-url http://127.0.0.1:8101/v1 \
                         --model qwen2.5-32b --prompts <workdir>/items/prompts.jsonl --out <workdir>/outputs/qwen2.5-32b.jsonl
  OpenAI (API arm):    python run_judges.py --judge gpt-5.6-luna --backend openai --prompts ... --out ... \
                         --spend-log .../SPEND.jsonl      (reads OPENAI_API_KEY from the environment; never printed)

Agent-written (Claude Opus 5.5), 2026-09-28.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import pathlib
import time
from types import SimpleNamespace

from docent.judges.impl import BaseJudge
from docent.judges.types import Rubric
from docent.judges.util.parse_output import ValidationFailedException
from docent.judges.util.validation_logging import validation_repair_user_message
from openai import AsyncOpenAI

import k1_common as C

HERE = pathlib.Path(__file__).resolve().parent


class SpendCapReached(Exception):
    pass


class Spend:
    def __init__(self, log_path: str | None, judge: str):
        self.path = pathlib.Path(log_path) if log_path else None
        self.judge = judge
        self.total = 0.0
        self.pending = 0.0  # worst-case reservations of in-flight calls
        self.lock = asyncio.Lock()
        if self.path and self.path.exists():
            for line in self.path.read_text().splitlines():
                r = json.loads(line)
                if r.get("stream") == "transluce-k1":
                    self.total += r["est_usd"]

    def worst_case(self, prompt_chars: int) -> float:
        return (prompt_chars / 3.0) * C.API_PRICE_IN / 1e6 + C.MAX_TOKENS * C.API_PRICE_OUT / 1e6

    async def reserve(self, prompt_chars: int) -> float:
        wc = self.worst_case(prompt_chars)
        async with self.lock:
            if self.total + self.pending + wc > C.API_CAP_USD:
                raise SpendCapReached(f"estimated spend {self.total:.3f} + in-flight + next call would exceed ${C.API_CAP_USD}")
            self.pending += wc
        return wc

    async def release(self, wc: float):
        async with self.lock:
            self.pending -= wc

    async def record(self, key: str, usage):
        pin = getattr(usage, "prompt_tokens", 0) or 0
        pout = getattr(usage, "completion_tokens", 0) or 0
        est = pin * C.API_PRICE_IN / 1e6 + pout * C.API_PRICE_OUT / 1e6
        async with self.lock:
            self.total += est
            if self.path:
                with open(self.path, "a") as f:
                    f.write(json.dumps({
                        "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "stream": "transluce-k1", "judge": self.judge,
                        "key": key, "prompt_tokens": pin, "completion_tokens": pout, "est_usd": round(est, 6),
                        "cum_est_usd": round(self.total, 6),
                        "price_assumption_per_mtok": [C.API_PRICE_IN, C.API_PRICE_OUT],
                    }) + "\n")


def make_validator():
    j = SimpleNamespace(cfg=Rubric(rubric_text=C.RUBRIC_TEXT))
    return lambda text: BaseJudge._parse_xml_key_output(j, text, None)


async def one_rollout(client, args, spend, messages, key, validate):
    """Docent 0.1.87 retry_with_feedback: validation failures are fed back, up to 3 attempts."""
    attempts, failures = [], []
    for attempt in range(C.MAX_VALIDATION_ATTEMPTS):
        cur = list(messages)
        for failed_output, err in failures:
            cur += [{"role": "assistant", "content": failed_output},
                    {"role": "user", "content": validation_repair_user_message(err)}]
        kw = dict(model=args.model, messages=cur)
        if args.backend == "openai":
            kw.update(max_completion_tokens=C.MAX_TOKENS, reasoning_effort=C.API_JUDGE["reasoning_effort"])
        else:
            kw.update(temperature=C.TEMPERATURE, max_tokens=C.MAX_TOKENS,
                      seed=int(C.sha256_text(f"{key}|{attempt}")[:8], 16))
        resp, last_exc = None, None
        for net_try in range(4):
            try:
                if args.backend == "openai":
                    wc = await spend.reserve(sum(len(m["content"]) for m in cur))
                    try:
                        resp = await client.chat.completions.create(**kw)
                    finally:
                        await spend.release(wc)
                    await spend.record(f"{key}|a{attempt}", resp.usage)
                else:
                    resp = await client.chat.completions.create(**kw)
                break
            except SpendCapReached:
                raise
            except Exception as e:  # transport / server error: back off and retry
                last_exc = e
                await asyncio.sleep(2 ** net_try)
        if resp is None:
            return {"status": "transport_error", "error": repr(last_exc)[:500], "attempts": attempts}
        text = resp.choices[0].message.content or ""
        attempts.append({"text": text, "finish_reason": resp.choices[0].finish_reason,
                         "completion_tokens": getattr(resp.usage, "completion_tokens", None),
                         "prompt_tokens": getattr(resp.usage, "prompt_tokens", None)})
        try:
            validate(text)
            return {"status": "ok", "final_text": text, "n_attempts": attempt + 1, "attempts": attempts}
        except ValidationFailedException as e:
            failures.append((e.failed_output or text, str(e)))
    return {"status": "validation_exhausted", "final_text": None, "n_attempts": C.MAX_VALIDATION_ATTEMPTS,
            "attempts": attempts}


async def run_group(client, args, spend, row, k, validate, sem, out_fp, lock):
    async with sem:
        t0 = time.monotonic_ns()
        done_order: list[int] = []

        async def _one(r):
            res = await one_rollout(client, args, spend, row["messages"],
                                    C.row_key(row["item_id"], row["variant"], r), validate)
            res["rollout"] = r
            res["t_done_ms"] = (time.monotonic_ns() - t0) / 1e6
            done_order.append(r)
            return res

        results = await asyncio.gather(*[_one(r) for r in range(k)])
        rec = {"judge": args.judge, "item_id": row["item_id"], "variant": row["variant"],
               "prompt_sha256": row["prompt_sha256"], "k": k, "completion_order": done_order,
               "rollouts": sorted(results, key=lambda x: x["rollout"])}
        async with lock:
            out_fp.write(json.dumps(rec, ensure_ascii=False) + "\n")
            out_fp.flush()


async def main_async(args):
    manifest = {json.loads(l)["item_id"]: json.loads(l) for l in open(HERE / "materials" / "items_manifest.jsonl")}
    keep = {i for i, m in manifest.items() if m["split"] == args.split}
    if args.backend == "openai" and args.split == "scored":
        keep = {i for i in keep if manifest[i]["rank"] < C.API_JUDGE["n_items"]}
    rows = [r for r in map(json.loads, open(args.prompts)) if r["item_id"] in keep]
    for r in rows:
        assert C.sha256_text(C.dumps(r["messages"])) == r["prompt_sha256"] == manifest[r["item_id"]]["prompt_sha256"][r["variant"]]
    rows.sort(key=lambda r: (manifest[r["item_id"]]["rank"], C.VARIANTS.index(r["variant"])))

    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    done = set()
    if out.exists():
        kept = []
        for line in out.read_text().splitlines():
            rec = json.loads(line)
            if all(x["status"] != "transport_error" for x in rec["rollouts"]):
                done.add((rec["item_id"], rec["variant"]))
                kept.append(line)
        out.write_text("".join(l + "\n" for l in kept))  # drop groups with transport errors; they are redone
    todo = [r for r in rows if (r["item_id"], r["variant"]) not in done]
    print(json.dumps({"judge": args.judge, "groups_total": len(rows), "groups_done": len(done), "todo": len(todo)}), flush=True)

    if args.backend == "openai":
        client = AsyncOpenAI(timeout=600, max_retries=0)
    else:
        client = AsyncOpenAI(base_url=args.base_url, api_key="EMPTY", timeout=1800, max_retries=0)
    spend = Spend(args.spend_log, args.judge)
    validate = make_validator()
    sem, lock = asyncio.Semaphore(args.group_concurrency), asyncio.Lock()
    with open(out, "a") as fp:
        tasks = [asyncio.create_task(run_group(client, args, spend, r, C.ROLLOUTS[r["variant"]] if args.backend == "vllm" else 1,
                           validate, sem, fp, lock)) for r in todo]
        n = 0
        for fut in asyncio.as_completed(tasks):
            try:
                await fut
            except SpendCapReached as e:
                print(json.dumps({"stopped": "spend_cap", "detail": str(e)}), flush=True)
                for t in tasks:
                    t.cancel()
                await asyncio.gather(*tasks, return_exceptions=True)
                break
            n += 1
            if n % 25 == 0:
                print(json.dumps({"judge": args.judge, "groups_written": n, "of": len(todo)}), flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--judge", required=True)
    ap.add_argument("--backend", choices=["vllm", "openai"], required=True)
    ap.add_argument("--base-url")
    ap.add_argument("--model", required=True)
    ap.add_argument("--prompts", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--split", default="scored", choices=["scored", "smoke"])
    ap.add_argument("--group-concurrency", type=int, default=24)
    ap.add_argument("--spend-log")
    args = ap.parse_args()
    if args.backend == "openai":
        assert args.spend_log, "--spend-log is required for the API arm"
        assert args.model == C.API_JUDGE["name"]
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
