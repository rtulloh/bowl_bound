# Generated OOB evidence correction — DATA-039

Owner reported near-universal OOB stars on ordinary generated offensive cells.
Tracked in [DATA-039](issues/DATA/DATA-039.md), Milestone 34a. Investigation and
repair are isolated from the owner checkout, release worktrees and canonical
retained charts. Prior completed-game accounting audits do not establish that
source OOB distributions were correctly encoded.

## Cause and reviewed policy

The source adapter records an explicit narrative OOB mention as true; missing
mentions remain unknown. The old family estimator filtered unknown records out
of both numerator and denominator. One positive and 99 unknown observations
therefore requested 100% OOB, regardless of the observed incidence.

The reviewed correction models positive narrative incidence over the full matching
ordinary numeric support: true weight divided by all true/false/unknown weight.
The same synthetic sample requests 1%, with 99 unknown observations explicitly
reported. This is a lower-bound modeling assumption, not proof that those 99 plays
finished in bounds. Empty or wholly unknown evidence is visibly dormant or
unidentified. Source records, hashes and evidence classifications remain intact.

Support matches ordinary gain construction: known rush/completion yards with
primary fumbles excluded; existing B tail records and stable ties; QT sacks; QR
scrambles or documented rush proxy. The old shared team-wide supplemental OOB
proxy is removed. No gain, penalty, branch, color, recovery or RNG selection is
changed. Source-specific optional-boolean denominators must be reviewed separately.

The fumble estimator is not automatically the same defect: the adapter preserves
structured explicit false when present, and its denominator intentionally models
known fumble outcomes. Recovery outcomes require actual holder identities;
PAT/FG outcome samples retain explicit success/failure evidence. This inspection
found no second demonstrated positive-only denominator defect requiring a broader
repair. Missingness and source selection can still limit all of these estimates.

## Paydirt consultation

Before this repair, reviewed local `paydirt/chart_generator.py:533`,
`_mark_numeric_out_of_bounds`, and its numeric eligible-mass allocation. Adapt
conditioning on eligible numeric mass and physical dice probabilities. Do not copy
NFL source rates, face distributions, timing, play families or private charts.
Bowl Bound uses all 216 physical offensive combinations, not equal weights for
the thirty distinct totals.

## Test-first evidence and acceptance boundary

Three new synthetic integration controls failed on the unchanged generator:
sparse positive-only evidence with irrelevant incomplete-pass mentions; B/QT/proxy
support separation; and QR isolation from other rush outcomes. The first requested
incidence was quantized to the nearest attainable numeric mass, while the old
implementation marked the entire numeric support. The failure receipts remain
private. The corrected focused run passes eleven OOB-related tests, including
explicit false, wholly unknown/empty support, asymmetric weights and an
independent attainable-mass check. Independent review also identified an empty-QT
diagnostic path that borrowed a rush proxy before the existing generator correctly
rejected missing QT yardage. A fourth control failed first; the proxy fallback is
now explicitly QR-only, so empty QT evidence stays empty before that rejection.

Before modifying production code, retained original-generator synthetic semantic
baselines at seeds 7 and 19. Corrected charts and metadata compare equal after
removing only OOB flags and their literal provenance asterisks. Retained historical
inputs and catalogs are read-only; small-subset and full-cohort regeneration use
new ignored roots. Fresh generator version `college-chartgen-v5`, configuration,
input hashes, OOB diagnostics and exact semantic-difference receipts must accompany
the new candidate. Current-engine/coaching game acceptance belongs to the release
audit and must be renewed before publication. DATA-039 remains open until those
receipts are reviewed; this note does not declare release or M34a acceptance.

## Local verification receipts

Supported Python: `/Users/rtulloh/work/bowl_bound/.venv/bin/python` (3.12).

```sh
python -m pytest -q tests/chartgen/test_oob.py tests/chartgen/test_generation.py -k 'oob or bounds or missing_qt_support'
python -m pytest -q tests/chartgen/test_generation.py tests/chartgen/test_oob.py tests/chartgen/test_evidence.py tests/chartgen/test_empirical.py
python scripts/build_issue_index.py
python -m pytest -q tests/test_issue_tracker.py tests/test_priority_docs.py tests/test_release_player_docs.py
ruff check tools/chartgen/generate.py tests/chartgen/test_generation.py tests/chartgen/test_oob.py
ruff format --check tools/chartgen/generate.py tests/chartgen/test_generation.py tests/chartgen/test_oob.py
git diff --check
```

Results: final focused OOB controls **11 passed**; cumulative generator/evidence/
empirical checks **131 passed in 453.76s**; metadata/docs **22 passed**. No skips or
warnings. The cumulative process had loaded the implementation before the final
empty-QT guard clarification; the final focused run includes its separately
demonstrated red/green control. Lint, format and whitespace checks pass.

The three-team tiny candidate was independently reloaded with the current public
codec: non-OOB facts, colors, source-token bases, PAT, recovery and team metadata
match the retained charts. The final guard changes no tiny output bytes. All
source/config/output hashes, source counts and per-team diagnoses stay in ignored
private receipts; no historical chart values or source narratives are copied here.
