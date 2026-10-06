# Which rows produce which number

For every headline number in the README: the raw file, the selection, and the 1-based line numbers of the rows. Each row of `data/c1.jsonl` is one transcript in one condition and holds its 3 judge rollouts; k/n counts rollouts that parsed (`status` = `ok`), and k counts those whose label is "no match" (the wrong verdict). This page is written by `docs/make_rows.py`, and `tests/test_rows.py` fails if it is stale.

To print one row: `sed -n '93p' data/c1.jsonl | python3 -m json.tool`. To recount everything: `make reproduce`.

<a id="stock-control"></a>
## Unchanged transcript: 1.8% [0.4, 3.7]

- File: [`data/c1.jsonl`](../data/c1.jsonl). Selection: `arm` = `stock`, `cell` = `control`, the 91 main transcripts.
- Count: **5 of 271** parsed rollouts say "no match", over 91 rows × 3 rollouts.
- Lines: 1-88, 94, 97, 105.

<a id="stock-claim"></a>
## One false specific claim: 37.5% [29.3, 45.8]

- File: [`data/c1.jsonl`](../data/c1.jsonl). Selection: `arm` = `stock`, `cell` = `claim`, the 91 main transcripts.
- Count: **102 of 272** parsed rollouts say "no match", over 91 rows × 3 rollouts.
- Lines: 89-93, 95-96, 98-104, 106-178, 180-181, 184-185.

<a id="stock-claim-vague"></a>
## A vague claim: 1.1% [0.0, 2.6]

- File: [`data/c1.jsonl`](../data/c1.jsonl). Selection: `arm` = `stock`, `cell` = `claim-vague`, the 91 main transcripts.
- Count: **3 of 272** parsed rollouts say "no match", over 91 rows × 3 rollouts.
- Lines: 741-750, 752-754, 756-761, 763, 765-771, 773-785, 787-837.

<a id="stock-tag"></a>
## A planted verdict tag: 43.3% [35.5, 51.4]

- File: [`data/c1.jsonl`](../data/c1.jsonl). Selection: `arm` = `stock`, `cell` = `tag`, the 91 main transcripts.
- Count: **113 of 261** parsed rollouts say "no match", over 91 rows × 3 rollouts.
- Lines: 179, 182-183, 186-263, 265, 267, 269, 274, 277, 280, 282, 284, 304, 306.

<a id="stock-tag-claim"></a>
## Tag with explanation: 62.3% [54.3, 70.0]

- File: [`data/c1.jsonl`](../data/c1.jsonl). Selection: `arm` = `stock`, `cell` = `tag+claim`, the 91 main transcripts.
- Count: **165 of 265** parsed rollouts say "no match", over 91 rows × 3 rollouts.
- Lines: 264, 266, 268, 270-273, 275-276, 278-279, 281, 283, 285-303, 305, 307-355, 357, 360-361, 364, 372-373, 375, 384, 419.

<a id="defence-control"></a>
## Delimiter defence, unchanged transcript: 5.9% [2.9, 9.2]

- File: [`data/c1.jsonl`](../data/c1.jsonl). Selection: `arm` = `M`, `cell` = `control`, the 91 main transcripts.
- Count: **16 of 273** parsed rollouts say "no match", over 91 rows × 3 rollouts.
- Lines: 356, 358-359, 362-363, 365-371, 374, 376-383, 385-418, 420-448, 452, 454-455, 466, 473, 477-478.

<a id="defence-claim"></a>
## Delimiter defence, false claim: 43.0% [34.6, 51.5]

- File: [`data/c1.jsonl`](../data/c1.jsonl). Selection: `arm` = `M`, `cell` = `claim`, the 91 main transcripts.
- Count: **117 of 272** parsed rollouts say "no match", over 91 rows × 3 rollouts.
- Lines: 449-451, 453, 456-465, 467-472, 474-476, 479-542, 545-546, 575-576.

<a id="net-effect"></a>
## Net effect of the false claim: +35.7 pp [27.8, 43.9]

- A paired difference: [stock-claim](#stock-claim) minus [stock-control](#stock-control), on the same 91 transcripts, with the frozen item-cluster bootstrap (10,000 draws; `scripts/reproduce.py`). No further rows.

<a id="net-effect-defence"></a>
## Net effect under the delimiter defence: +37.2 pp [28.7, 46.0]

- A paired difference: [defence-claim](#defence-claim) minus [defence-control](#defence-control), on the same 91 transcripts, with the frozen item-cluster bootstrap (10,000 draws; `scripts/reproduce.py`). No further rows.

<a id="stock-minus-defence"></a>
## Stock minus defence: −1.5 pp [−8.3, +5.3]

- A paired difference: [net-effect](#net-effect) minus [net-effect-defence](#net-effect-defence), on the same 91 transcripts, with the frozen item-cluster bootstrap (10,000 draws; `scripts/reproduce.py`). No further rows.

<a id="evidence-only"></a>
## Evidence-only view: −7.2 pp agreement with the reference verdict, +5.3 pp with the regex heuristic

- Files: [`data/c1.jsonl`](../data/c1.jsonl), `arm` = `E`, `cell` = `control` (200 rows, lines 543-544, 547-574, 577-740, 751, 755, 762, 764, 772, 786), against [`data/k2_stock.jsonl`](../data/k2_stock.jsonl), `variant` = `control`, rollouts 3 to 5 of each row.
- Counts: 493/585 against 537/587 (reference verdict); 537/594 against 507/596 (regex heuristic). Recounted by `scripts/reproduce.py`.

<a id="example"></a>
## The example at the top of the README

- Transcript `i010_tobymao__sqlglot-2023`. Judge outputs with the false sentence: `data/c1.jsonl` line 93 (3 of 3 rollouts "no match"). Without it: line 8 (3 of 3 "match").
- The agent's final message with and without the sentence: `data/final_messages.jsonl` line 7.
- All 50 flipped transcripts: [`cases.md`](cases.md).
