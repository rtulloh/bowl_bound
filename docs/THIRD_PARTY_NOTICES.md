# Third-party notices

Original Bowl Bound code and player documentation are provided under the
[MIT License](../LICENSE), Copyright (c) 2026 rtulloh. This project is an
independent, unofficial adaptation and does not claim affiliation with or
endorsement by any board-game publisher, school or league.

## Paydirt adaptations

Portions of the field/scoreboard/play-selection/coin presentation and frontend
configuration were adapted from Paydirt, Copyright (c) 2026 rtulloh, MIT-licensed.
The full MIT copyright/permission/warranty notice is included in LICENSE and
applies to these adapted portions. Paydirt is not a runtime requirement.

## Fictional samples and third-party charts

The original Cedar Valley and Harbor Tech chart/provenance bundles are
[CC0-1.0](../seasons/SAMPLE-LICENSE.md). No historical chart, PDF, roster or
board-game rulebook is licensed by this code notice. A user’s ownership of a
chart does not automatically grant redistribution rights.

## Generated statistical charts

The 116 generated 2007 teams are statistical transformations of ESPN-derived
individual-play data supplied through SportsDataverse/cfbfastR. SportsDataverse
labels its data-release store CC BY 4.0. The generated content retains credit,
license and modification notices under [CC BY 4.0](../seasons/GENERATED-LICENSE.md).
See [generation provenance and limits](generated-charts.md). This narrow scope
does not assert rights to source narratives, private benchmark charts, historical
rosters or logos, or endorsement by the data providers or schools.

## Runtime dependencies

The software uses Python and libraries including PyYAML, FastAPI, Starlette,
Pydantic, Uvicorn and their dependencies. The web interface uses React and
React DOM. These retain their respective licenses. Native standalone builds
must include the applicable dependency license texts and Python notices for
the exact versions bundled; the summary here does not replace those notices.
Native build tooling collects Python, installed package (including analyzed
setuptools/vendor and packaging code) and React license texts under
`THIRD_PARTY/`, with exact package versions in `DEPENDENCIES.json`.
`THIRD_PARTY/NATIVE/` additionally carries hash-pinned upstream notices for
bundled native libraries and a conservative Rust dependency notice collection.
`NATIVE-LIBRARIES.json` records each native binary path/hash, its component
family, version/provenance references and notice hashes. The same native
notices are retained under `_internal/THIRD_PARTY/`; Windows installers copy
both sets unchanged and also include the NSIS compiler notice.

The inventory distinguishes bundled libraries from macOS system libraries and
records known audit limitations. Notices do not themselves grant distribution
rights or prove which static dependencies were compiled into a wheel. Complete
transitive/native licensing and Windows runtime redistribution review, corrected
three-platform builds and fresh-machine acceptance remain publication gates.
