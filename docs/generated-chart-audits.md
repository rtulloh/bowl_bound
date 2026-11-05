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
  are recorded. A foreign imported engine or different candidate core is rejected.

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

The current schema deliberately supports only the reviewed model. A different
policy, source contract or cohort transformation requires an explicit versioned
audit change, synthetic failures first, independent review and renewed acceptance.
