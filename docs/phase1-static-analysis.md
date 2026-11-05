# Phase 1. Static SQL Analysis

2026-11-04 기술 Gate 통과. Python 3.13.15와 기존 lock의 SQLGlot 30.18.0을 사용했다.

## 구현

`src/sqlpvi/`에 Parser Adapter, 독립 dataclass Report/AST/Reference/SqlFlow 모델,
Scope 분석, SQL Flow, JSON CLI를 추가했다. CTE/Derived Table/상관 Subquery,
Identifier 대소문자 및 Quoted Identifier, 중복 Alias, Schema 불일치를 확인했다.
Metadata 없는 단일 Table Column은 UNRESOLVED, 복수 Source는 AMBIGUOUS로 유지한다.
Qualified Column의 RESOLVED는 SQL Scope의 Source 연결을 뜻하며 DB Column 존재 확인이 아니다.
Source Range는 start 포함/end 제외이며 위치가 없는 노드는 연결하지 않는다.

## 실제 검증

- `uv --cache-dir .uv-cache lock --check`: exit 0.
- `uv --cache-dir .uv-cache run --no-sync pytest`: **42 passed**, exit 0.
- `uv --cache-dir .uv-cache run --no-sync ruff check .`: All checks passed, exit 0.
- `uv --cache-dir .uv-cache run --no-sync ruff format --check .`: 26 files already formatted, exit 0.
- `uv --cache-dir .uv-cache run --no-sync sqlpvi analyze fixtures/sql/join.sql --output artifacts/phase1-join.json`:
  exit 0. JSON을 다시 읽어 PARSED, Reference 8개,
  Scan/Scan/Join/Filter/Project를 확인했다.
- CLI subprocess 테스트로 stdout JSON, 파일 출력, 오류 종료 코드 및 입력 보존 확인.
- 기존 세 Fixture와 CTE/Subquery/상관 Subquery/DISTINCT/Sort/Limit/Offset,
  오류/빈 입력/다중 Statement, 이중 Join을 검증했다.

## 환경 제약

uv의 Windows 패키지 설치는 entry_points.txt 접근 거부가 재현된다.
표준 pip editable 설치 후 검증 명령에 `--no-sync`를 사용했다.
자동 sync 경로는 실패했으며 통과로 기록하지 않는다. 빌드 도구는 정식 setuptools
84.2.1로 고정했다. `.git`/Remote가 없어 Git/PR은 미수행이다.
DB Metadata, DB Plan, 완전한 Expression Source Range는 이번 Phase 범위가 아니다.
