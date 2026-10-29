# Bowl Bound dice

`bowl_bound.dice` implements Basic IV-1 (printed p. 2) of the local rules reference
identified in [the rules profile](rules-profile.md). It has no PDF or Paydirt dependency.

Each tuple below has six entries, one per physical face; repeated numbers are intentional.

| Die | Faces |
| --- | --- |
| Black | 1, 2, 2, 3, 3, 3 |
| First white | 0, 0, 1, 2, 3, 4 |
| Second white | 0, 1, 2, 3, 4, 5 |
| Red | 1, 1, 1, 2, 2, 3 |
| Green | 0, 0, 0, 0, 1, 2 |

`OffensiveRoll.total` is ten times black plus both white faces (10–39). Its
`direct_sum` adds all three faces without the tens multiplier. `DefensiveRoll.total`
is red plus green (1–5). Frozen roll objects reject impossible faces, non-integers,
and booleans; passing a total instead of individual faces is not supported.

## Published distributions

Basic IV-1 gives both the physical face values (described as opposite face pairs)
and the total frequencies below. The tuple ordering above does not encode physical
opposition, since random sampling and direct-sum calculation do not depend on it.

Offensive total: rolls out of 216 (tens digit scales by black die: x1, x2, x3 for 10s, 20s, 30s).

| Ones digit | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 10s | 2 | 3 | 4 | 5 | 6 | 6 | 4 | 3 | 2 | 1 |
| 20s | 4 | 6 | 8 | 10 | 12 | 12 | 8 | 6 | 4 | 2 |
| 30s | 6 | 9 | 12 | 15 | 18 | 18 | 12 | 9 | 6 | 3 |

Defensive total: rolls out of 36.

| Total | 1 | 2 | 3 | 4 | 5 |
| --- | --- | --- | --- | --- | --- |
| Rolls | 12 | 11 | 9 | 3 | 1 |

## Injectable sources

Engine code will accept the `DiceSource` protocol, whose `offensive()` and
`defensive()` methods return complete roll objects.

```python
from random import Random

from bowl_bound.dice import DefensiveRoll, OffensiveRoll, RandomDice, ScriptedDice

random_dice = RandomDice(Random(73))
script = ScriptedDice((OffensiveRoll(3, 2, 5), DefensiveRoll(1, 0)))
assert script.offensive().total == 37
assert script.defensive().total == 1
```

`RandomDice` samples physical faces, never uniform chart totals. Identically seeded
Python generators reproduce identical request sequences within the same Python
random implementation; no cross-version save compatibility is promised here.
`ScriptedDice` copies its input and enforces the combined offensive/defensive request
order. Exhaustion or a wrong-kind request raises `DiceSequenceError`; a wrong-kind
request does not consume a roll. The source never silently falls back to randomness.

Tests enumerate all 216 offensive and 36 defensive combinations and compare the
complete frequency tables with the published distribution, not a statistical sample.
Variable-yardage and structured-trace resolution build on these sources.
[Versioned save/resume](saves.md) records observed physical faces and persists the
future random state under an explicit engine/Python compatibility boundary.
