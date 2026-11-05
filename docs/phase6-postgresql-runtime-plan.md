# Phase 6. PostgreSQL Runtime Plan

2026-11-04 기술 Gate 통과.

`--database --runtime`에서만 EXPLAIN ANALYZE/BUFFERS를 실행한다.
`--runtime` 단독 사용은 exit 2로 거부한다. CLI와 HTML에 실제 실행 사실을 표시하며
Actual Rows/Loops/Time/Buffers와 전체 실행 시간을 Estimated와 구분한다.
동일한 SELECT/함수 Allowlist, Read-only, 최소 권한, Timeout을 적용한다.

실제 검증:

- 전체 회귀 및 실제 DB 테스트 **81 passed**, exit 0.
- SELECT/JOIN/Aggregate Actual Rows/Loops/Time/Shared Hit Blocks 확인.
- 기본 Estimated Plan에는 Actual Rows가 없음을 확인했다.
- 재귀 SELECT의 실제 5초 Statement Timeout과 취소 후 데이터 집계값 보존 확인.
- `--runtime` 단독 거부 및 Actual 필드 없는 Runtime Plan 거부 확인.
- `uv lock --check`, Ruff check/format: 각각 exit 0.
- 실제 CLI로 `artifacts/postgres-runtime.html` 생성: exit 0.
- 브라우저에서 RUNTIME, Actual Rows/Loops/Buffers, 실행 알림을 확인했다.

수치 자체는 실행 환경에 따라 달라지므로 Golden Value로 고정하지 않았다.
Query 결과 행은 수집하지 않는다. Runtime은 승인된 격리 DB에서만 검증했으며,
Production 자동 실행/튜닝은 제공하지 않는다. uv/Git 환경 제약은 이전과 같다.
