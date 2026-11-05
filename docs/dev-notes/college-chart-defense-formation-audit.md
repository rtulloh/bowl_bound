# Generated defensive formation audit — DATA-040

Status: reproduced; correction policy remains unapproved. This pass audits the
existing neutral generator, not a replacement tactical model. No charts were
generated or changed, and no engine/viewer behavior or immutable release tag was
changed. [DATA-040](issues/DATA/DATA-040.md) targets the in-progress M34a generation
workstream. Earlier complete-game acceptance does not validate tactical contrast.

## Finding

Every generated team's ordinary A–F formations have the same defensive outcome
probability distribution for each of the nine offensive plays. The four pass
columns also have the same distribution within every formation. Defensive
strength varies between teams; the gap is formation and within-family strategy.

The complete 116-team, 2007 OOB-corrected candidate was loaded through the strict
runtime CSV codec. Equality includes normalized kind, yards/location, variables,
priority, OOB, penalty, classified color and measured RGB. Source coordinates and
the formation address are excluded because they do not determine the result.
The chart catalog SHA-256 is
`e0fddc5f0e888e5339a924a908a813766c729b195b8c6cf72e2e89cda0f88939`.
Generator implementation: `388546e36d1c9ec2d0486d391cbbbca41fe06923`;
audit checkout: `b232fd9e6e21bfc7de1def28d56be90750e75613` (documentation checkpoint).
Detailed team-level results, hashes and the read-only audit script remain ignored
under `private-data/data040-defense-audit/`.

Defensive totals 1–5 have physical weights **12, 11, 9, 3, 1** out of 36, from all
six red faces crossed with all six green faces. These are not five equally likely
rows. For each play there are 116 × 15 = 1,740 formation pairs.

| Play | Teams with all six row vectors identical | Teams with all six weighted distributions identical | Equal row-vector formation pairs / 1,740 |
| --- | ---: | ---: | ---: |
| 1 | 96 | 116 | 1,580 |
| 2 | 96 | 116 | 1,616 |
| 3 | 96 | 116 | 1,560 |
| 4 | 100 | 116 | 1,648 |
| 5 | 96 | 116 | 1,548 |
| 6 | 103 | 116 | 1,614 |
| 7 | 109 | 116 | 1,687 |
| 8 | 103 | 116 | 1,626 |
| 9 | 103 | 116 | 1,632 |

All 1,740 formation pairs per play match in weighted distribution. Across 696
team/formation combinations, all four pass columns are distribution-identical;
627 are also row-identical. All five run columns are distribution-identical in
all 696 combinations, and row-identical in 584. For 103 of 116 teams, all 24 pass
columns match row for row. The other 13 differ only in equal-probability placement.
There are 91 distinct complete pass-defense profiles across teams and 115 distinct
full-defense row profiles. Thus this is not one chart copied to every team.

Root's independent raw-CSV enumeration agrees with these strict-codec results.
This is a distribution claim, not a claim that every fixed seed gives an identical
game: moving cells between rows can change a particular seeded outcome while
preserving its probability.

## Cause and source limits

`tools/chartgen/tactics.py:66–71` creates 54 neutral formation/play entries with all
seven deltas zero. `generate_team` defaults to that profile and rejects
`origin: reference-derived`. All 116 retained generation manifests declare neutral
tactics, the same tactical-profile hash
`5bd014298f0454b9f8891899c0f99c19d26a2b2f975062103cdd7f31a19824d3`,
and unidentifiable formation-specific historical distributions.

In `tools/chartgen/generate.py:1080–1223`, regularized team/opponent run or completion
yardage effects and completion/INT/sack effects are shared across formations.
The four pass plays use the same team effects and response pools. A formation
changes a tactical lookup, whose deltas are zero, and deterministic placement
seeds. Those seeds can produce alternative row placements; they do not supply a
football tradeoff. Inspection of all retained diagnostics found no formation
contrast in requested yardage effects and no pass-play contrast in those effects.

The normalized PBP schema records partial called/resolved-family evidence but no
observed A–F defensive formation. Generic outcomes and pooled families do not
identify Screen/Sprint Out/Boot-leg/Drop Back independently. The retained local
source-contract review and generator reference-comparison guidance explicitly
separate inferred neutral effects from source observations. Those working
documents are outside this public release subset. Averages and team
strength cannot recover unidentified tactical interactions. This audit exposes a
playability gap in the neutral baseline; it does not establish empirical values
for a replacement model.

