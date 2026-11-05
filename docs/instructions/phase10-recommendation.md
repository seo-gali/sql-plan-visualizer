# Phase 10. Evidence 기반 Recommendation 작업 지침

적용 시점: Phase 10 구현 단계. 선행 조건: Phase 9 기술 Gate 통과.
Gate 근거: [완료 기록](../phase10-recommendation.md), 2026-11-04 기준.

## 구현 범위

규칙의 입력: 확인된 Static·Database·Runtime 근거.
후보의 필수 정보: Evidence ID·관측 사실·이유·적용 조건·한계·검증 방법.
Seq Scan만을 근거로 한 Index 권고 금지.
Exact Cost·Runtime의 보편 임계값 사용 금지.
근거 부족 시 후보 미생성.

Suggested SQL·Index의 텍스트 표시만 허용.
자동 실행·입력 SQL 수정·Schema 변경·LLM API 사용 제외.

Phase 10 당시 검증 규칙: 실측 PostgreSQL 디스크 정렬 점검 1종.
후속 코드 개선: [2026-11-05 기록](../code-improvements-2026-11-05.md)의 해시 임시 파일 점검 추가. 현재 2종.
일반화된 SQL·Index 자동 최적화 완료로의 과대 표기 금지.

## 기술 Gate

- [x] Phase 0~9·모든 Vendor 회귀 통과
- [x] 각 후보의 실제 Evidence 연결·RECOMMENDATION 출처 표시
- [x] 근거 부족·작은 Table·불확실 Reference의 오권고 방지 확인
- [x] 실제 DB 근거의 후보·설명·한계·검증 절차 확인
- [x] SQL/Index 자동 실행 없음·입력 보존 확인
- [x] Lock·pytest·Ruff·전체 통합 테스트 통과

결과 기록: `docs/phase10-recommendation.md`와 README.
브랜치: `feat/phase10-recommendation`.
Push·PR: 사용자 사전 승인 범위.
