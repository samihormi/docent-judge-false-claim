# K1 deviations log

Record every departure from `KILL_TEST.md` or from a hashed file after the freeze. Each entry gives:
- the date;
- what changed;
- why;
- whether any scored output had been seen at the time.

None as of the freeze.

## D1 (2026-09-28): crash fix in `analyze.py`, line 247

- **What changed.** `r[arm]["label"]` became `r[arm].get("label")` in the `flip_opposite_{arm}` metric
  (secondary metric 5). No other line changed. `analyze.py` sha256 goes from
  `7c719a4a…2f93` (frozen, in `KILL_TEST.sha256`) to
  `44aab8e35f43aca6a6fb5f732ff78b88ef948267bf4cbb8aa1757fc083fd75ed`. `KILL_TEST.sha256` is left as the
  freeze record, so `shasum -c` now reports `analyze.py: FAILED` by design; every other file still passes.
- **Why.** The first run of the frozen `analyze.py` on the complete outputs raised `KeyError: 'label'`
  there. When the `strict` comparator fails to validate a rollout, its result dict has `ok: False` and
  no `label` key. The stock and patched arms always have a label, because every `ok` rollout validated
  under both (asserted). With `.get`, a strict failure counts as "did not return the planted label".
  That is how `is_planted` already treats a failed parse for the hijack metrics. The fix changes no
  definition, threshold, item or output. It affects only `flip_opposite_strict`; the stock and patched
  values are the same expression as before.
- **Seen at the time?** No metric value had been computed, printed or read. The crash happened
  after the per-rollout parsing, before anything was written. The only thing seen was the traceback.
  The primary endpoint (H_stock) and the decision rule code are unchanged.
