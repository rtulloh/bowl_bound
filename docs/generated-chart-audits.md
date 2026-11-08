# Generated-chart release audits

Generated charts must pass a fresh audit before a native build. The reusable CI
test workflow also requires this check, and native build jobs depend on that
workflow succeeding. A saved successful JSON report is evidence, not an input
that can bypass recomputation.

```sh
python -m scripts.audit_generated_charts --report private-data/release-audit/charts.json
```

The audit reads the exact generated-file pins in `release/manifest.json`, loads
every selected team through the strict chart/provenance codec, and requires
`release/generated-chart-audit.json`. The latter is a reviewed development input;
it is excluded from runtime bundles. Missing, stale, incomplete or unsupported
inputs fail with a nonzero exit status. Rejections retain a machine-readable
report when `--report` is supplied.

## What the automated gate proves

- Exact defensive probability mass comes from all 36 physical red/green pairs,
  not equally weighted displayed rows. Different-looking rows can have the same
  distribution: row 1 has mass 12/36, as do rows 2 and 5 together.
- The selected original `authored-bb-yardage-v1` model has the reviewed policy
  hash. The audit recomputes that hash from its complete coefficient table.
  It is an experimental gameplay model, separate from observed team strength.
- Subtracting those declared numeric adjustments reconstructs the accepted
  baseline's complete normalized defensive facts. Blank versus explicit numeric
  zero, numeric priority, sign/color, nonnumeric responses and OOB facts are
  preserved. Nonnumeric response changes cannot hide behind plausible means.
- Offense, supplemental, special-teams, PAT, recovery and team metadata retain
  their accepted baseline file hashes. Existing corrected OOB facts remain pinned.
- The actual priority resolver gives the declared directional benefits and costs
  for ordinary gain controls 4, 10 and 18. Every formation pair needs counterplay
  across offensive calls. The A anchor may retain equal pass columns; universal
  cell or column uniqueness is not required.
- Every distinct frozen offensive cell retains its exact primary result-class,
  operation, pending and OOB distribution against each formation. Pending B/QR/QT,
  Option, penalties and recoveries remain explicit primary categories; the audit
  does not treat them as completed zero-yard plays. Directional scores are numeric
  primary contribution, **not** full expected yardage or turnover utility.
- Candidate, expectation, policy, auditor and actually imported engine identities
  are recorded. The engine identity covers the exact approved runtime module
  inventory, so source and native stages identify the same core while development
  audit tools remain unpackaged. Every loaded project module must originate from
  the auditor's source tree; candidate runtime selection and all core bytes must
  match. A foreign imported engine or different candidate core is rejected.

Native builders repeat the audit against their staged bytes before frontend build
and freezing. Each native inventory embeds the compact audit identity and full
report digest. Audit expectations and detailed reports are not packaged, and the
release asset count does not expand to include private evidence.

## Source qualification stays separate

Public CI does not possess private raw PBP. It cannot independently establish
historical truth, reconstruct missing formations or validate an OOB denominator
from a hash alone. Every report explicitly states `source_truth_revalidated: false`.
The source/OOB evidence review must happen locally against frozen source inputs,
including the DATA-039 positive/unknown-support accounting. Its independently
reviewed report hashes bind the public expectation file to the exact candidate and
baseline. They do not replace those private checks or establish historical accuracy.

Before publication, independently review full current-engine games, AI-selected
formation/call mixtures, per-team source-fit effects, coaching/fallbacks, timing,
scoring, statistics, structured traces and strict save/replay. Renew those reviews
when relevant source/model/engine inputs change. An equal-formation average or a
completed season alone is insufficient. Protected-cell, Option and supplemental
full-resolution synthetic regressions remain required alongside this primary gate.

After qualification, export compact baseline expectations from the already accepted
public baseline and the new candidate:

```sh
python -m scripts.audit_generated_charts \
  --root /absolute/path/to/candidate \
  --baseline-root /absolute/path/to/accepted-baseline \
  --qualification /absolute/path/to/private-data/qualification-summary.json
```

