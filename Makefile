# One-command reproduce. `make reproduce` needs Python 3.11 and numpy (pip install -r requirements.txt).
PY ?= python3

.PHONY: reproduce test rescore followup figures cases rows page

reproduce: test          ## run the tests, then recompute every number in the README's results table
	$(PY) scripts/reproduce.py

test:                    ## golden tests, standard library only
	$(PY) -W ignore::ResourceWarning -m unittest discover tests

rescore:                 ## re-score the bundled sample of saved judge outputs (standard library, no GPU, no network)
	$(PY) scripts/rescore_sample.py

followup:                ## recompute the follow-up table from data/followup_sessions.csv (standard library, no GPU, no network)
	$(PY) scripts/followup.py

rows:                    ## rewrite docs/rows.md (which raw rows produce which README number)
	$(PY) docs/make_rows.py

figures:                 ## redraw the three README figures from data/ (needs matplotlib)
	$(PY) figures/make_figures.py

cases:                   ## rewrite docs/cases.md from data/
	$(PY) docs/make_cases.py

page: cases              ## rewrite the static project page docs/index.html
	$(PY) docs/make_page.py
