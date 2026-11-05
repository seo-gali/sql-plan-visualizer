# Phase 8. MariaDB 작업 지침

적용 시점: Phase 8 구현 단계. 선행 조건: Phase 7 기술 Gate 통과.
Gate 근거: [완료 기록](../phase8-mariadb.md), 2026-11-04 기준.

## 구현 범위

도입 대상: 사용자 승인 범위의 정식 MariaDB 드라이버·격리 테스트 DB.
계획 수집: `EXPLAIN FORMAT=JSON`과 Vendor Adapter.
보존 필드: `access_type`·`key`·`rows`·`filtered`·`attached_condition`.
PostgreSQL 연산과의 임의 동치화 금지.

안전 기준: Vendor별 Allowlist·Read-only·최소 권한·Timeout·Credential 보호.
MariaDB Runtime: 이 단계의 제외 범위. 요청 시 명확한 거부.

## 기술 Gate

- [x] Phase 0~7·PostgreSQL 회귀 통과
- [x] 실제 MariaDB SELECT·JOIN·Aggregate Estimated Plan 확인
- [x] Vendor 구조·필드·HTML DATABASE 출처 확인
- [x] 쓰기·복수 Statement·Runtime 거부와 Read-only·Timeout 검증
- [x] 접속·권한·SQL 오류의 Credential 비노출 확인
- [x] Lock·pytest·Ruff·MariaDB 통합 테스트 통과

실제 DB 미확보 시 Phase 9 착수 금지.
결과 기록: `docs/phase8-mariadb.md`와 README.
브랜치: `feat/phase8-mariadb`.
Push·PR: 사용자 사전 승인 범위.
