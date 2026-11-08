# Common source observations for reference benchmarks

This extends the [frozen benchmark method](reference-benchmark-method.md) with
descriptive source populations. It does not establish historical accuracy or
change charts. Both generated and reference charts receive the same target
binding; reference cells and simulated call mixtures are never source inputs.

## Population and identity

Freeze original normalized bytes, the baseline's exact source-game IDs and the
canonical JSON hash of the original filtered event dictionaries before parsing
them into other objects. Preserve original event order, exclusions and raw versus
conditioned counts. Do not substitute the smaller comparison schedule for the
generation population. Within that population, primary observations select the
actual offensive team or opponent explicitly, exclude no-play records and exclude
conversion plays. PAT observations retain their separate conversion population.
Duplicate game/event identities refuse rather than inflate a denominator.

The maintained `tools/reference_targets.py` helper consumes those dictionaries
without mutation. It does not import the research generator or infer historical
Bowl Bound calls. Missing structural identity or noninteger yardage refuses;
explicit unknown yardage remains part of its eligible population.

## Metric contract

| Observation | Numerator | Full eligible denominator |
| --- | --- | --- |
| Completion | Complete provider events | Complete + incomplete + interception |
| Interception | Interception provider events | Same pass attempts |
| Sack | Sack provider events | Pass attempts + sacks |
| Pure rushing yards | Known rush yards | Rush events |
| NCAA rushing yards | Known rush + sack yards | Rush + sack events |
| Completion yards | Known complete-event yards | Complete events |
| Passing yards per attempt | Complete-event yards; zero for incomplete/INT | Pass attempts |
| Kick/punt distance | Known distance | Team's corresponding kick events |
| Kick/punt/INT return | Known return distance | Corresponding events against the returning team |
| PAT good | Provider-reported good status | Team's PAT events, including unknown statuses |

Every metric retains full eligible, known and unknown counts, known numerator,
unknown event identities and per-game counts. An exact point observation exists
only with nonempty complete measurement of that eligible population. A known-only
mean is labeled separately; it is never a full-population estimate. Sack and
passing/rushing populations follow the documented Bowl Bound/NCAA accounting
distinction. Provider classification itself still requires source review.

Unconditional INT catch depths retain an observed histogram and unknown CDF
envelope. At each observed atom the lower bound is known depth mass at or below
that point divided by all INT events; the upper bound includes every unknown.
Conflicting direct/air-depth values are unknown, not silently selected. No yardage
cap, tail imputation or point mean for missing depths is invented.

Designed-call depth samples additionally require the exact call number, narrative
confidence and matching explicit Screen/Sprint Out/Boot-leg/Drop Back marker.
Generic deep-pass language does not qualify. The denominator includes matching
events with unknown depth. These samples cannot establish full historical call
or formation frequencies; authored priors remain separate.

## Interpretation and transfer

The existing two conditioned source populations and eight preregistered teams
are reused. The four reference teams are retrospective development comparisons;
the four deterministically selected nonreference teams test the same procedure,
not an untouched prospective claim. The 2008 neutral research baseline remains
distinct from the published 2007 profile. No additional season is published.

Legacy provider annotations do not independently certify completeness. Fumble
mechanism, charged field-goal eligibility, OOB completeness, score/pace and
historical formation targets remain outside this helper. PAT good/miss and return
observations retain their provider limitations. No artificial six-game threshold,
reference-match tolerance or new confidence guarantee turns them into qualified
historical truth. Later uncertainty uses game clusters and states systematic
missingness limits, rather than treating repeated plays or seeds as independent.

Consulted Paydirt's `chart-reference-comparison-protocol.md` for common target
populations, transfer labels and cluster cautions. Adapt those principles; do not
reuse its NFL populations, numerical gates, source data or runtime. The comparison
remains incomplete until terminal residuals, games and material discrepancies are
reviewed under their own frozen identities. DATA-046 stays open.

## Bounded verification checkpoint

The explicit private run reuses two exact conditioned populations: 129,078 events
in 682 game clusters and 137,736 events in 765 game clusters. All eight
preregistered teams have offense and defense observations, with identical target
bindings available to either chart set. Original normalized bytes, canonical
filtered dictionaries, game IDs and all 52 source/input/code pins reconcile and
remain unchanged. No source files were copied or rewritten.

All 16 team/side INT known/unknown depth counts reconcile with the earlier frozen
source inventory. None has eligible explicitly identified designed-call support.
Unconditional depth envelopes and missing return measurements remain visible;
available provider yardage is not proof that the source population is complete.
No simulation error, historical-fit score or confidence interval was computed.

Fifteen synthetic controls cover denominator choices, role selection, missing
yardage and depth, conflicting depth fields, conversion exclusions, exact call
markers, receiver ownership, duplicate identities and nonmutation. The applicable
401-test regression includes the inventory, exact chart measures, normalization,
ordinary loader, models, dice and documentation checks. Static checks pass. The
initial missing-module collection failure is a feature scaffold, not evidence of
an old gameplay defect. Detailed observations and identity receipts stay private.
