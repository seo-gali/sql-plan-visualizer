# Phase 2. HTML Visualization

2026-11-04 기술 Gate 통과. Jinja2 3.1.6과 MarkupSafe 3.0.4를 현재 Phase에
추가하고 uv.lock에 고정했다.

## 구현

Report Model만 받는 HTML Renderer, 패키지 내부 Jinja 템플릿과 CSS/JS,
Overview/Source/References/AST/SQL Flow를 추가했다. Source와 분석 요소의
Hover/Focus 연결, SVG Flow 연결선, 키보드 조작, 작은 화면 레이아웃을 제공한다.
CLI 기본 출력은 `.sqlpvi.html`이고 `--format json`으로 JSON 출력을 유지한다.
출력 경로와 입력의 symlink/hardlink 동등성을 검사해 입력 덮어쓰기를 방지한다.

## 실제 검증

- `uv --cache-dir .uv-cache lock --check`: exit 0.
- `uv --cache-dir .uv-cache run --no-sync pytest`: **47 passed**, exit 0.
- Ruff check: All checks passed. Ruff format check: 29 files already formatted. 각각 exit 0.
- CLI로 SELECT/JOIN/Aggregate/CTE/Subquery/악성 문자열 Fixture 6개의 HTML을 생성했다.
- 브라우저에서 Overview/SQL Source/References/AST/SQL Flow, Focus 강조 2개,
  Hover 강조 5개, SVG edge 4개, 깨진 Anchor 0개, 외부 Resource 0개를 확인했다.
- 390×844 화면에서 문서 가로 넘침이 없고 한 열 배치를 확인했다.
- 실제 Tab 키로 Skip link에 도달하고 focus-visible이 적용되는 것을 확인했다.
- 악성 문자열 리포트에서 Script 요소 1개(앱 코드만), 주입된 전역값 false,
  원문 문자열 보존, Console Errors/Warnings 0개를 확인했다.
- 별도 headless Chrome의 file URL 직접 실행: exit 0, SVG edge 4개.
- `python -m pip wheel --no-deps --wheel-dir artifacts/wheels .`: exit 0.
  실제 Wheel ZIP에서 HTML 템플릿 및 CSS/JS 3개 자산 포함을 assert로 확인했다.

## 한계

uv 자동 sync의 Windows 접근 거부는 지속되어 표준 pip 설치와 `--no-sync`를 사용했다.
브라우저 증거와 생성 HTML은 `artifacts/`에 있다. 자동화된 전체 WCAG 감사나
모든 브라우저 호환성은 검증하지 않았다. DB Plan은 아직 범위에 포함하지 않았다.
Git 저장소/Remote가 없어 Commit/Push/PR은 미수행이다.

## 사용자 요청: 언어 선택 추가

같은 작업 세션에서 한국어/English 선택 UI를 추가했다. 화면 제목/설명/표 항목/
상태 설명을 번역하고 SQL 원문/식별자/분석 코드는 보존한다.
브라우저에서 ko→en→ko 전환, `lang` 갱신, SQL 보존, SVG edge 수 보존,
새로고침 후 ko 유지, Console Errors/Warnings 0개를 assert로 확인했다.
기존 `artifacts/unsafe-strings.html`을 포함한 리포트 6개를 재생성했다.
