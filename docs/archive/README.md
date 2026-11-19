# 과거 기획·구현·검증 기록

보관 분류 기준일: 2026-11-15.
기존 파일의 위치와 URL을 유지한 기록 목록. 파일 이동·삭제 없음.

현재 사용법: [루트 README](../../README.md).
현재 설계 계약: [.project/plan.md](../../.project/plan.md).
현재 문서 안내: [문서 맵](../README.md).

## Phase 0~10

지침: 해당 단계의 목표·Fixture·Gate 기록.
결과: 실제 실행한 명령·당시 수치·확인한 한계의 근거.
완료한 단계의 자료이며, 향후 기능의 구현 완료를 뜻하는 자료는 아님.

| Phase | 당시 범위 | 구현 지침 | 실행 결과 |
| --- | --- | --- | --- |
| 0 | 구현 가능성 | [지침](../instructions/phase0-feasibility.md) | [결과](../phase0-feasibility.md) |
| 1 | 정적 분석 | [지침](../instructions/phase1-static-analysis.md) | [결과](../phase1-static-analysis.md) |
| 2 | HTML 시각화 | [지침](../instructions/phase2-html-visualization.md) | [결과](../phase2-html-visualization.md) |
| 3 | SQLPVI Skill | [지침](../instructions/phase3-sqlpvi-skill.md) | [결과](../phase3-sqlpvi-skill.md) |
| 4 | PostgreSQL 예상 계획 | [지침](../instructions/phase4-postgresql-estimated-plan.md) | [결과](../phase4-postgresql-estimated-plan.md) |
| 5 | Catalog·참조 보강 | [지침](../instructions/phase5-postgresql-plan-enrichment.md) | [결과](../phase5-postgresql-plan-enrichment.md) |
| 6 | PostgreSQL 실제 측정 | [지침](../instructions/phase6-postgresql-runtime-plan.md) | [결과](../phase6-postgresql-runtime-plan.md) |
| 7 | 다중 DBMS 구조 | [지침](../instructions/phase7-multi-dbms-architecture.md) | [결과](../phase7-multi-dbms-architecture.md) |
| 8 | MariaDB | [지침](../instructions/phase8-mariadb.md) | [결과](../phase8-mariadb.md) |
| 9 | SQL Server | [지침](../instructions/phase9-sqlserver.md) | [결과](../phase9-sqlserver.md) |
| 10 | 근거 기반 점검 후보 | [지침](../instructions/phase10-recommendation.md) | [결과](../phase10-recommendation.md) |

## 후속 변경과 선택 기록

| 자료 | 기록 기준 | 보관 이유 |
| --- | --- | --- |
| [기획 정리본](../../기획서.md) | 2026-11-05, 후속 문구 수정 포함 | 원안의 20개 절과 당시 구현 차이 |
| [출력·Hint·해시 개선](../code-improvements-2026-11-05.md) | 2026-11-05 | 전체 258개 검사와 개선 근거 |
| [작업 경위 HTML](../index.html) | 2026-11-04~07 | 요청·실패·수정·검증의 과정 |
| [구현 선택 HTML](../sqlpvi-decisions-2026-11-05.html) | 2026-11-05 | 당시 범위·기본값의 선택 |
| [기획서 선택 HTML](../planning-decisions-2026-11-05.html) | 2026-11-05 | 당시 기획 정리 방식 |

자료 해석: 기술 Gate·과거 검사 통과·현재 지원 범위의 구분.
현재 코드와 다른 문구는 해당 기록의 기준일과 현재 계약을 함께 확인.
