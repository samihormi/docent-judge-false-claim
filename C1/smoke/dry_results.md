# C1 DRY RUN on K1 rows (claim = K1 early:no match, tag = K1 quoted:no match; NOT C1 results)

**Decision: INCONCLUSIVE**

| arm/cell | items run | ok % | P(no match) % [95% CI] | k/n | echo % |
|---|---|---|---|---|---|
| stock|control | 91/91 | 99.3 | 1.5 [0.4, 3.0] | 4/271 | - |
| stock|claim | 91/91 | 98.5 | 7.4 [3.0, 12.6] | 20/269 | 0.0 [0.0, 0.0] |
| stock|tag | 91/91 | 94.9 | 63.7 [54.8, 72.6] | 165/259 | 0.0 [0.0, 0.0] |
| stock|tag+claim | 91/91 | 97.1 | 61.5 [53.4, 69.5] | 163/265 | 19.6 [14.7, 24.9] |

Net adoption (stock, minus stock control), pp [95% CI]:

- A_claim: 6.0 [1.5, 11.4]
- A_tag: 62.2 [53.2, 70.9]
- A_tag+claim: 60.0 [52.0, 68.0]
- content_share: 0.10 [0.02, 0.19]

Secondary readings: {"format_carries_it": true}
Not run: ['M|control', 'M|claim', 'E|control', 'stock|claim-vague']
