# Chart schema v1

The immutable Python models in bowl_bound.models define normalized chart facts.
They do not parse tokens, roll dice, or resolve football outcomes. Schema v1 has
no JSON codec yet; a future codec must be explicitly versioned and preserve all
fields below.

## Identity and provenance

A TeamChart has a non-empty team name and positive integer season. Every
NormalizedCell and each dedicated PatOutcome has immutable Provenance: exactly
64 hexadecimal SHA-256 characters, filename, one-based page, finite
positive-area PDF bounding box, original text, and measured RGB evidence. A
metadata provenance row may have no measured fill, represented explicitly as
three empty RGB fields in the bundle; chart cells and PAT outcomes always require
RGB. RGB belongs to provenance, not semantics; engines must not inspect PDF colors.

## Semantic facts

ResultKind represents yards, no change, incomplete, touchdown, DS/X/T1/T2/T3,
B/QR/QT, SOP, BLP, penalties, F/INT/BK, punt/field-goal/kickoff references,
and NG (no-good field goal). QT means quarterback trapped, SOP means sprint-out
pass, and BLP means bootleg pass.

A numeric cell has signed integer yards. A variable cell has its matching
VariableReference and a signed non-zero multiplier. F/INT/BK require either
signed yards as their location or a variable location. Out-of-bounds is allowed
on numeric, variable, blank no-change, or punt-column FG/KO redirect outcomes
(the legend's FG* and KO*), never F/INT/BK, TD, INC, or penalties. Locations must
not contain both fixed and variable values.

Penalties require typed PenaltyData with offense/defense and one of fixed, S, R,
PI, 5Y, or 5X. Fixed penalties carry positive integer yards. PI is always defensive
(offensive pass interference is not a chart token) and carries exactly one location:
signed fixed yards or a variable reference with a signed non-zero multiplier. S, R,
5Y, and 5X carry no separate distance.

Placement is enforced: NG only in the field-goal column, FG/KO redirects only in the
punt column, and SOP/BLP only in offensive play 5. Other kind-versus-column legality
is checked by normalization and import validation in later milestones.

Schema conventions for later normalization (not parsing done here): the legend's T0
is the same value as X and maps to the X variable, keeping the original token in
provenance. A printed fixed 5-yard penalty (DEF 5/OFF 5) is `FIXED` with yards=5, while
the distinct 5Y and 5X tokens keep their own codes. Asterisk and dagger are equivalent
in the legend and both set out_of_bounds. Priority decoration is retained separately.
Source hashes must be lowercase hexadecimal.

Play is limited to callable columns 1 through 9. B, QR, and QT are separate,
non-callable SupplementalColumn records.

## Complete records

Rolls for offense, supplemental, special teams, and PAT are 10 through 39;
defensive rolls are 1 through 5. TeamChart accepts tuple records and validates
all enum/roll keys, rejecting omissions and duplicates:

- offense: 9 plays x 30 rolls = 270;
- supplemental: 3 columns x 30 rolls = 90;
- defense: 6 defenses x 9 plays x 5 rolls = 270; and
- special teams: 6 columns x 30 rolls = 180.

These total 810 chart cells, plus 30 separate PatOutcome records. Recovery is
a non-empty ascending built-in range wholly within 10 through 39.
