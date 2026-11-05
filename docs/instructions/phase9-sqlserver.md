# Phase 9. Microsoft SQL Server 작업 지침

적용 시점: Phase 9 구현 단계. 선행 조건: Phase 8 기술 Gate 통과.
Gate 근거: [완료 기록](../phase9-sqlserver.md), 2026-11-04 기준.

## 구현 범위

도입 대상: 사용자 승인 범위의 SQL Server 드라이버·격리 테스트 DB.
수집 방식: `SET SHOWPLAN_XML`의 Query 미실행 계획.
변환 기준: XML Namespace 처리와 공통·Vendor 필드 보존.
HTML 표시: Estimated 연산·Rows·Index.

| 경계 | 기준 |
| --- | --- |
| XML | 외부 Entity 거부 |
| 예외 | SHOWPLAN OFF 시도·연결 정리 |
| SQL·권한 | SELECT Allowlist·최소 권한 |
| 자원·출력 | Timeout·Credential 비노출 |
| Runtime | 미지원 요청 거부 |

## 기술 Gate

- [x] Phase 0~8·PostgreSQL·MariaDB 회귀 통과
- [x] 실제 SQL Server SELECT·JOIN·Aggregate SHOWPLAN_XML 확인
- [x] Query 미실행·세션 복구·권한/Timeout 실패 처리 검증
- [x] XML 안전성·Vendor 정보·HTML 출처 확인
- [x] Connection String·Credential 비노출 확인
- [x] Lock·pytest·Ruff·SQL Server 통합 테스트 통과

실제 DB 미확보 시 Phase 10 착수 금지.
결과 기록: `docs/phase9-sqlserver.md`와 README.
브랜치: `feat/phase9-sqlserver`.
Push·PR: 사용자 사전 승인 범위.