The qualification input contains `model_identity` with `origin`, `sha256`,
`authored_experimental`, `tool_version`, and conditioned `source_sha256`, plus
`normalized_source_sha256`, `source_review_sha256` and `oob_review_sha256`. The
builder validates both pinned catalogs and equal team inventories, derives the
candidate/baseline hashes and baseline semantic expectations, and writes the
audit-only file. It does not issue a successful audit or qualify source truth.
Run the audit command afterward against the actual candidate. Keep detailed
source reports in ignored storage; publish only approved aggregate provenance.

The legacy schema deliberately supports only its reviewed numeric model. A different
policy, source contract or cohort transformation requires an explicit versioned
audit change, synthetic failures first, independent review and renewed acceptance.


## Budget-aware experimental schema 2

Schema 2 admits the exact reviewed `authored-bb-budget-aware-v1` model and
`bb-chartgen-budget-alpha-v1` producer identity. Schema 1 retains its original
coefficient, response-coordinate and primary-class checks; selecting schema 2 is
not a way to relabel a stale schema-1 candidate. Both versions require the exact
candidate catalog, baseline expectation, source-review and actual runtime pins.
The accepted frozen-input correction is also applied: parse detached allowlisted
bytes and reject original input changes before returning a green result.

The new model intentionally redistributes ordinary/INC/INT/QT pass facts. Its
paired baseline expectations preserve exact run/Option semantics, fixed pass
whole cells, original normal/non-OOB call INC/INT/QT totals, formation INT totals
and the explicit A INT/QT anchors. Fixed variable family mass counts in those
budgets. Numeric support must remain. The audit independently checks signed
non-reversal relative to the revised A, preserved run counterplay and every
actual offensive cell's exact 216-by-36 primary denominator. Pending outcomes
remain distinct categories. It records stripes diagnostically without imposing
a universal appearance threshold or requiring unique rows/columns.

Role reports distinguish dormant, limited and exactly requested attainment. They
retain absolute residuals, including overshoot; equality does not establish a
strict benefit. The gate does not rerun the production optimizer or establish
mutable numeric/depth fit. Independent local candidate review binds the actual
objects to the reviewed joint family/partition/numeric-mean/edit objective,
conditional source-CDF/balance stages and residuals. Real-engine terminal/game
checks remain separate. `optimizer_optimality_revalidated` is false and
`source_fit` is `UNVERIFIED`.

Generated evidence may be truthfully rebased to one virtual logical source per
team. The ordinary installed loader must preserve all semantic coordinates, PAT,
recovery and gameplay metadata; source IDs, provenance and YAML bytes may change.
Schema 2 therefore checks nondefensive gameplay semantically rather than requiring
old YAML/provenance bytes. All five exported team/provenance files remain pinned.
No private preview decoder, detailed multi-source ancestry, private reference
chart or generator dependency is required by the runtime/public gate.

The owner permits a transparent experimental update of the existing 2007 cohort.
Exact historical formations/results, optional B placement and disclosed source
micro-reconciliation remain follow-ups, not automatic alpha rejection. This does
not waive actual identity/denominator, probability, legal codec, engine state,
privacy/packaging or build failures, and it does not claim historical accuracy.
The release owner runs the established full gate and approves publication.

## Conditional-depth schema 3

Schema 3 composes the accepted budget-aware checks with
`authored-bb-call-depth-v1`. Passing INT catch depths may change; every slot's
kind, priority and flags, event budgets and all nondepth football facts remain
protected. Reports explicitly identify preservation except for passing INT
depths rather than claiming those whole cells are unchanged.

The gate independently enumerates the finite conditional allocation for all
28 offensive/defensive passing columns per team. It requires declared support,
weights and canonical ordering, rejects missing/unknown policies and retains
zero-budget columns. Generated provenance and metadata are refreshed and pinned
to the actual ordinary files. Native staging repeats this same schema-three
audit before freezing.

Qualifying designed-call/catch-depth observations are absent in this cohort,
so these conditional shapes are authored assumptions. Neither a passing
schema-three report nor successful game/replay checks establish historical
conditional fit or complete causal/clock coverage.
