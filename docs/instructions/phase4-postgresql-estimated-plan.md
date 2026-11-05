# Phase 4. PostgreSQL Estimated Plan 작업 지침

적용 시점: Phase 4 구현 단계. 선행 조건: Phase 3 기술 Gate 통과.
Gate 근거: [완료 기록](../phase4-postgresql-estimated-plan.md), 2026-11-04 기준.
현재 접속 변수·사용법: [README](../../README.md).

## 구현 범위

의존성: 사용자 승인 범위의 Psycopg 3 도입.
검증 환경: PostgreSQL 18.x·Docker Compose의 격리 테스트 DB.
Phase 4 접속 변수: `SQLPVI_DATABASE_URL`.
접속 조건: `--database` 지정. 정적 분석의 기본 수행 유지.

계획 수집: PostgreSQL `EXPLAIN (FORMAT JSON)` → Vendor Adapter → Report.
표시 항목: DB 출처·실제 계획의 비용·추정 Rows·Vendor 트리.

| 안전 경계 | 기준 |
| --- | --- |
| 입력 | SELECT·함수 Allowlist |
| 거부 대상 | 중첩 DML·SELECT INTO·잠금·복수 Statement |
| 계정·트랜잭션 | 최소 권한·Read-only |
| 자원 | Statement·Lock·Connection Timeout |
| 실패 | Rollback·Close·Credential 비노출 |

임의 SQL 함수의 안전 간주 금지.
Runtime·ANALYZE 도입 제외.
Fixture 준비 조건: 승인된 격리 테스트 DB.

## 기술 Gate

- [x] Phase 0~3 회귀·Static 무환경변수 실행 통과
- [x] 실제 PostgreSQL 18.x Estimated JSON Plan 조회
- [x] HTML의 계획 구조·Relation·Rows·출처 확인
- [x] 쓰기·잠금·복수 Statement 차단과 Read-only·Timeout 확인
- [x] 접속·DB 오류의 Credential 비노출 확인
- [x] Lock·pytest·Ruff·DB 통합 테스트 통과

실제 DB 미확보 시 후속 Phase 착수 금지와 원인 기록.
결과 기록: `docs/phase4-postgresql-estimated-plan.md`와 README.
브랜치: `feat/phase4-postgresql-estimated-plan`.
Push·PR: 사용자 사전 승인 범위.
