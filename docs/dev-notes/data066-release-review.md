# DATA-066: 2002 season candidate for v1.1.0

Status: both full regression gates pass and the reviewed generator/packaging
changes are integrated. New-chart distribution review and maintained season
acceptance remain open. This is not a release or historical-fit certification.

The recovered public generator produces **55 selected 2002 teams**, replacing the
older 52-team attempt with a separately identified source snapshot. The combined
review package has **173 playable teams**: 55 new 2002 teams, the unchanged 116
published 2007 teams and two original fictional samples. This selected cohort is
not the entire 2002 college schedule. Every new team has a season-correct
commentary roster; several are explicitly partial, spring, depth or bowl lists.

| Check | Evidence and scope |
| --- | --- |
| Source replay | All 506 retained games normalize deterministically; 99 reviewed official factual corrections replay exactly. All 524 inferred interception spots match raw next-drive starts. Provider consistency does not certify independent historical completeness. |
| Chart files | All 550 final/baseline pins verify; all 55 final bundles load normally and pass the current semantic/budget checks. |
| Combined package | The independent audit passes 171 generated teams; all 580 existing 2007 chart/provenance pins remain unchanged. Exact new selection: 275 generated files and 110 roster/source-note files. |
| Complete games | 55 balanced-panel games and 251 selected historical opponent fixtures pass scoring, clock, statistics, legal coaching and checkpoint/final replay review. These are different panels, not full source-schedule coverage. |
| Roster integration | All 55 pass packaged API and CLI narration, save/load and named/generic RNG equivalence. |
| Browser | All 72 unchanged real-engine tests pass in local Linux. The actual package separately passes exact catalog/team selection, roster narration and UI download/save/load for all 55 new teams in drive mode. No Mac browser is launched. |
| Packaging changes | 255 synthetic staging/audit/native/archive/installer checks pass in an isolated copy. They do not certify native executable builds. |
| Python coverage | Both full gates pass **6,886 tests** at **90.77% branch-enabled coverage**, with no skips or warnings: source-only in 5,198.89 seconds; expanded 173-team proposal in 3,034.69 seconds. Independent receipts verify every original case exactly once, all 1,601 source / 1,987 proposal pins and the measured import roots. Earlier schema/catalog/roster assertion failures and their precise corrections are preserved in the recovery record. |

The actual-matchup rushing assessment **fails the retained experimental reference**:
3.564 simulated versus 4.502 source non-sack yards per attempt. Fixed QB Sneaks,
call mixture, quantization, defense and physical yardage accounting were examined;
no engine defect or justified coefficient correction was established. Do not
inflate chart gains or claim historical fit. The existing 2007 cohort also retains
a failed rushing assessment; its community-testing approval does not grant a new
2002 fit waiver or distribution permission.

Other disclosed limits include modeled narrative-incidence fumble negatives,
260 unresolved recovery associations under the clock fallback, sparse gross-kick
and blocked-punt locations, unknown OOB observations and authored designed-call
priors. Full details and receipts are in the
[generator recovery record](data066-generator-recovery.md).

The exact private review archive is
`private-data/data066-full-release-review-v2/unpublished-review-runtime.zip`,
SHA-256 `c4c5bdf8d6693362b2d2e5a8d5b79dbc3199b987cd0b82fb2a8f1a8cd41e0472`.
Runtime manifest SHA-256:
`e7c2a783f8e2f6028b307a07dc1ee76aa4a1ec3fb0bb97e0767968323c1c703f`.
It retains the current 1.0.1 application version and is an unpublished review
artifact, not a frozen v1.1.0 native release. Historical rosters were already
authorized for the selected release cohort under [DATA-067](issues/DATA/DATA-067.md).

Remaining work is to record the new-chart distribution basis and explicit
current approval for this exact experimental cohort, then accept its maintained
release selection. The 2007
SportsDataverse grant does not cover the fresh 2002 ESPN/core and official-gamebook
inputs. Proposed release inclusion must distinguish the new generated 2002 Ohio
State/Miami outputs from the original private imported benchmarks; original private
files remain excluded. No raw narratives, source PDFs, logos, source caches, saves
or detailed audit logs are proposed for publication.

After that review, update the maintained exact manifest, cohort audit and scoped
attribution together, repeat checks affected by final bytes, and commit with the
`v1.1.0:` prefix. Version preparation, native builds and verification of actual
published install assets remain subsequent release phases. Do not label the season
release-qualified or resolve DATA-066 before its acceptance work is committed.

Distribution review should distinguish factual inputs from their source expression:
the [U.S. Copyright Office](https://www.copyright.gov/help/faq/faq-protect.html)
states that facts are not protected, while their expression can be. That does not
settle source-access terms: [Disney's published U.S. terms](https://disneytermsofuse.com/english/)
include ESPN-branded products and restrict automated extraction. These primary
sources were checked on November 16, 2026. Their applicability to this retained
API snapshot and the distribution basis for these independently generated
statistics still require an explicit recorded decision; no upstream license grant
or legal clearance is inferred from public accessibility.

The exact new cohort below is read from the review package's 55 `team.yaml`
entries. The pinned archive above, rather than any local season directory,
defines the proposed file selection.

| Selected team | Selected team | Selected team |
| --- | --- | --- |
| Alabama | Arizona State | Arizona |
| Arkansas | Auburn | Baylor |
| Boston College | California | Colorado |
| Duke | Florida | Georgia Tech |
| Georgia | Illinois | Indiana |
| Iowa State | Iowa | Kansas State |
| Kansas | Kentucky | LSU |
| Miami | Michigan State | Michigan |
| Minnesota | Mississippi State | Missouri |
| NC State | Nebraska | Northwestern |
| Notre Dame | Ohio State | Oklahoma State |
| Oklahoma | Ole Miss | Oregon State |
| Oregon | Penn State | Pittsburgh |
| Purdue | Rutgers | Stanford |
| Temple | Tennessee | Texas A&M |
| Texas Tech | Texas | UCLA |
| USC | Vanderbilt | Virginia Tech |
| Washington State | Washington | West Virginia |
| Wisconsin |  |  |
