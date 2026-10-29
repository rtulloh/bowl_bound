# Troubleshooting

[Player guide](README.md) · [Report a bug](reporting-bugs.md)

- **Blocked or unknown publisher:** verify the release/checksum, then follow the
  platform-specific [download instructions](installation.md). Do not disable
  antivirus or organization policy. `xattr` applies only to macOS.
- **Window closes immediately on Windows:** open PowerShell in the extracted
  folder and run `.\BowlBound.exe --no-browser` so you can read the message.
- **Browser does not open:** enter the printed local address manually. Keep the
  server terminal open. Use `--no-browser` if automatic opening is unwanted.
- **Port in use:** stop another copy, or run `start.bat --port 8001` on Windows
  (`./start.sh --port 8001` on macOS/Linux). Use the new displayed URL.
- **Missing resources/assets:** re-extract the entire standalone archive; keep
  supporting folders with the executable. Source users must build the frontend.
- **Python/module not found:** standalone players should use the actual platform
  app, not a source ZIP. Source users should install dependencies with the same
  environment interpreter used by the starter.
- **No teams / imported team missing:** PDFs alone are not playable team files.
  Complete the [import steps](importing-teams.md), preserve the season/team
  folders, and start with `--seasons` pointing to the library root, not a team
  subfolder. That option replaces the bundled library; it does not merge it.
- **Unsupported season or PDF:** game profiles cover 1940–2023; the PDF extractor
  accepts only the documented digitally generated layout. Do not replace missing
  cells with zeros or force incompatible charts into the game.
- **A choice is disabled:** read its explanation. Some advanced procedures are
  intentionally unavailable in this alpha. Follow the currently offered legal
  controls rather than instructions for another game or phase.
- **Computer stopped:** use Retry computer if offered. Save first if possible,
  note the situation, and report a repeatable failure. Repeated refreshes lose
  unsaved progress and do not repair a game.
- **Save rejected:** use the original unedited file with the same unchanged
  team charts and compatible game version. Do not edit hashes or JSON fields
  to bypass validation. Keep the file and report its error without sending
  private charts. An invalid load leaves the current game unchanged.
- **Update changed behavior:** keep the previous download and backups of saves;
  try the same fictional-team situation and include both versions in a report.

The game does not create persistent diagnostic log files automatically. You can
copy terminal startup/error output, a relevant Play log excerpt, or a screenshot
of the problem. Detailed chart traces can reveal chart values: review everything
and prefer fictional-team reproductions. Never post your source PDFs or charts.
