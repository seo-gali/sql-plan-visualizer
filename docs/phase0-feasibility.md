# Phase 0. Feasibility

## 학습 목표

SQLGlot PostgreSQL Parsing, AST/Reference 추출, Identifier Source Mapping,
안전한 문자열 출력과 Standalone HTML/SVG의 구현 가능성을 실제로 확인한다.

## 실습

2026-11-04 재검증. Python 3.13.15, SQLGlot 30.18.0, pytest 9.1.1,
Ruff 0.16.8, uv 0.12.5. Python 버전 변경과 lock 갱신은 사용자가 승인했다.

- `uv lock --check`: exit 0.
- `uv run pytest`: **16 passed**, exit 0.
- `uv run ruff check .`: All checks passed, exit 0.
- `uv run ruff format --check .`: 19 files already formatted, exit 0.
- `uv run python tests/phase0_probe.py fixtures/sql/join.sql artifacts/phase0-probe.html`:
  exit 0, HTML 파일 생성.
- Playwright로 로컬 HTTP에서 Reference 8개, SVG line 8개, 유효한 좌표,
  Focus/Hover 시 연결 요소 2개 강조, 외부 Resource 0개를 확인했다.
- 별도 프로필의 headless Chrome으로 HTML 파일을 직접 열었다.
  Chrome exit 0, 실행 후 DOM에서 SVG line 8개를 확인했다.

HTML은 Identifier의 SQLGlot start/end를 사용하며 임의 Offset을 추정하지 않는다.
원문의 줄바꿈, Unicode, 악성 script 문자열과 특수문자 보존 및 Escape를 테스트했다.

## 확인 결과

- [x] PostgreSQL Dialect SELECT/JOIN/Aggregate Parsing
- [x] AST Traversal
- [x] Table / Column Reference 추출
- [x] Table / Column Alias
- [x] Join Condition / Aggregate Function
- [x] Parser Error
- [x] Source Mapping 범위 확인 및 Source↔Reference 연결
- [x] 최소 Standalone HTML 생성과 파일 직접 열기
- [x] SQL 문자열 안전 출력
- [x] 실제 SVG 연결선 표시
- [x] 핵심 방식의 기술적 장애 없음

**기술 Gate: 통과.** 기존 보고서의 SVG 미검증/완료 표기를 실제 결과로 정정했다.
기존 디렉터리에 `.git`과 Remote가 없어 Branch/Commit/Push/PR은 수행하지 않았다.
Repository 기준 완료와 사용자의 PR Merge는 별도다.

확인된 한계:

1. Parsing 성공은 실제 PostgreSQL 실행 가능성을 보증하지 않는다. 키워드 오타가
   다른 Expression으로 해석될 수 있다.
2. Fixture의 Table/Column 상위 노드에는 전체 Source Range가 없고 Identifier 리프에
   위치가 있다. 확인된 Identifier 범위만 연결한다.
3. Python 3.13.14 배포본은 SQL 파일 읽기에 PermissionError가 발생했다. 사용자 승인으로
   기존 3.13.15를 사용했다. uv의 pytest entry_points.txt 복사 오류는
   `uv export --frozen --no-hashes --no-emit-project`로 내보낸 동일 버전을 표준 pip로
   설치해 복구했다. 보안 설정은 변경하지 않았다.
4. Playwright의 file 프로토콜 제한 때문에 HTTP로 상호작용을 검증하고,
   별도 headless Chrome으로 파일 직접 실행을 검증했다.
