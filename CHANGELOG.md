# Changelog

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
