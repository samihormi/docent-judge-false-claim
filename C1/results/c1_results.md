# C1 results

**Decision: GO**

| arm/cell | items run | ok % | P(no match) % [95% CI] | k/n | echo % |
|---|---|---|---|---|---|
| stock|control | 91/91 | 99.3 | 1.8 [0.4, 3.7] | 5/271 | - |
| stock|claim | 91/91 | 99.6 | 37.5 [29.3, 45.8] | 102/272 | 24.3 [17.9, 31.1] |
| stock|tag | 91/91 | 95.6 | 43.3 [35.5, 51.4] | 113/261 | 17.2 [12.3, 22.6] |
| stock|tag+claim | 91/91 | 97.1 | 62.3 [54.3, 70.0] | 165/265 | 17.7 [12.9, 22.8] |
| M|control | 91/91 | 100.0 | 5.9 [2.9, 9.2] | 16/273 | - |
| M|claim | 91/91 | 99.6 | 43.0 [34.6, 51.5] | 117/272 | 26.5 [20.2, 33.1] |
| E|control | 200/200 | 99.0 | 10.7 [5.5, 16.8] | 29/270 | - |
| stock|claim-vague | 91/91 | 99.6 | 1.1 [0.0, 2.6] | 3/272 | 2.9 [1.1, 5.1] |

Net adoption (stock, minus stock control), pp [95% CI]:

- A_claim: 35.7 [27.8, 43.9]
- A_tag: 41.5 [33.7, 49.3]
- A_tag+claim: 60.4 [52.3, 68.4]
- A_claim-vague: -0.7 [-2.9, 1.1]
- content_share: 0.59 [0.43, 0.79]
- A_claim_M: 37.2 [28.7, 46.0]
- delta_M: -1.5 [-8.3, 5.3]
- E_accuracy_vs_heuristic: E 90.4 [86.5, 94.0]; stock 85.1 [80.8, 89.1]; E-stock 5.3 [0.3, 10.4]
- E_accuracy_vs_reference: E 84.3 [79.4, 88.9]; stock 91.5 [88.7, 94.2]; E-stock -7.2 [-12.3, -2.2]

Secondary readings: {"content_carries_K1_effect": true, "format_carries_it": false, "M_reaches_prose": false, "M_does_not_reach_prose": false}
Not run: []
