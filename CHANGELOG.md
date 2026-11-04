# Changelog

## 0.18.49 (2026-11-05)

### Fixed
- "Clean Add-on Data" no longer crashes with `StructRNA of type Image has been removed`
- Right-click "Remove Tie" now responds to `X` instead of `T`

### Changed
- Keyboard: `Del` mirrors `X` (removes the selected ties only, helpers kept); `Backspace` is unbound to keep the node editor's native reset behavior
- Right-click menu reworked:
  - `(G) Move` added at the top
  - shortcut-first labels (`(R) Rotate`, `(S) Spacing`, `(N) Name`, `(C) Color`, `(X) Remove Tie`)
  - built-in icons added to every entry
  - faded shortcut hints hidden
  - left padding added after icons
