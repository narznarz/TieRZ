# TieRZ

TieRZ is a Blender add-on that organizes node links with movable cable ties (reroute bundles). It works on unmodified Blender and keeps all native node connections intact.

[English](README.md) | [한국어](README.ko.md)

## Features

- Draw a stroke across wires to bundle them into a movable tie.
- Rotate, space, name, color, and remove ties from the right-click menu.
- Ties are designed to feel like native Blender controls, so they are easy to handle.
- Clean uninstall: removes control data so nothing is left behind.
- Multilingual interface: English and Korean (more languages can be added via `i18n/*.json`).

## Installation

1. Download `TieRZ-x.x.x.zip` from [Releases](https://github.com/narznarz/TieRZ/releases).
2. In Blender: `Edit > Preferences > Add-ons > Install...` and select the zip.
3. Enable **TieRZ** in the add-on list.
4. A `TiesRZ` tab appears in the Node Editor sidebar (N panel).

## Usage

- **Create a tie**: hold the gesture key (default `Z`) and drag across wires.
- **Right-click menu** (on a selected tie): Rotate (R) / Spacing (S) / Name (N) / Color (C) / Remove (X).
- **N panel**: edit selected tie name, color, spacing, design, and appearance.
- **Match sizes**: `Alt+S` to unify selected tie sizes.

## Warnings

- **Uninstall cleanup**: before uninstalling, run `Clean Add-on Data` in the N panel to restore native links and remove metadata. Otherwise managed reroute nodes may remain.
- **Collapsed nodes**: drawing near collapsed (hidden) nodes may be ignored to avoid incorrect selections.
- **Read-only trees**: cleanup stops on read-only node trees.
- **Keymap conflicts**: the add-on registers shortcuts in the Node Editor keymap. If shortcuts do not work, check `Preferences > Keymap` for stale `tie.rz_*` entries.

## Credits

The basic behavior was derived from NODE ZIP TIE, then almost entirely rewritten.

## Copyright

MACHOCAT character copyright (c) NARZ & 박냥냥.

## License

SPDX:GPL-3.0-or-later