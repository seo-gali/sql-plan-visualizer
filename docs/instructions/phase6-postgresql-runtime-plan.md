# Phase 6. PostgreSQL Runtime Plan 작업 지침

적용 시점: Phase 6 구현 단계. 선행 조건: Phase 5 기술 Gate 통과.
Gate 근거: [완료 기록](../phase6-postgresql-runtime-plan.md), 2026-11-04 기준.

## 구현 범위

실제 Query 실행 조건: `--database --runtime`의 명시적 지정.
수집 방식: PostgreSQL EXPLAIN ANALYZE·BUFFERS JSON.
`--runtime` 단독 사용 거부.

표시 정보: Actual Rows·Loops·Time·Buffers와 Estimated의 구분.
실행 알림: CLI·HTML에 실제 실행 사실 표시.
유지 경계: Allowlist·Read-only·최소 권한·Timeout·Credential 비노출.
Query 결과 행의 Report 포함 금지.

## 기술 Gate

- [x] Phase 0~5 회귀 통과
- [x] 기본 Estimated 경로의 입력 Query 미실행 확인
- [x] 격리 PostgreSQL의 Actual·Loops·Buffers 확인
- [x] Timeout·금지 Statement 차단·데이터 보존 확인
- [x] 변동 수치 대신 구조·의미 검증과 한계 기록
- [x] Lock·pytest·Ruff check/format 통과

결과 기록: `docs/phase6-postgresql-runtime-plan.md`와 README.
브랜치: `feat/phase6-postgresql-runtime-plan`.
Push·PR: 사용자 사전 승인 범위.
