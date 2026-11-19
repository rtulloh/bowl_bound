<!-- Maintainer draft: publish only with qualified new v1.1.1 assets. -->
# Bowl Bound 1.1.1

macOS downloads now use a disk image with a Finder app and Applications shortcut.
Choose your processor:

- [Apple Silicon DMG (M1 or later)](https://github.com/rtulloh/bowl_bound/releases/download/v1.1.1/BowlBound-1.1.1-macos-arm64.dmg) · [SHA256](https://github.com/rtulloh/bowl_bound/releases/download/v1.1.1/BowlBound-1.1.1-macos-arm64.dmg.sha256)
- [Intel Mac DMG (64-bit x86_64)](https://github.com/rtulloh/bowl_bound/releases/download/v1.1.1/BowlBound-1.1.1-macos-x86_64.dmg) · [SHA256](https://github.com/rtulloh/bowl_bound/releases/download/v1.1.1/BowlBound-1.1.1-macos-x86_64.dmg.sha256)
- [Windows installer](https://github.com/rtulloh/bowl_bound/releases/download/v1.1.1/BowlBoundSetup-1.1.1-windows-x64.exe) · [SHA256](https://github.com/rtulloh/bowl_bound/releases/download/v1.1.1/BowlBoundSetup-1.1.1-windows-x64.exe.sha256)

Verify the DMG checksum, mount it, and drag `Bowl Bound.app` into Applications.
Unmount the image, then remove quarantine from the copied app and launch it:

```sh
xattr -dr com.apple.quarantine "/Applications/Bowl Bound.app"
open "/Applications/Bowl Bound.app"
```

Use the actual copied-app path if you choose another folder. These builds are
unsigned and not notarized. Apply the command only to the verified app. It opens
Terminal and the local browser game; keep Terminal open while playing and use
Ctrl+C there to stop. Python and Node installation are unnecessary.

Portable ZIPs are secondary alternatives:
[Windows](https://github.com/rtulloh/bowl_bound/releases/download/v1.1.1/BowlBound-1.1.1-windows-x64.zip),
[Apple Silicon](https://github.com/rtulloh/bowl_bound/releases/download/v1.1.1/BowlBound-1.1.1-macos-arm64.zip),
[Intel Mac](https://github.com/rtulloh/bowl_bound/releases/download/v1.1.1/BowlBound-1.1.1-macos-x86_64.zip).

This patch retains the existing teams, charts, football rules and saves.
See [installation](https://github.com/rtulloh/bowl_bound/blob/v1.1.1/docs/installation.md)
and [release notes](https://github.com/rtulloh/bowl_bound/blob/v1.1.1/RELEASE_NOTES.md).
