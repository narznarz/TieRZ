# TieRZ

**TieRZ** is a Blender add-on that organizes node links with movable cable ties (reroute bundles). It works on unmodified Blender and keeps all native node connections intact.

**TieRZ**는 블렌더 노드 링크를 이동 가능한 케이블 타이(리라우트 번들)로 정리해 주는 애드온입니다. 블렌더를 수정하지 않고 동작하며, 모든 네이티브 노드 연결을 그대로 유지합니다.

---

## Features / 기능

- Draw a stroke across wires to bundle them into a movable tie.
- Rotate, space, name, color, and remove ties from the right-click menu.
- Ties stay editable: move nodes and the ties follow.
- Native reroute helpers are restored to ordinary links on uninstall.

- 와이어 위로 드래그해 타이로 묶습니다.
- 우클릭 메뉴에서 회전/간격/이름/색상/삭제를 수행합니다.
- 노드를 이동하면 타이도 따라갑니다.
- 제거 시 네이티브 리라우트를 일반 링크로 복원합니다.

---

## Installation / 설치

1. Download `TieRZ-x.x.x.zip` from [Releases](https://github.com/narznarz/TieRZ/releases).
2. In Blender: `Edit > Preferences > Add-ons > Install...` and select the zip.
3. Enable **TieRZ** in the add-on list.
4. A `TiesRZ` tab appears in the Node Editor sidebar (N panel).

1. [Releases](https://github.com/narznarz/TieRZ/releases)에서 `TieRZ-x.x.x.zip`을 다운로드합니다.
2. 블렌더에서 `Edit > Preferences > Add-ons > Install...`로 zip을 선택합니다.
3. 애드온 목록에서 **TieRZ**를 활성화합니다.
4. 노드 에디터 사이드바(N 패널)에 `TiesRZ` 탭이 나타납니다.

---

## Usage / 사용법

- **Create a tie**: hold the gesture key (default `Z`) and drag across wires.
- **Right-click menu** (on a selected tie): Rotate (R) / Spacing (S) / Name (N) / Color (C) / Remove (X).
- **N panel**: edit selected tie name, color, spacing, design, and appearance.
- **Match sizes**: `Alt+S` to unify selected tie sizes.

- **타이 생성**: 제스처 키(기본 `Z`)를 누른 채 와이어 위로 드래그합니다.
- **우클릭 메뉴** (타이 선택 시): 회전(R) / 간격(S) / 이름(N) / 색상(C) / 삭제(X).
- **N 패널**: 선택한 타이의 이름, 색상, 간격, 디자인, 표시 옵션을 편집합니다.
- **크기 통일**: `Alt+S`로 선택한 타이 크기를 통일합니다.

---

## Warnings / 주의사항

- **Uninstall cleanup**: before uninstalling, run `Clean Add-on Data` in the N panel to restore native links and remove metadata. Otherwise managed reroute nodes may remain.
- **Collapsed nodes**: drawing near collapsed (hidden) nodes may be ignored to avoid incorrect selections.
- **Read-only trees**: cleanup stops on read-only node trees.
- **Keymap conflicts**: the add-on registers shortcuts in the Node Editor keymap. If shortcuts do not work, check `Preferences > Keymap` for stale `tie.rz_*` entries.
- **Version**: the panel shows the version read from `blender_manifest.toml`.

- **제거 전 정리**: 제거 전 N 패널의 `Clean Add-on Data`를 실행해 네이티브 링크를 복원하고 메타데이터를 삭제하세요. 그렇지 않으면 관리 중인 리라우트 노드가 남을 수 있습니다.
- **접힌 노드**: 접힌(숨겨진) 노드 근처에서 드래그하면 정확도 문제로 무시될 수 있습니다.
- **읽기 전용 트리**: 읽기 전용 노드 트리에서는 정리가 중단됩니다.
- **키맵 충돌**: 애드온이 노드 에디터 키맵에 단축키를 등록합니다. 단축키가 동작하지 않으면 `Preferences > Keymap`에서 `tie.rz_*` 잔재 항목을 삭제하세요.
- **버전**: N 패널의 버전은 `blender_manifest.toml`에서 읽어 표시됩니다.

---

## Copyright / 저작권

MACHOCAT character copyright (c) NARZ & 박냥냥.

## License / 라이선스

SPDX:GPL-3.0-or-later