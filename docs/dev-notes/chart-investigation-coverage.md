# Outstanding chart investigations after Alpha 9

Reviewed 2026-11-07 against the owner's chart-generation, benchmark, season-validation and release questions. Alpha 9 is an accepted experimental release; it is not a historical-accuracy certification. All investigations below remain open. Public-safe summaries consolidate ten existing research tickets without changing their IDs or claiming that pending research fixes are integrated. DATA-063 is a new dedicated investigation.

| Question | Accountable ticket(s) |
| --- | --- |
| Can automated qualification carry the load without community feedback, and catch clustering of any outcome family? | [DATA-045](https://github.com/rtulloh/bowl_bound/issues/104) |
| How do generated charts compare with authorized 2007/2008 developer references, and transfer to seasons without a baseline? | [DATA-046](https://github.com/rtulloh/bowl_bound/issues/105), [DATA-045](https://github.com/rtulloh/bowl_bound/issues/104) |
| Can missing teams, failed games, pooled averages or weak precision hide a bad result? | [DATA-048](https://github.com/rtulloh/bowl_bound/issues/106) |
| Are field-goal outcomes accurate for supported distances and attempt populations? | [DATA-049](https://github.com/rtulloh/bowl_bound/issues/107) |
| Do complete games and repeated actual seasons reflect team strengths, weaknesses and plausible postseason outcomes under baseline and Hard policies? | [DATA-053](https://github.com/rtulloh/bowl_bound/issues/108) |
| Does the selected year use actual regular fixtures and declared postseason rules, with historical-only assessment when no developer charts exist? | [DATA-054](https://github.com/rtulloh/bowl_bound/issues/109) |
| Is every event independently accounted for, including QT classification and the known kickoff-return fumble recovery-draw observer gap? | [DATA-055](https://github.com/rtulloh/bowl_bound/issues/110) |
| Are missing opponents, fixtures, source coverage, codecs and crosswalks qualified before full-season campaigns? | [DATA-056](https://github.com/rtulloh/bowl_bound/issues/111) |
| Are source phase overrides, loaded runtime identity and versioned coaching menus trustworthy? | [DATA-057](https://github.com/rtulloh/bowl_bound/issues/112), [DATA-058](https://github.com/rtulloh/bowl_bound/issues/113), [DATA-059](https://github.com/rtulloh/bowl_bound/issues/114) |
| Are formation event budgets, retained INT stripes, conditional depths and authored priors justified beyond visual variety? | [DATA-060](https://github.com/rtulloh/bowl_bound/issues/115) |
| Does a genuine pooled interception depth support its assignment to Screen or another particular passing play? | [DATA-064](https://github.com/rtulloh/bowl_bound/issues/117), required next-release correction in [Milestone 42](milestone-42.md) |
| When should rare defensive (B) cells be awarded, and what exact probability/tail effects follow? | [DATA-063](https://github.com/rtulloh/bowl_bound/issues/116) |
| Which recent and legacy years have enough lawful, reliable source support? | [DATA-037](https://github.com/rtulloh/bowl_bound/issues/100) |
| How should the AI value a penalty that repeats a two-point try? | [AI-034](https://github.com/rtulloh/bowl_bound/issues/36) |

The rare defensive (B) question is analysis first. No implementation or new regeneration is implied by this inventory. Razzle-Dazzle is an artificial engine action, not a source chart play family. Keep source, chart lookup, Priority, terminal outcome, policy exposure and historical-fit claims distinct.

Consulted Paydirt's local DATA-040 and DATA-041 before this documentation phase. Relevant findings: ordered allocation/shared templates can create interception stripes, fixed depth support needs separate qualification, and per-weight preservation can freeze QT blocks. Adapt the broad census and probability/conditional-outcome checks; do not import NFL rules, Paydirt weights, source data or a runtime dependency. Detailed Bowl Bound research histories remain private; only concise investigation scopes are consolidated here.

For each investigation, retain a frozen scope and reproducible evidence, test behavior changes with synthetic controls first, record tested integration commits before resolution, and require applicable play-test confirmation before closure. When a model or observer changes, renew affected evidence. Publication does not silently close these tickets, and incomplete full-season or accuracy qualification must not be reported as passing.

Validation for this documentation-only review: regenerated the issue index; all 38 issue metadata/index/creation and applicable documentation tests pass; all 32 local documentation links resolve; reciprocal ticket links and git diff whitespace checks pass. No gameplay, chart, generation-model or release-asset bytes changed.

2026-11-07 execution update: owner moved DATA-046 and DATA-055 into Milestone 42
alongside DATA-064 and authorized a high-reasoning subagent to implement that
milestone. Their complete acceptance criteria remain in force; broader tickets
retain their existing ownership and scope.

2026-11-07 release-target update: owner selected 1.0.0 for Milestone 42's next
release, superseding Alpha 10. DATA-046/055/064 acceptance requirements remain
in force. See [1.0.0 preparation](release-1.0.0.md).
