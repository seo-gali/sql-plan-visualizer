# Phase 7. Multi-DBMS Architecture 작업 지침

적용 시점: Phase 7 구현 단계. 선행 조건: Phase 6 기술 Gate 통과.
Gate 근거: [완료 기록](../phase7-multi-dbms-architecture.md), 2026-11-04 기준.

## 구현 범위

변환 경계: 검증된 PostgreSQL 경로의 Vendor Adapter 분리.
보존 정보: 공통 Plan 필드·Vendor별 속성.
Renderer 입력: Report 모델.

도입 항목: `--vendor`, `SQLPVI_POSTGRES_URL`, `SQLPVI_MARIADB_URL`, `SQLPVI_SQLSERVER_URL`.
기존 PostgreSQL URL의 명시적 호환 경로 유지.
미지원 Vendor·Dialect 조합 거부.
이 단계의 후속 Vendor 드라이버 선반영 금지.

## 기술 Gate

- [x] Phase 0~6·실제 PostgreSQL Estimated/Runtime 회귀 통과
- [x] 기존 CLI·환경 변수 호환과 새 PostgreSQL 경로 확인
- [x] Vendor 속성 보존·미지원 조합의 실패 확인
- [x] DB 없는 Static·Renderer 경계 검증
- [x] Lock·pytest·Ruff check/format 통과

결과 기록: `docs/phase7-multi-dbms-architecture.md`와 README.
브랜치: `feat/phase7-multi-dbms-architecture`.
Push·PR: 사용자 사전 승인 범위.
