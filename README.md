# TieRZ
TieRZ is a Blender add-on that organizes node links with movable cable ties (reroute bundles). It works on unmodified Blender and keeps all native node connections intact.

[![Blender Compatibility](https://img.shields.io/badge/Blender-4.0%20~%205.4%20Alpha-ea7600?style=flat-square&logo=blender&logoColor=white)](https://www.blender.org/)
[![License: GPL-3.0](https://img.shields.io/badge/License-GPL--3.0-blue.svg?style=flat-square)](LICENSE)
[![Latest Release](https://img.shields.io/badge/Release-Latest-f5792a?style=flat-square)](https://github.com/narznarz/TieRZ/releases/latest)

[![English](https://img.shields.io/badge/Language-English-238636?style=for-the-badge&logo=github)](README.md)
[![한국어](https://img.shields.io/badge/Language-%ED%95%9C%EA%B5%AD%EC%96%B4-21262d?style=for-the-badge&logo=readme)](README.ko.md)

---

## 📸 Before & After

| Before (Tangled Spaghetti) | After (TieRZ Cable Ties) |
| :---: | :---: |
| <img src="assets/before-spaghetti.png" width="460" alt="Before Spaghetti"/> | <img src="assets/after-tierz.png" width="460" alt="After TieRZ"/> |

---

## 🎨 Tie Styles & Unique Designs
TieRZ allows customizing tie designs via the N-panel. In addition to clean standard ties, unique expressive styles are supported:
- **Classic Cable Tie**: Clean, minimal collar tags for standard workflow organization.
- **MACHOCAT**: Cute cat face collar design clamped over bundled wires.
- **MUSIC NOTE**: Musical note collar design adding rhythm to complex shader trees.

| MACHOCAT | MUSIC NOTE |
| :---: | :---: |
| <img src="assets/tie-style-cat.png" width="280" alt="MACHOCAT Tie"/> | <img src="assets/tie-style-music.png" width="280" alt="MUSIC NOTE Tie"/> |

---

## Features
- Draw a stroke across wires to bundle them into a movable tie.
- Rotate, space, name, color, and remove ties from the right-click menu.
- Customizable tie appearance and styles (Classic, MACHOCAT, MUSIC NOTE via N-panel).
- Ties are designed to feel like native Blender controls, so they are easy to handle.
- Clean uninstall: removes control data so nothing is left behind.
- Multilingual interface: English, Korean, Simplified Chinese, and Japanese (more languages can be added via `i18n/*.json`).

---

## Installation
1. Download the latest release `.zip` from [Releases](https://github.com/narznarz/TieRZ/releases). *(Do not extract)*
2. In Blender: `Edit > Preferences > Add-ons` (or `Get Extensions` in 4.2+ / 5.x) `> Install...` and select the zip.
3. Enable **TieRZ** in the add-on list.
4. A `TieRZ` tab appears in the Node Editor sidebar (N panel).

---

## Usage
- **Create a tie**: hold the gesture key (default `Z`) and drag across wires.
- **Right-click menu** (on a selected tie): Rotate (R) / Spacing (S) / Name (N) / Color (C) / Remove (X).
- **N panel**: edit selected tie name, color, spacing, style (`MACHOCAT`, `MUSIC NOTE`, etc.), and appearance.
- **Match sizes**: `Alt+S` to unify selected tie sizes.
- **Move selected**: `G` to move selected nodes and ties together.
- **Remove**: `X` (ties only) / `Del` or `Backspace` (ties and nodes).

<p align="center">
  <img src="assets/tierz-context-menu.png" width="260" alt="TieRZ Context Menu"/>
</p>

### Keys
| Key | Action |
|---|---|
| `Z` (hold) + drag | Create a tie across wires |
| `R` | Rotate selected ties (smooth free rotation) |
| `S` | Adjust spacing |
| `N` | Name the selected tie |
| `C` | Change color |
| `X` | Remove selected ties |
| `Alt+S` | Match sizes |
| `G` | Move selected nodes and ties |
| `Del` / `Backspace` | Remove selected ties and nodes |

---

## Warnings
- **Uninstall cleanup**: before uninstalling, run `Clean Add-on Data` in the N panel to restore native links and remove metadata. Otherwise managed reroute nodes may remain.
- **Collapsed nodes**: drawing near collapsed (hidden) nodes may be ignored to avoid incorrect selections.
- **Read-only trees**: cleanup stops on read-only node trees.
- **Keymap conflicts**: the add-on registers shortcuts in the Node Editor keymap. If shortcuts do not work, check `Preferences > Keymap` for stale `tie.rz_*` entries.

---

## Background
The idea started as a prototype in a game engine, then moved to ComfyUI, and finally landed in Blender as NODE ZIP TIE. This add-on builds on that lineage. It is a free add-on; no grand claims intended.

---

## Credits & Special Thanks
The basic behavior was derived from NODE ZIP TIE, then almost entirely rewritten.

Deeply inspired by and grateful to wonderful contributors in the Blender ecosystem — including **aras-p** (ex-Unity), **ando** (ZOZO Inc.), and the **ACGGit** team — I am glad to contribute back to the 3D community with this add-on.

TieRZ is free and open-source, and **will always remain 100% free with no monetization or paywalls intended**.

---

## Copyright

<p align="left">
  <img src="assets/7_macho_shy.png" width="96" alt="MACHOCAT Character" style="vertical-align: middle; margin-right: 12px;"/>
  <span>MACHOCAT character copyright &copy; <b>NARZ & 박냥냥</b>.</span>
</p>

---

## License
SPDX:GPL-3.0-or-later (GNU General Public License v3.0)
