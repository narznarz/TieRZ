# Changelog

## 0.18.55 (2026-11-20)

### 수정
- 직접 만든 그룹 노드 안에서도 타이의 기능 사용이 원활해졌습니다.
- 외부 라이브러리에서 링크한 읽기 전용 그룹노드는 관련 경고 메시지를 표시합니다.
  편집을 원할 때는 Make Local 등 블렌더 기본 사용법을 이용하세요.

### Fixed
- Tie operations now work smoothly inside locally authored group nodes.
- Library-linked read-only node groups show a warning message. To edit them, use Blender's standard Make Local workflow.

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
