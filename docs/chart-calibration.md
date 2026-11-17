# Chart generation and calibration recipe

This guide is for people running the public generator from a source checkout.
No AI assistant, private agent script or Paydirt checkout is needed to execute
the commands. The game's native download does not contain this development
toolchain. Use Python **3.12** and run the commands from the repository root.
The shell examples use Bash on macOS/Linux. On Windows, use an equivalent Bash
environment or translate environment assignments and use your Python 3.12
virtual environment's interpreter.

Calibration is required when producing a new or regenerated cohort or changing
its source/model context. It includes measuring the baseline; a coefficient
does not have to change if the neutral result qualifies. Successful generation
and a passing structural audit alone do not establish precision or release
acceptance. See [the required workflow](chart-generation.md#mandatory-calibration-and-acceptance).

## 1. Prepare the tools and reviewed inputs

Use an existing Python 3.12 development environment, or create one:

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -e '.[dev,web,pdf,generator]'
.venv/bin/python --version
.venv/bin/python -m tools.chartgen --help
```

Create a new working directory for each investigation. These examples use
`private-data/chart-calibration-2002/`; choose a new name rather than overwriting
an existing experiment. The supported execution seasons are currently 2002 and
2007. The same process applies to either supported season after updating the
paths and plan. Supporting a different season needs a reviewed model/contract
change, not just a different directory name.

Acquire source data only when you are authorized to do so:

```sh
mkdir -p private-data/chart-calibration-2002
.venv/bin/python -m scripts.acquire_chart_source \
  --season 2002 \
  --output private-data/chart-calibration-2002/source --workers 4
```

If you already have a reviewed normalized snapshot, place it at
`private-data/chart-calibration-2002/source/normalized.json` instead. Keep its
original acquisition and adjudication receipts. Do not reacquire a cleaned
snapshot merely to follow this example.

Review `coverage.json`, game inventories and source facts before generating.
Acquisition success means the listed endpoints were checked, not that the
season is complete. Unknown primary gains, fumbles or gross kick distances must
be reconciled using evidence; never fill them with convenient zeros. The
[source guide](chart-generation.md#acquire-and-normalize-source) explains the
normalization and reviewed-adjudication paths. Source review is a human task;
the commands below cannot establish historical truth for you.

Create `private-data/chart-calibration-2002/selected-teams.json`, mapping actual
source IDs to display names. The following is a **format example with fictional
IDs**, not a ready-made historical selection:

```json
{
  "fictional-source-id-1": "Cedar Valley",
  "fictional-source-id-2": "Harbor Tech"
}
```

Replace both keys and names with your reviewed cohort from the acquired
`teams.json`. Include only teams with sufficient season-specific source evidence.
Do not treat every opponent mentioned in a feed as a complete team-season.
The panel recipe needs at least two selected teams from the same season.

## 2. Write the experiment plan before looking at results

Save `private-data/chart-calibration-2002/plan.json`:

```json
{
  "season": 2002,
  "generation_seed": 1,
  "timebox_minutes": 120,
  "maximum_trial_profiles": 3,
  "training": {
    "master_seed": 20311031,
    "games_per_team": 4,
    "minimum_samples": 1000
  },
  "validation": {
    "master_seed": 20311101,
    "games_per_team": 64,
    "minimum_samples": 2000
  }
}
```

These are an editable example plan, not a universal sample-size policy or a
runtime estimate. Choose exposure, timebox and a finite list of proposed changes
before starting, based on cohort size, source coverage and required precision.
Game counts must be positive and even for this balanced-panel example. The
existing assessment uses raw outcome denominators, with separate limits for
sparse kick/return/PAT observations; inspect game-cluster counts and uncertainty
as well. Four training games per team will often be insufficient for statistical
acceptance: they screen a direction, not qualify a release. Even 64 validation
games do not guarantee enough observations for every metric.
The copyable drivers do not enforce wall-clock or trial-count limits for you;
record the start time, monitor progress and stop at the declared limit. Preserve
an interrupted run as incomplete evidence rather than a pass.

Write down the question, permitted parameter(s), expected direction and stopping
rule alongside the plan. For example: investigate low non-sack rushing efficiency
by changing only the shared rushing scale. Preserve completion, passing,
turnover, special-teams and per-team checks. Use the existing experimental
references in `tools/chartgen/refine.py:TOLERANCES`, or separately review a new
policy **before** running it. Do not loosen a bound after seeing a miss.

## 3. Generate the neutral cohort and one justified trial

Save this as `private-data/chart-calibration-2002/generate-candidate.py`:

```python
import json
import sys
from pathlib import Path

from tools.chartgen.generate import CalibrationProfile
from tools.chartgen.release_pipeline import generate_release_cohort
from tools.chartgen.source import read_normalized

work = Path("private-data/chart-calibration-2002")
label, profile_file = sys.argv[1:]
plan = json.loads((work / "plan.json").read_text())
events, _ = read_normalized(work / "source/normalized.json")
teams = json.loads((work / "selected-teams.json").read_text())
profile = CalibrationProfile(**json.loads(Path(profile_file).read_text()))
receipt = generate_release_cohort(
    events,
    teams,
    plan["season"],
    work / label,
    seed=plan["generation_seed"],
    profile=profile,
)
print(receipt["status"], len(receipt["teams"]))
```

Create `profile-neutral.json` in the same working directory containing `{}`.
Omitted fields use neutral defaults. Run:

```sh
PYTHONPATH=. .venv/bin/python private-data/chart-calibration-2002/generate-candidate.py \
  baseline private-data/chart-calibration-2002/profile-neutral.json
```

The complete cohort pipeline is required here. Its CLI `generate` command
currently has no profile option; use the public Python API above for calibrated
cohorts. The older single-team phase-one helper is not a substitute for this
pipeline. Outputs include ordinary files under `seasons/`, a paired allocator
baseline under `baseline/`, and `generation-receipt.json` with exact pins and
per-team profiles. A new output directory is required. Preserve any failed
receipt and partial output; a partial cohort is not a successful generation.

First measure the neutral charts using step 4. Only then create a justified
`profile-trial-01.json`. For the already reviewed 2002 investigation it contained
`{"run_yards_scale": 1.15}`; that number is **not a recommendation for another
cohort**. The scale acts before finite chart quantization, not on engine results.
The observed/source YPA ratio may suggest a direction but is not an exact
correction formula. Review call mixture, sacks, fixed plays, defense and source
coverage before attributing an error to the scale.

```sh
PYTHONPATH=. .venv/bin/python private-data/chart-calibration-2002/generate-candidate.py \
  trial-01 private-data/chart-calibration-2002/profile-trial-01.json
```

Keep other offensive settings and all defensive settings neutral for a one-knob
experiment. If a later investigation justifies defensive changes, the same API
accepts `defensive_profile=DefensiveProfile(...)`; record and revalidate them.

## 4. Run matched real-engine panels

The following copyable driver uses the existing research engine runner and
observers. It does not implement football rules. It deliberately uses a
**generated balanced schedule**, not the actual historical schedule. For a
historical-matchup study, substitute independently reviewed `GameSpec` fixtures
with verified home/away identities and freeze them before either chart run.
Record opponents excluded from the cohort and do not call either panel a full
historical-season reproduction.

Save as `private-data/chart-calibration-2002/run-panel.py`:

```python
import gzip
import hashlib
import json
import math
import sys
from dataclasses import asdict
from pathlib import Path

from bowl_bound.cli import TeamCatalog
from tools.chartgen.current_runtime import reference_options
from tools.chartgen.primary_fumbles import observe_primary_results
from tools.chartgen.refine import (
    TOLERANCES,
    aggregate_games,
    assess_metrics,
    engine_identity,
    observe_chart_draws,
    source_targets,
)
from tools.chartgen.research_runner import _play_one, build_schedule
from tools.chartgen.source import read_normalized

work = Path("private-data/chart-calibration-2002")
label, phase = sys.argv[1:]
assert phase in {"training", "validation"}
plan_file = work / "plan.json"
source_file = work / "source/normalized.json"
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
plan = json.loads(plan_file.read_text())
assert plan["training"]["master_seed"] != plan["validation"]["master_seed"]
candidate = work / label
receipt_file = candidate / "generation-receipt.json"
receipt = json.loads(receipt_file.read_text())
assert receipt["status"] == "complete" and receipt["season"] == plan["season"]
runtime = engine_identity()  # Rejects stale reviewed source/runtime contracts.
identities = {"plan": sha(plan_file), "source": sha(source_file)}
if phase == "validation":
    selection = json.loads((work / "selection.json").read_text())
    assert selection["inputs"] == identities and selection["runtime"] == runtime
    assert label in {"baseline", selection["selected"]}
    assert sha(receipt_file) == selection["receipts"][label]


def verify_files():
    for name, pin in receipt["output_pins"].items():
        assert sha(candidate / name) == pin, name


def finite_json(value):
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, dict):
        return {key: finite_json(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [finite_json(item) for item in value]
    return value


verify_files()
catalog = TeamCatalog(candidate / "seasons")
entries = catalog.teams()
assert not catalog.problems and {entry.key for entry in entries} == set(receipt["teams"])
teams = {entry.key: catalog.load_with_metadata(entry.key) for entry in entries}
settings = plan[phase]
specs = build_schedule(
    entries,
    games_per_team=settings["games_per_team"],
    master_seed=settings["master_seed"],
)
events, _ = read_normalized(source_file)
out = candidate / phase
out.mkdir(exist_ok=False)
contract = {
    "inputs": identities,
    "runtime": runtime,
    "reference_options": reference_options(),
    "receipt_sha256": sha(receipt_file),
    "driver_sha256": sha(Path(__file__)),
    "specs": [asdict(spec) for spec in specs],
    "tolerances": TOLERANCES,
    "settings": settings,
    "scope": "balanced generated schedule; not historical fit",
}
(out / "contract.json").write_text(json.dumps(contract, indent=2) + "\n")
results = []
for index, spec in enumerate(specs, 1):
    pair = {key: teams[key] for key in (spec.home_id, spec.away_id)}
    result = _play_one(spec, pair, verify_replay=True, **reference_options())
    result["normalized_chart_draws"] = observe_chart_draws(result, pair)
    result["normalized_primary_results"] = observe_primary_results(result, pair)
    with gzip.open(out / f"game-{index:05d}.json.gz", "wt", encoding="utf-8") as stream:
        json.dump(result, stream)
    results.append(result)
    print(index, len(specs), result["status"], flush=True)
summary = aggregate_games(results)
targets = {}
assessments = {}
for key, team in receipt["teams"].items():
    targets[key] = source_targets(events, [team["source_team_id"]])
    assessments[key] = assess_metrics(
        summary["per_team"].get(key, {}).get("metrics", {}),
        targets[key],
        minimum_samples=settings["minimum_samples"],
    )
replays_ok = all(
    row.get("save_replay", {}).get("checkpoint_verified")
    and row.get("save_replay", {}).get("final_replay_verified")
    for row in results
)
summary.update(
    targets=targets,
    assessments=assessments,
    all_save_replays_verified=replays_ok,
    statistical_reference_passed=all(row["passed"] for row in assessments.values()),
    historical_fit="UNVERIFIED",
    source_holdout=False,
)
verify_files()
assert engine_identity() == runtime
assert {"plan": sha(plan_file), "source": sha(source_file)} == identities
(out / "summary.json").write_text(
    json.dumps(finite_json(summary), indent=2, allow_nan=False) + "\n"
)
assert summary["failed_games"] == 0 and replays_ok
print("PANEL_COMPLETE; inspect summary.json, samples, team misses and limitations")
```

This is a sequential driver; large panels take time and disk space. Its internal
`_play_one` research API is checked against the current reviewed runtime by
`engine_identity()`. If that check fails after a code change, stop and review
the changed contract; do not disable attestation. Do not run the ordinary
local-season CLI and assume its defaults match these research coaching options.
The recipe retains each game's detailed audit privately and fails on incomplete
games or failed save/replays. Missing measurements have null error values in
JSON and remain failed assessments; they are not zeros or passes.

Run the same training panel for the neutral and trial charts:

```sh
PYTHONPATH=. .venv/bin/python private-data/chart-calibration-2002/run-panel.py baseline training
PYTHONPATH=. .venv/bin/python private-data/chart-calibration-2002/run-panel.py trial-01 training
```

Compare the two `training/contract.json` fixture lists: they must be identical.
Inspect both `summary.json` files, particularly:

| Evidence | What to inspect |
| --- | --- |
| `failed_games`, replay flag and game logs | Every scheduled game completes with reconciled scores, clock, statistics and traces. |
| `metrics` and `per_team` | Outcome values, denominators, game clusters and standard errors; never rely solely on a pooled average. |
| `assessments` | Actual target, tolerance, insufficient-sample flags and all missed bounds for each team. |
| `pure_rush_yards_per_attempt` | Non-sack source and simulated rushing use matched definitions; NCAA rushing including sacks is a separate diagnostic. |
| Passing, turnovers, kicks and returns | A rushing change can alter shared breakaway/pass encoding and other outcomes. |
| `call_distribution` and private `coaching_calls` | Call mix, comparable-situation repetition, legal choices and fallbacks. |
| Points and offensive plays per team/game | Scoring and pace regressions; completion alone is insufficient. |

The source targets are references from the selected teams' observed data. An
artificial opponent mixture is not the source schedule, and missing designed-call
or formation observations remain authored assumptions. Sparse field-goal/distance
coverage and other metrics outside these helpers require separate review.
`statistical_reference_passed` is only this declared panel's metric result; the
driver deliberately does **not** label a cohort release-qualified.

### How to recognize a useful calibration result

Look for all of the following, rather than a plausible final score:

- Every selected team is represented, every scheduled game completes, the replay
  checks pass and scoring/clock/statistics/traces reconcile. Investigate illegal
  choices or coaching fallbacks before interpreting fit.
- Each required metric has enough observations. An `insufficient_samples` flag
  is a failed assessment even when its observed mean looks close. Read `n`,
  `clusters`, effective sample size and standard error together; thousands of
  plays in very few games do not provide thousands of independent games.
- Absolute errors satisfy the **predeclared** acceptance policy on unused
  validation seeds. Inspect the complete per-team table as well as pooled values.
  Record every miss; a pooled pass is not a statement that every team passes.
- The selected change improves the intended error without unacceptable passing,
  turnover, special-teams, scoring, pace or coaching regressions. Compare team
  mean absolute error and RMSE as well as the average outcome.
- The effect survives the validation panel and is material relative to simulation
  variation. Report uncertainty instead of treating a tiny mean difference as
  an improvement. Per-run standard errors are not automatically the standard
  error of a paired difference; retain the paired game records for that analysis.
- Independent generation reproduces the selected file hashes, and source,
  structural, gameplay, packaging and full regression checks also pass. Separate
  any explicitly approved experimental limitations from actual passes.

The current experimental point-reference tolerances in `refine.TOLERANCES` are:

| Metric | Maximum absolute error |
| --- | --- |
| Completion rate | 0.035, or 3.5 percentage points |
| Interception rate | 0.012, or 1.2 percentage points |
| Sack rate | 0.015, or 1.5 percentage points |
| Primary-fumble rate | 0.010, or 1 percentage point |
| Non-sack rushing yards/attempt | 0.5 yards/attempt |
| Passing yards/attempt | 0.7 yards/attempt |
| Drawn gross punt/kickoff and punt/kickoff return distance | 3 yards |
| Drawn interception-return distance | 5 yards |
| Field-goal success | 0.08, or 8 percentage points |
| PAT success | 0.04, or 4 percentage points |

Use the function's actual rate denominators; for example, sack rate uses passing
attempts plus sacks. A one-percentage-point error is 0.01, not a one-percent
relative error. `assess_metrics` checks point errors and sample counts; it does
not require an entire confidence interval to fit within a tolerance. The recipe's
`source_targets` does not supply a field-goal target: review distance-conditioned
kicking evidence separately rather than inventing a pooled target. These
experimental references do not certify historical accuracy or create a new
cohort's release policy automatically.

For an actual worked comparison, the selected 2002 study paired both chart sets
on 251 unused-seed fixtures:

| Rushing measure | Neutral charts | Selected charts |
| --- | ---: | ---: |
| Source non-sack target | 4.502 yards/attempt | 4.502 yards/attempt |
| Simulated non-sack rushing | 3.498 | 4.238 |
| Absolute pooled error | 1.004 | 0.264 |
| Mean absolute team error | 0.936 | 0.293 |
| Teams within 0.5 yards/attempt | 10/55 | 47/55 |

All 12 declared pooled references passed for that selected setting; eight teams
still missed the individual half-yard reference. The paired rushing improvement
was 0.740 yards/attempt with an approximate 95% simulation interval [0.616, 0.864].
That supports the measured improvement, not perfect team fit or independent
historical validation. See the [full result and limits](generated-charts.md#generated-2002-cohort).
Do not adopt its results, profile or accepted scope as a waiver for another cohort.

### How to improve a result that misses

First rule out missing/incorrect source facts, mismatched denominators, changed
opponent or coaching mixtures, sparse samples and an engine defect. Increasing
a scale is not a repair for any of those problems. If the model is the supported
cause, adjust one parameter in a new profile and preserve every earlier trial:

| Observed pattern | Next investigation or bounded adjustment |
| --- | --- |
| Rushing is consistently low/high across the cohort | Review non-sack accounting, fixed plays, call mix and defense first. If the residual is a yardage-response issue, test a higher/lower shared `run_yards_scale`. |
| Passing yards/attempt miss while completion and turnover rates are reasonable | Review gross/net passing and sacks, then test `pass_yards_scale`. Recheck completion, INT and shared breakaway effects. |
| Completion rate misses | Review observed attempts and classifications first; test a small `completion_shift` only for a supported response error. Recheck passing yards/attempt and event budgets. |
| INT, sack or fumble rates miss | Verify their denominators, primary versus return events and known/modelled absence evidence. Only then consider the corresponding `interception_scale`, `sack_scale` or `fumble_scale`. |
| Returns are consistently too short/long | Separate kick flight from return yardage and recovery advances before testing `return_yards_scale`; this affects several return types. |
| Gross punts/kickoffs miss | Review gross versus net/source return fields and finite quantization. A return-yardage scale does not correct kick flight. |
| Field-goal success misses | Review attempt distances, range support and makes/misses before considering `field_goal_shift`. It is not a PAT calibration knob. |
| Only a few teams miss, or errors have opposite signs | Review each team's coverage and uncertainty. A cohort-wide scale may worsen other teams; do not hand-edit cells or invent team-specific factors. |
| Formation/call behavior is distorted | Review authored tactical assumptions and the actual legal coaching distribution. Preserve event mass and counterplay; a structural audit is not a fit measurement. |

`CalibrationProfile` validates scale values in [0.6, 1.4] and shift values in
[-0.15, 0.15]. These are software bounds, not evidence that a value is sensible.
Offsets/shifts in `DefensiveProfile` have separate bounds; reserve them for an
independently justified defensive residual rather than moving both sides at once.
Finite dice masses, caps, rounding, protected cells and shared columns make the
response nonlinear. A source/observed ratio suggests a direction; measure the
regenerated charts instead of assuming the ratio produces the desired result.

Rerun the matched **training** panel and all affected metrics after each trial.
If the permitted experiment does not solve the miss, preserve that result and
document the next source/model question. Never change rules or targets, delete
unfavorable games, lower sample requirements after the fact or tune on validation.

## 5. Freeze the choice, then validate once on unused seeds

Choose using training evidence only. If a trial fails, preserve it and proceed
only within the predeclared finite search. If no setting qualifies within the
timebox, record that outcome rather than declaring the charts ready or trying
additional validation seeds until a favorable result appears.

After selecting a trial, run this once, changing `selected` if necessary. The
neutral baseline may also be selected if its measurements qualify.

```sh
PYTHONPATH=. .venv/bin/python - <<'PY'
import hashlib
import json
from pathlib import Path
from tools.chartgen.refine import engine_identity

work = Path("private-data/chart-calibration-2002")
selected = "trial-01"
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
record = {
    "selected": selected,
    "inputs": {"plan": sha(work / "plan.json"), "source": sha(work / "source/normalized.json")},
    "runtime": engine_identity(),
    "receipts": {
        label: sha(work / label / "generation-receipt.json")
        for label in {"baseline", selected}
    },
    "training_summaries": {
        label: sha(work / label / "training/summary.json")
        for label in {"baseline", selected}
    },
}
with (work / "selection.json").open("x") as stream:
    json.dump(record, stream, indent=2)
    stream.write("\n")
PY

PYTHONPATH=. .venv/bin/python private-data/chart-calibration-2002/run-panel.py baseline validation
PYTHONPATH=. .venv/bin/python private-data/chart-calibration-2002/run-panel.py trial-01 validation
```

If the baseline itself was selected, run its validation only once. Compare the
baseline and selected validation fixture lists, source/runtime identities and
the same metrics as training. Summarize paired changes, uncertainty, per-team
misses and any newly introduced regressions. Individual games follow different
paths after chart changes even when starting seeds match. Unused simulation
seeds do not constitute held-out historical source data. If validation fails,
retain the failure; a revised experiment needs a newly declared plan and fresh
independent validation evidence.

## 6. Reproduce the exact selected charts and review release inclusion

Run `generate-candidate.py` again with the same source, team selection, generation
seed and selected profile, using a new output label such as `reproduction`.
Compare `source_sha256`, model identity, complete team inventory, `output_pins`
and `baseline_pins` in both receipts. Every file pin must match. Generation
does not rerun source adjudication or grant distribution rights.

Before changing the release selection:

1. Independently review source coverage/corrections, modeled versus observed
   quantities, unknowns, statistical results and full current-engine game evidence.
   Record the actual source-review and OOB-review artifact hashes. The automated
   gate cannot create this qualification for you; never invent approval hashes.
2. Follow [generated-chart release audits](generated-chart-audits.md) to produce
   the reviewed cohort expectations. Keep prior cohorts' qualification objects
   intact when composing schema 4. An audit must bind the selected calibrated
   candidate to **its own paired allocator baseline**, not another profile's files.
3. Obtain the applicable source/distribution approval and add only the exact
   generated-file pins. Review roster names/positions/provenance separately and
   pin exactly the approved roster/source-note pairs. Never copy or unignore the
   whole local seasons tree, raw feeds, PDFs, caches or detailed audits.
4. Run the chart audit against the actual maintained manifest and run the full
   regression. Use the Node version/dependencies required by the repository's
   [test workflow](../.github/workflows/tests.yml) and browser setup.

```sh
.venv/bin/python -m scripts.audit_generated_charts \
  --report private-data/chart-calibration-2002/maintained-chart-audit.json
.venv/bin/python scripts/run_full_regression.py \
  --report private-data/chart-calibration-2002/full-regression.json
.venv/bin/python -m pytest --cov --cov-report=term-missing -n 4 --dist=loadgroup --durations=25 -q
```

For earlier feedback while working, the existing synthetic checks include:

```sh
# Complete cohort export, profile plumbing and deterministic ordinary files:
.venv/bin/python -m pytest tests/chartgen/test_release_pipeline.py -q
# Refinement, statistical measurement and reviewed runtime identity:
.venv/bin/python -m pytest tests/chartgen/test_refinement.py tests/chartgen/test_current_runtime.py -q
# Exact packaged selection, cohort separation and roster loading:
.venv/bin/python -m pytest tests/test_release_package.py tests/test_multiseason_chart_audit.py tests/test_roster.py -q
```

Changes to normalization or a fitting/model component also require its focused
synthetic tests and the relevant cumulative `tests/chartgen/` suite. For a code
behavior change, first demonstrate the regression on the unchanged implementation.
These checks test software contracts; they do not replace source qualification
or the real-engine training/validation panels. A profile-only change still needs
fresh generated artifacts and applicable measured validation.

If team selection, season behavior or the UI changes, include the real-engine
browser suite. For focused cross-season feedback after installing the documented
frontend/browser dependencies:

```sh
cd frontend
npm run test:e2e -- e2e/crossSeason.spec.js
```

Run the full browser suite through the regression gate before pushing, and
explicitly exercise a 2002-versus-2007 pairing in the assembled artifact: both
canonical IDs, side swapping, the home season's rules, game startup and
save/reload must stay correct. A source/browser pass does not certify a native
download built from different bytes.

Retain failures, warnings and skips. A failed dependency audit or packaging check
still fails release acceptance even if the statistical panel passes. Verify the
assembled catalog, rosters, commentary and save/load in the API and browser;
native builds and verification of actual published install artifacts remain
separate requirements in the [release guide](dev-notes/release-builds.md).

Record the tested commit, exact source/code/profile/chart identities, commands,
panel and sample policy, comparison tables, uncertainty, failed bounds and
remaining limitations in the issue and milestone notes. Keep detailed historical
evidence ignored; publish only approved charts and a public-safe summary.
For a worked result, see the [selected 2002 cohort](generated-charts.md#generated-2002-cohort).
Its 1.15 profile and acceptance scope do not transfer to another season.
