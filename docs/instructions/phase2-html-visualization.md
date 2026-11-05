# Phase 2. HTML Visualization 작업 지침

적용 시점: Phase 2 구현 단계. 선행 조건: Phase 1 기술 Gate 통과.
화면 기준: `design.md`.
Gate 근거: [완료 기록](../phase2-html-visualization.md), 2026-11-04 기준.

## 구현 범위

의존성: 사용자 승인 범위의 Jinja2 도입.
Renderer 계약: Report 모델 입력, Parser 객체 직접 해석 금지.
CLI 기본 출력: Standalone HTML. 기존 JSON 경로: `--format json`.
출력 생략 시 위치: 입력 파일 옆의 `.sqlpvi.html`.

화면 영역: Overview·SQL Source·References·AST·SQL Flow.
상호작용: Source Hover·Focus 양방향 연결.
Source Metadata 없는 노드의 임의 범위 생성 금지.

## 기술 Gate

- [x] Phase 0~1 회귀와 JSON 호환 경로 확인
- [x] 실제 SELECT·JOIN·Aggregate·CTE·Subquery HTML 생성
- [x] 브라우저의 Standalone·SVG·Hover·Focus 확인
- [x] 키보드·좁은 화면·JS Console 확인
- [x] `<script>`·`</script>`·`<>&"'`·Unicode·파일명 Escape 확인
- [x] 외부 네트워크 의존 없음·입력 덮어쓰기 방지 확인
- [x] Lock·pytest·Ruff check/format 통과

제외 범위: DB·Graph Editor·Drag/Zoom·Animation.
결과 기록: `docs/phase2-html-visualization.md`와 README.
브랜치: `feat/phase2-html-visualization`.
Push·PR: 사용자 사전 승인 범위.