## Engine effects

Ordinary `resolve_play` selects the requested formation's normalized chart cell,
then `resolve_cells` applies the priority table. There is no hidden A–F bonus,
blitz multiplier or prevent-defense adjustment. Equal semantic distributions
therefore provide equal ordinary response probabilities against the same offense.

Razzle-Dazzle also uses the chosen formation's chart cell. Ordinary Option SOP/BLP
rerolls nullify the original defense. QB Sneak uses the offense's Play 1 box color
with blank defense; Hail Mary uses blank defense. Separate Advanced II
RUN/PASS/NICKEL/wildcard calls have engine-owned effects, but they are distinct
from A–F and are disabled for the generated-catalog play profile. Those paths do
not supply missing A–F tactical structure.

This is a generator modeling finding. Changing the viewer would hide it; changing
the engine would apply a second rules layer to chart semantics and needs separate
rules authority.

## Paydirt consultation and correction choices

Consulted local Paydirt before this audit phase:

- `paydirt/chart_generator.py:951–1060`, especially `_generate_defense`, starts
  from a tactical template, then separately adds team efficiency and disruption.
- `docs/dev-notes/statistical-chart-generator.md:124–135` explicitly calls that
  structure modeled rather than an observed formation reconstruction;
  `371–375` distinguishes uniqueness from accuracy.
- `tests/test_chart_generator.py:278–318` uses synthetic team-strength controls,
  but does not establish all directional formation tradeoffs.
- Last Paydirt generator-file commit reviewed: `86b70c323a88b1ca91a07942538899b36bce249c`.

Adapt the separation of tactical structure from team strength, explicit model
labels and synthetic controls. Do not reuse its template values, NFL play-number
semantics, historical private charts or runtime code dependency. Original template
provenance also requires review before any reuse. Bowl Bound's current prohibition
on fitting reference-derived formation coefficients remains in force.

Two defensible model paths require explicit authority before implementation:

1. Approve an original Bowl Bound structural policy with declared tradeoffs across
   formations and offensive families. Label it an authored modeling prior, separate
   from measured team strength and observed outcomes. Centering can preserve the
   declared formation mixture, but must not be advertised as empirical calibration.
   No particular coefficients are proposed by this read-only audit.
2. Acquire qualified source observations identifying the relevant formations and
   designed offensive calls. Audit coverage, classification and provenance before
   fitting interactions. Ordinary PBP plus formation names cannot supply them.

Keeping the neutral cohort is also an explicit experimental-product choice, with
the tactical limitation stated plainly; it does not resolve this issue. Whether
to release that product is an owner decision, not an inferred approval here.

For any approved correction, write synthetic failures first for intended
directional gains and costs, formation/play contrasts after exact physical-dice
encoding, priority/color interactions, team-strength independence and declared
mixture centering. Evaluate all 216 × 36 primary dice combinations against varied
synthetic offenses, plus supplemental/Option branches and multiple seeds. A token
uniqueness test can pass with the same probability distribution and is inadequate.
Renew source-fit/holdout, per-team distribution, current-engine clock/stat/trace/
replay and coaching-call/fallback diagnostics in a new immutable cohort root.

## Validation boundary

This documentation-only audit changes no production behavior. Its synthetic
probability control places a modifier on row 1 in one column and rows 2+5 in
another: both have mass 12/36 despite different rows. Exact physical enumeration
and aggregate counts are retained in the private receipt. Applicable existing
issue/documentation checks passed on the documentation diff from `b232fd9`:

```sh
/Users/rtulloh/work/bowl_bound/.venv/bin/python scripts/build_issue_index.py
/Users/rtulloh/work/bowl_bound/.venv/bin/python -m pytest -q tests/test_issue_tracker.py tests/test_priority_docs.py tests/test_release_player_docs.py
git diff --check
```

Result: **22 passed in 0.59s**, with no skips or warnings; generated index and
whitespace checks pass. No artificial behavioral regression or historical chart
fixture is added to CI. Production source remains identical to `b232fd9`.
