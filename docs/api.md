# Derived API report commentary (21a)

Every report and `view.log` item includes additive `commentary`: engine-generated
text using the game's optional local roster snapshot, or existing generic text.
`description` and all structured report fields are unchanged. Null reports stay
null. Create/get/action/coached/load responses use the same serialization. Names
are illustrative labels, not player statistics. Saves do not contain this field
or rosters. Load may refresh names from current installed rosters.
