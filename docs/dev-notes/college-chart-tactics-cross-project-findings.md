# Transferable defensive-chart findings — 2026-11-05

This note is safe to share with the separate Paydirt investigation. No Paydirt
source, data or release was changed by the Bowl Bound work.

Bowl Bound's cause is established: its generated 116-team cohort used a neutral
tactical profile with all A–F/play offsets zero. The engine applies chart facts
without a hidden formation bonus. All nine plays have identical exact defensive
outcome distributions across A–F; all four pass columns are also equivalent within
each formation. Team defensive strength does vary between teams. This is a
missing tactical model, not one team chart copied everywhere or a viewer defect.

Paydirt starts from a **nonzero tactical template**, then applies team efficiency
and disruption changes (`paydirt/chart_generator.py`, `_DEFENSE_TEMPLATE` and
`_generate_defense`; `docs/dev-notes/statistical-chart-generator.md`, “Defense
Generation”). The same zero-profile cause is therefore **not established in
Paydirt**. Its template's presence does not independently prove its final resolved
tradeoffs. That is for the separate session to test with Paydirt's own rules.

Different-looking cells, unique CSVs and different seeded games do not establish
different probability distributions. Bowl Bound's physical defensive totals have
masses **12, 11, 9, 3, 1 out of 36**. A modifier on row 1 has mass 12/36; placing
the same modifier on rows 2 and 5 has mass (11+1)/36, also 12/36. Those charts look
different but have the same weighted distribution. Verify each game's own dice
before applying this counterexample to it.

Keep four questions separate:

- **Team strength:** with tactical policy and offense fixed, does a stronger
  defensive team change outcomes in the intended direction?
- **Formation contrast:** with team and offensive call fixed, does changing the
  defense create a declared benefit and a corresponding vulnerability?
- **Play contrast:** with team and formation fixed, do the defensive columns
  distinguish calls? Control the offensive inputs so their differences do not
  masquerade as defensive differences.
- **Resolved outcomes:** after priority, protected cells, Option, B/QR/QT and
  other supplemental rules, do the intended differences survive? Count pending
  penalties/recoveries separately; do not turn unknown branches into zero yards.

The first Bowl Bound correction proposal added response probabilities. Mixed-rate
tests caught an allocation hazard: rare responses occupied masses 1 and 3, leaving
the next event only 0 or 9/36 as its smallest choices. A requested probability
0.126 encoded as 0.25; adding QT also introduced unintended INC and INT changes.
Nearest attainable allocation can be implemented correctly and still have a poor
model result. This is a transferable finite-row testing hazard, **not a finding
that Paydirt's different allocator exhibits it**.

Root selected a narrower original **yardage-only experimental Bowl Bound policy**.
It adds formation/play benefits and costs while preserving existing response-rate
targets and printed nonnumeric cells. It is separate from measured team strength,
not empirical tactical calibration or reference-chart fitting. Synthetic tests
cover 27 mixed-rate/strength/seed contexts, ordinary gains 4/10/18 and all 216×36
primary dice pairs, including cross-strength ordering and pairwise counterplay.
Selected-policy priority/supplemental and tiny-cohort checks precede full cohort
regeneration. Passing these controls is not a claim of historical accuracy.

For Paydirt, test the template **after** all strength/rate transformations and
engine resolution; inspect intended directional costs as well as benefits. Do not
copy Bowl Bound coefficients, play numbers, dice assumptions or rule decisions.
Aggregate means or a completed season alone cannot establish tactical contrast.
