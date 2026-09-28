# Redaction note

Internal file paths, host names and internal bookkeeping references were removed from the files below on 2026-10-06; test rules unchanged. No question, item set, cell, metric, threshold, decision rule, seed or prompt text was edited. The hash manifests (`*/KILL_TEST.sha256`) were recomputed for the edited files, so `tests/test_c1.py::test_freeze_hashes` checks the files as they are now. The original sha256 values are kept here so that anyone holding an original copy can confirm what it was.

The git history of this repository was rebuilt on the same date so that no earlier blob contains the removed text. Raw judge outputs (`data/`), the results (`C1/results/c1_results.json`), the item manifest and all analysis code are byte-identical to the originals; their hashes are pinned in `tests/test_c1.py`.

## Hash-locked files

| file | original sha256 | new sha256 | lines removed / added | what was removed |
|---|---|---|---|---|
| `C1/KILL_TEST.md` | `359264144a5c9ea6bd31826d3732683798558c022df8f3f5bdbd987eb3eb5f3a` | `427a0915dc1e66b8210a464415dc3de21c5b9233e7e590a973d0a652c685390a` | 5 / 4 | work-directory path; two references to an internal mirror folder; pointer to the design note |
| `C1/materials/EXTERNAL_SHA256.txt` | `5761412a21772fcbdcaa7553db28bc47e5acc1e318b329b28a5098e1fa0a852c` | `91976d86c82b91a131831befd907656476c9753e78588d005d96126f180de37d` | 4 / 4 | host name and work-directory path in front of four file names; the four hashes are unchanged |
| `K1/KILL_TEST.md` | `595929570f6cbaf5ebd5ff6e284be5ad1ca7369be04198824a11833998c49800` | `bf75913f920b27b07c7c546055067a7122d94948e0b58e7fdcde9b41b5ae46fd` | 9 / 8 | host name; work-directory paths; internal spend-log path; an internal config reference; one clause of internal status |
| `K1/run_judges.py` | `975aec16e90a652df4b4a923750ff162b8daa2eb91027b905a9e44ccefe20858` | `2658a9971f1a1cfe6c938811cb9703f82f7423dae75ee38be2e2059b875ba0d9` | 2 / 2 | the key and value of one spend-log field (now `"run": "docent-k1"`), used only by the optional API arm's spend cap |
| `K1/serve_vllm.sh` | `41b65a31810eca6f2ba1c50f0172b88e5038ae39f959233eb4e5cd1dfa3f008e` | `3303ea917bc541b0da037452d5cfb5c8aeedc7f1c4f78a8b28b93800c4f3b514` | 5 / 5 | host name in two comments; three host-specific paths, now read from the environment |
| `K2/KILL_TEST.md` | `d4964707212acdacae68c19b91a695167890ca13cb5562879b061d0623a3c2f2` | `95342fafffd74e72413eddb67d0f2d54856c311c121da96091555e12beb1ec3e` | 6 / 4 | host name; work-directory paths; an internal file path in the GO consequence; one clause of internal status |

Manifests, recomputed for the lines of the files above (lines for files not shipped here are untouched):

| manifest | original sha256 | new sha256 | lines changed |
|---|---|---|---|
| `C1/KILL_TEST.sha256` | `5f0d2176277ffc212bffaf3c887a122342ad29cd1c940c97f1b82414809be194` | `1e7dc09bd87060eccbf2202af1043c13598f6f5beb3826336ab05e5a4c66a234` | 2 |
| `K1/KILL_TEST.sha256` | `984b7670411a57bf952786c5f5af4ff3703fe7a3662dd16b7aa569cae3804d4b` | `91e97f0fa558d3dae9f1f70e2916d6abf93e82bd39825edf8ce12d6248dafaf3` | 3 |
| `K2/KILL_TEST.sha256` | `e80a8f893df3813c708a32c2db7744b2a7f7583e7a56233524ebd167764b192c` | `385d94a793d78ee9daf3b672d9f7d1c60c801ca48738d2b171b67719de7cd3b2` | 1 |

## Other edited files (not hash-locked)

