# Changelog

## 0.18.47 (2026-11-05)

### Changed
- **`(G) Move` moved to the top of the right-click menu.**
- **Removed the faded `G` shortcut hint shown next to the `(G) Move` button**: the
  right-click menu now routes the move action through a dedicated, keymap-free
  wrapper operator, so Blender no longer echoes the move key beside the entry.

## 0.18.46 (2026-11-05)

### Changed
- **Right-click / N-panel menu labels now lead with their shortcut key**: all entries use
  the `(key) Label` form — `(R) Rotate`, `(S) Spacing`, `(N) Name`, `(C) Color`,
  `(X) Remove Tie` — so the menu accelerator always matches the documented shortcut.

### Added
- **(G) Move** entry in the right-click menu: moves the selected ties (and any selected
  nodes) together, the same action as pressing `G`.

## 0.18.45 (2026-11-05)

### Fixed
- **Right-click menu "Remove Tie" responded to `T` instead of `X`**: Blender picks a
  menu item's accelerator letter as the first unused letter in its label, and in
  `Remove Tie (X)` the `X` is consumed by earlier words, leaving `T`. The label now
  leads with `X` (`X  Remove Tie`), so the menu honours the documented shortcut.
  - Relabeled in all four languages (English, Korean, Chinese, Japanese).
  - Removed the now-unused `Remove Tie (X)` / `Remove Ties (X)` translation entries.

## 0.18.44 (2026-11-05)

### Fixed
- **"Clean Add-on Data" crashed with `ReferenceError: StructRNA of type Image has been
  removed`**: the MachoCAT GPU texture cache could hold an Image datablock that a file
  reload, add-on update, or earlier cleanup had already removed. Reading the cache then
  raised a ReferenceError and aborted both the scan and the cleanup run.
  - Dead cache entries are now detected and dropped before their pointer is read
    (`rendering__live_macho_image_pointers`).
  - Image iteration in the scan and cleanup paths guards `image.get`, `as_pointer`,
    `filepath`, `users`, `pack`, and property removal against removed datablocks.

## 0.18.43 (2026-11-04)

### Changed
- **`Del` now mirrors `X`**: it removes only the selected ties and keeps their reroute
  helpers, instead of deleting every selected node in the tree.
- **`Backspace` is no longer bound**: it used to delete ties together with the selected
  nodes, which collided with the node editor's native "reset to default" shortcut and
  caused accidental edits. It now keeps its default Blender behavior.

## 0.18.42 (2026-11-04)

### Added
- Simplified Chinese (`zh_CN.json`) and Japanese (`ja_JP.json`) translations covering all
  interface strings, including placeholders and cleanup dialog text.
- Language names for the new locales in the language selector (简体中文, 日本語).

## 0.18.41 (2026-11-04)

### Fixed
- **Garbled labels in the Color / Tie Design dropdowns**: Blender's RNA layer mangles
  non-ASCII text used directly as a Python `EnumProperty` item name, so the 0.18.40
  pre-translated labels rendered as unreadable characters. Both dropdowns are now drawn
  as menus whose entries pass `i18n_tr()` output as ordinary UI text (the path already
  used by the rest of the panel), which renders Korean correctly.
- Renamed the Korean labels: 회색, 와이어의 색상, 마초냥.

## 0.18.40 (2026-11-04)

### Fixed
- **Color and Tie Design dropdowns ignored the language setting**: `color_mode` and
  `tie_style` used static `EnumProperty` item lists, which Blender registers once at
  import time and never re-translates. They now build their items through dynamic
  callbacks that call `i18n_tr()`, matching the forced-translation approach used by the
  rest of the panel, so the labels follow the selected interface language immediately.

## 0.18.26 (2026-11-02)

### Fixed
- **Panel validation error**: `bl_icon = ''` is not a valid icon enum value, causing
  "validating class: enum '' not found" on registration. Use `'NONE'` when the custom
  icon is active (and `'SNAP_MIDPOINT'` as the fallback).

## 0.18.24 (2026-11-02)

### Fixed
- **Custom tab icon not showing intermittently**: `bpy.utils.previews` collection could be
  invalidated on `.blend` file load, leaving the N-panel tab with a stale/blank icon.
  - Icon is now re-applied on every `load_post` (refresh with a fresh collection).
  - Load result is validated (`icon_id != 0`); on failure the addon retries once with a
    fresh collection, then falls back to the built-in `SNAP_MIDPOINT` icon so the tab
    always has an icon instead of going blank.
  - Built-in fallback is used automatically in headless/background mode where preview
    icon generation is unavailable.

## 0.18.23 (2026-11-02)

### Fixed
- **Blender 5.4 alpha compatibility**: `TRZ_OT_color` failed to register because
  `Operator` no longer accepts `PointerProperty(type=bpy.types.NodeTree)` ("this type
  doesn't support data-block properties"). The node tree is now stored by name
  (`StringProperty`) and resolved from `bpy.data.node_groups` at execute time.
- **Blender 5.4 alpha compatibility**: modal link hit-testing crashed with
  `AttributeError: 'ThemeNodeEditor' object has no attribute 'noodle_curving'` on
  builds/themes where that property was removed. Now falls back to the default value (4).
- **Color picker out-of-range values**: tie colors are stored/rendered as sRGB but
  `FloatVectorProperty(subtype='COLOR')` expects scene-linear. Conversion is now
  applied at the picker boundary only, so stored/rendered colors are unchanged while
  the picker no longer shows values above 1.0 (e.g. Value 1.079, Saturation 1.784).
  Out-of-range stored colors are clamped to 0..1 instead of dropping the tie.
- **Random color palette**: 16-colour DawnBringer 16 (DB16) palette, no repeats
  within a single node tree until all 16 are used.

### Compatibility
- Verified working on **Blender 5.2**, **5.3 beta**, and **5.4 alpha**.
- Minimum supported Blender version: 5.2.0.

### Notes
- Only the latest working release (0.18.23) is published. Earlier intermediate
  releases have been withdrawn.
