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

## Runtime dependencies

The software uses Python and libraries including PyYAML, FastAPI, Starlette,
Pydantic, Uvicorn and their dependencies. The web interface uses React and
React DOM. These retain their respective licenses. Native standalone builds
must include the applicable dependency license texts and Python notices for
the exact versions bundled; the summary here does not replace those notices.
Native build tooling collects Python, installed package and React license texts
under `THIRD_PARTY/`, with exact versions in `DEPENDENCIES.json`. Windows
installers also include the NSIS compiler notice. The bundled native-library
license review and three-platform build verification remain release gates;
these generated notices alone do not establish a completed license audit or
published standalone distribution.