| file | original sha256 | new sha256 | lines removed / added | what was removed |
|---|---|---|---|---|
| `C1/results/launch_c1_attempt1.log` | `6bedeb10a31b03a929c5e71b2f4f90a71d4b6a22235ee62bf3cd210b5ef1f152` | `8c3a446a72e0de4bff2e7452db8d22a540171ab824a079fc6d53385b2c26a98a` | 4 / 4 | work-directory path in four log lines |
| `C1/verify_c1_independent.py` | `9fcc0b104464ad648c569671f71a04330a0af76976804fb959129835627e7f43` | `e6bbc160d0ff87e2ed37175df56da0a024ab8c1579abbfebc15aeea0962b1626` | 3 / 3 | two hard-coded work-directory paths, now read from the environment |
| `docs/RESULT.md` | `f4487996599e2a6ac395bacab48578f3a7b3113e6c70a952402da1dceb0feb3f` | `de7e39766aa06f1610f61b7eef9a179a029bca64624b0be84c37139b56cd73fa` | 9 / 9 | host name; work-directory path; internal mirror folder; one phrase |
| `docs/VERIFY.md` | `1d848d1bb57b3c60342d9e8c5feaa03bf569b9c9c704e60986ec5ef048339949` | `9ee3b9ac37699d9d530ad45e808b1c4cfd157717c0a320c1505178610944f96c` | 6 / 6 | host name; work-directory path; internal mirror folder |

One file was left out of the public copy: `docs/CHOICE.md` (original sha256 `a90799e6d850794d4267bbec8c44ce5f844430c120d143f4c3cd01cba0edbe0e`), the note that chose between candidate experiments. Its design section is reproduced verbatim as section B of `C1/KILL_TEST.md`.

## The edited lines, as they read now

Line numbers refer to the current files. Each entry replaces the same number of original lines unless noted in the table above. `<workdir>` stands for the original work directory.

**`C1/KILL_TEST.md`**

```text
8: - **Hashes:** `KILL_TEST.sha256`, stored next to this file.
10: - **Design source:** the design note written before the freeze (`CHOICE.md`, not in this repository), §2, pasted verbatim in §B below.
21: | code | `<workdir>/core/code/C1/`, with `c1_common.py`, `build_c1.py`, `run_c1.py`, `analyze_c1.py`, `materials/c1_manifest.jsonl` |
24: (line removed)
146: ## B. Design (design note §2, verbatim)
```

**`C1/materials/EXTERNAL_SHA256.txt`**

```text
1: e4a78201c7fe6fc1b24e6ba56b26e23ff28925e0be4cfb71663f2b3a0e6b3811  <workdir>/core/items/c1_prompts.jsonl
2: 4724148be126b7a7977d9581b76dc1ffbcb97c8cd0a86ab3525e7dfc5f471f7f  <workdir>/k1/items/prompts.jsonl
3: 28cb536e0503044411133839328d57cc978ced7d0ae7e10e7b55821e9f33f340  <workdir>/k1/results/k1_rows.jsonl
4: 680037005f156fb3cd2987b2f486b64c1530c691852b93f9716a0bb6cb5b14d2  <workdir>/core/smoke/c1_smoke.jsonl
```

**`K1/KILL_TEST.md`**

```text
9: Agent-written (Claude Opus 5.5) on 2026-09-28, in a session Sami Hormi started. Nothing here had been published.
84:   - The prompts themselves (46 MB) are on the compute host at
85:     `<workdir>/k1/items/prompts.jsonl`. They are rebuilt deterministically by
112: - **Primary: two local open-weight judges.** Both are served by vLLM 0.19.0 on the compute host (A100 80 GB), with
131:     call is logged to `SPEND.jsonl`. The runner stops before any call whose
222: - The overall cap is $25.
226: - **Directories.** The work directory on the compute host is `<workdir>/k1`, and the code is
228: - **Temp files.** The compute host's root filesystem is full, so set `TMPDIR` under the work directory for every
```

**`K1/run_judges.py`**

```text
50:                 if r.get("run") == "docent-k1":
77:                         "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "run": "docent-k1", "judge": self.judge,
```

**`K1/serve_vllm.sh`**

```text
2: # Start one vLLM judge server. Usage: serve_vllm.sh <judge-name> <gpu> <port>
7: K1_WORKDIR=${K1_WORKDIR:?set K1_WORKDIR to a writable work directory}
8: HUB=${HF_HUB_CACHE:-$HOME/.cache/huggingface/hub}
20: # Keep every cache under the work directory.
24: HF_HUB_OFFLINE=1 CUDA_VISIBLE_DEVICES=$GPU nohup vllm serve "$SNAP" \
```

**`K2/KILL_TEST.md`**

```text
8: Agent-written (Claude Opus 5.5) on 2026-09-28, in a session Sami Hormi started. Nothing here had been published.
88: GO → the README gets M as a proposed patch with this result. STOP → M is recorded as not working; no variants of M are tried under this kill test.
100: ## 7. How to run (compute host, `<workdir>/k2`, code in `code/{K1,K2}`)
103: export TMPDIR=<workdir>/k2/cache/tmp
```
