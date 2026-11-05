# Phase 1. Static SQL Analysis 작업 지침

적용 시점: Phase 1 구현 단계. 선행 조건: Phase 0 기술 Gate 통과.
Gate 근거: [완료 기록](../phase1-static-analysis.md), 2026-11-04 기준.
현재 CLI 사용법: [README](../../README.md).

## 구현 범위

구현 위치: `src/sqlpvi/`.
구성: SQLGlot Adapter·독립 dataclass 모델·Reference Analyzer·SQL Flow Builder·Report·표준 CLI.

| 항목 | Phase 1 기준 |
| --- | --- |
| 기본 출력 | JSON |
| 출력 파일 | `--output` 지정 |
| 기본 Dialect | postgres |
| Parsing 성공 | PARSED |
| 실패 처리 | 빈 입력·복수 Statement·Parser 오류·파일 오류 |

참조 분석: Table·Column·Alias·Identifier 범위와 Query Scope의 Qualifier 해석.
Metadata 없는 단일 Table의 Column 존재 확정 금지.
복수 Relation의 미지정 Qualifier: AMBIGUOUS 유지.
근거 부족: UNRESOLVED 유지.
CTE·Subquery·상관 Subquery의 Scope 분리와 추측 연결 금지.

AST 출력: Parser 객체를 노출하지 않는 독립 트리.
SQL Flow: Scan·Project·Filter·Join·Aggregate·Sort·Distinct·Limit·Offset·CTE·Subquery.
DB 실행 가능성의 보증 금지.

## Fixture·검증

기존 SELECT·JOIN·Aggregate와 추가 CTE·Subquery·상관 Subquery 검증.
비정규화 참조·별칭 충돌·DISTINCT·ORDER BY·LIMIT·OFFSET·오류·빈 입력 포함.
실제 CLI의 stdout JSON·종료 코드·파일 출력·입력 보존 확인.

## 기술 Gate

- [x] Phase 0 회귀 통과
- [x] PARSED·오류 처리·독립 AST/Report 확인
- [x] Scope와 RESOLVED·AMBIGUOUS·UNRESOLVED 구분
- [x] 원문 Identifier와 Source Range 일치
- [x] 목표 SQL Flow·CTE·Subquery Fixture 통과
- [x] 설치된 CLI의 실제 JSON 출력 확인
- [x] Lock·pytest·Ruff check/format 통과

제외 범위: DB·HTML UI·Skill.
결과 기록: `docs/phase1-static-analysis.md`와 README.
브랜치: `feat/phase1-static-analysis`.
Push·PR: 사용자 사전 승인 범위.
