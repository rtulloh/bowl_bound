# Difficulty and Easy CLI coaching — owner-approved target

Approved 2026-10-27; tracks AI-002 and CLI-041 in Milestone 21. This document
specifies the implementation contract. Controls are now present in the worktree;
full acceptance/review and commit are still pending.
It supersedes the initial baseline/chart player-facing naming proposal.

## Shared difficulty

Choose difficulty in browser setup or with CLI `--play -d easy`, `-d medium`,
or `-d hard`. **Medium is the default.** Difficulty affects decisions and
coaching, never physical dice distributions, engine rules or team-chart values.

| Mode | Aggression | Main distinction |
| --- | --- | --- |
| Easy | 0.3 | Conservative CPU and CLI player coaching |
| Medium | 0.5 | Balanced CPU with a coarse early-down run/pass strength adjustment |
| Hard | 0.7 | Aggressive CPU, 32-sample isolated real-engine candidate evaluation, recent-call variety and committed-public opponent tendencies |

Implement these as genuinely different policies, not three aliases. No Paydirt
runtime dependency or imported NFL rules. Both interfaces must select the same
versioned policy; loading a save restores its policy rather than silently applying
the current new-game default. Compatible baseline saves retain their future calls;
older engine-profile saves are rejected, not migrated.
Hard history may use only already committed public plays, never the current hidden
selection. Save/continuation tests must cover recent-call and tendency history.

Hard uses Monte Carlo samples of real physical-face dice in isolated sessions,
not an exact individual-play chart probability distribution. It settles supported
secondary procedures, values points plus heuristic field preference, and retains
whole-comparison fallback on a failed candidate. The exact chart-probability
library remains a separate tested foundation. None of these estimates is a
calibrated win probability.
The CLI is exclusively solitaire: choose which team to control, with the computer
controlling the opponent. No manual mode, paired calls or two-sided timeout keys.
Engine-level explicit calls remain available for synthetic testing.

## Easy player coaching

The CLI helper is available **only in Easy**, enabled by default. `Z` at play
selection toggles it without advancing game state or dice. Medium/Hard cannot
enable it. These keyboard controls do not imply a browser helper panel.
`?` expands the full compact-mode menu; `/` shows statistics.

The offensive helper ranks up to three currently callable plays. Use target
yardage rounded up, minimum one yard:

| Down | Target |
| --- | --- |
| First | Half the distance to gain |
| Second | 70% of the distance to gain |
| Third/fourth | Full distance to gain |

For second-and-seven the target is five yards; for third-and-seven it is seven.
Display target-reaching percentage, positive-gain percentage, average yards and
evaluated chart coverage, plus **separate** situation/clock tips.

### Estimate semantics

- Weight **plain numeric offensive chart cells only** using exact Bowl Bound dice
  multiplicities, not a uniform average of chart rows.
- Exclude missing rows and every symbolic outcome, including penalties, turnovers,
  breakaways and BLACK. Never substitute a zero-yard result for excluded mass.
- Do not resolve a particular defense, the priority chart or secondary procedures.
- Target rate, positive-gain rate and average yards are conditional on evaluated
  numeric probability mass. Coverage is that evaluated share of total chart
  probability, **not** a confidence interval.
- Mark coverage below 50% **limited** and rank it behind better-supported estimates.
  A perfect rate over sparse coverage is not evidence of guaranteed success.
- These are **not full-engine conversion odds**. Keep this display distinct from
  Hard's isolated full-engine candidate valuation.
- Defensive suggestions are situational advice, not an adaptive model learning
  the CPU's calls during CLI play. No current concealed call may enter advice.

## Implementation and acceptance gates

1. Test each tier and Easy-helper estimator before implementation with synthetic
   charts. Specify deterministic ranking ties and zero-numeric-coverage behavior.
2. Preserve save-policy compatibility, public observation boundaries and dice
   neutrality; choose explicit helper-preference persistence semantics.
3. Integrate API and browser setup together; validate UI/build using Node 24.22.1.
4. Audit independent seeds, both team arrangements and both human sides. Review
   call distributions, comparable repetition, fallbacks, state/clock/statistics,
   traces and save continuation, not scores alone.
5. Update runtime user docs only when these behaviors are actually available.
   Keep AI-002/CLI-041 open pending tested commit references and owner play-test.
