# Bowl Bound

An independent, unofficial computer adaptation of the Bowl Bound college-football
board game. Call plays against a computer opponent or control both sides in the
local web game. Dice, chart results, clock, scoring and statistics are resolved
by the game engine. No account or Internet connection is needed for local play
after installation.

**Seventh alpha: 0.1.0-alpha.7.** [Download Alpha 7](https://github.com/rtulloh/bowl_bound/releases/tag/v0.1.0-alpha.7)
for Windows, Apple Silicon or Intel Mac. Play 116 generated 2007 college teams
plus the original fictional Cedar Valley and Harbor Tech samples. See the
[generation notes and testing limits](docs/generated-charts.md).

## Get started

- [Install and launch](docs/installation.md): standalone and source instructions.
- [How to play](docs/playing.md): setup, controls, difficulty, saving and limits.
- [Optional: import your own team charts](docs/importing-teams.md) (advanced).
- [Troubleshooting](docs/troubleshooting.md) and [report a bug](docs/reporting-bugs.md).
- [Release notes](RELEASE_NOTES.md) and [all player documentation](docs/README.md).

The web game supports full regulation games, season-appropriate overtime,
team statistics, save/resume, and Easy/Medium/Hard computer coaching.
**Medium is the default; difficulty changes decisions, never dice odds.**
A separate source-installed terminal game is available:

```sh
python -m bowl_bound --play -d medium --compact
```

Run that command from the installed source checkout; see the installation guide.
The web game is a local service, not Internet multiplayer. Keep its terminal
window open, save before stopping, and press Ctrl+C to shut down.

## License and support

Original code/documentation: [MIT](LICENSE). Original fictional sample charts:
[CC0-1.0](seasons/SAMPLE-LICENSE.md). Generated statistical charts:
[CC BY 4.0](seasons/GENERATED-LICENSE.md). See [third-party notices](docs/THIRD_PARTY_NOTICES.md).
The code license does not grant rights to third-party game text, charts or names,
and no publisher affiliation or endorsement is implied.

Bug reports: **bowlboundsupport@gmail.com**. Include a short description, the
game version, reproduction steps, and relevant logs if available. Review
attachments first; do not send private charts, source PDFs, credentials or
personal information. The reporting guide includes a ready-to-copy template.
