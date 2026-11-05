# Phase 5. PostgreSQL Plan Enrichment 작업 지침

적용 시점: Phase 5 구현 단계. 선행 조건: Phase 4 기술 Gate 통과.
Gate 근거: [완료 기록](../phase5-postgresql-plan-enrichment.md), 2026-11-04 기준.

## 구현 범위

Catalog 조회 대상: Relation·Column·Index·Statistics.
참조 보강 조건: 충분한 Metadata 근거.
참조 상태: 기존 세 종류 유지. 출처: DATABASE로 구분.
연결 기준: Schema·Search Path·Alias 고려, 추측 연결 금지.

계획 정보: Filter·Join·Index 조건과 Vendor 속성 보존.
권한 부족: 명시적 안내와 Static 결과 보존.
자동 SQL·Index 수정 제외.

## 기술 Gate

- [x] Phase 0~4 회귀·실제 PostgreSQL 통합 통과
- [x] Metadata 근거가 있는 Column만 RESOLVED·DATABASE 보강
- [x] 다중 Schema·동명 Column·권한 부족·오래된 통계의 한계 검증
- [x] 실제 계획 조건·Index 근거·HTML 표시 확인
- [x] Metadata 유무와 무관한 SQL 입력·DB 데이터 보존
- [x] Lock·pytest·Ruff check/format 통과

결과 기록: `docs/phase5-postgresql-plan-enrichment.md`와 README.
브랜치: `feat/phase5-postgresql-plan-enrichment`.
Push·PR: 사용자 사전 승인 범위.
