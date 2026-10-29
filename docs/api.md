# Derived API report commentary

Every report and `view.log` item includes additive `commentary`: engine-generated
announcer-style text using the game's optional local roster snapshot, or generic
roles if names are missing. CLI and web display the same natural play-by-play.
Kicks preserve their complete engine distance/result details after the call.
Automatic kneels/spikes, pending, unsupported, penalty and ambiguous-recovery
reports retain factual wording; clients must not interpret prose to determine
football results.

`description` and all structured report fields are unchanged. Null reports stay
null. Create/get/action/coached/load responses use the same serialization. Names
are illustrative labels, not player statistics. Phrase selection is stable for
the report number and consumes no randomness. Saves do not contain this field
or rosters. Load may refresh names from current installed rosters. The save
schema, semantic digest and engine profile are unchanged.
