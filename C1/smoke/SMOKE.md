# C1 smoke test (held-out item only; not a result)

- Item: K1's held-out smoke item `x000_app-sre__sretoolbox-53` (heuristic "match"; never in K1/K2/C1 scoring).
- Command: `run_c1.py --split smoke --base-url http://127.0.0.1:8111/v1 --group-concurrency 8`, 2026-09-28
  ~08:55 UTC (16:55 SGT). Sent to K2's stock vLLM server (same Qwen2.5-32B-FP8 snapshot and flags) while K2 ran;
  24 requests; no K2 process was touched.
- Output: `c1_smoke.jsonl` (sha256 in `../materials/EXTERNAL_SHA256.txt`). 8 groups x 3 rollouts, 24/24 `ok` on attempt 1;
  seed variant and rollout ids match `c1_common.seed_spec` for every group.

| arm/cell | labels (3 rollouts) |
|---|---|
| stock control (K1 seeds r3-5) | match, match, match |
| stock claim | match, match, match |
| stock tag | match, match, match |
| stock tag+claim (= K1 late:no match) | no match x3 |
| stock claim-vague | match x3 |
| M control / M claim | match x3 / match x3 |
| E control | match x3 |

One item says nothing about the rates. It only shows the pipeline runs end to end. The analysis code path
(`load_c1`, E comparator, all bootstrap stats) was also executed on these rows with the item temporarily
treated as "main", without error.

Dry run of `analyze_c1.py` on K1 rows: `dry_results.md` (reproduces 163/265 for tag+claim; the claim/tag rows
there are K1 early/quoted stand-ins, not C1 data).
