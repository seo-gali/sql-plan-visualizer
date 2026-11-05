# Phase 3. SQLPVI Skill 작업 지침

적용 시점: Phase 3 구현 단계. 선행 조건: Phase 2 기술 Gate 통과.
분석 근거: Agent의 실제 CLI 실행 결과.
Gate 근거: [완료 기록](../phase3-sqlpvi-skill.md), 2026-11-04 기준.

## 구현 범위

프로젝트 로컬 Skill 위치:

- Codex: `.agents/skills/sqlpvi/SKILL.md`
- Claude Code: `.claude/skills/sqlpvi/SKILL.md`

계약 내용: CLI 실행·입력 보존·결과 경로 보고·PARSED와 DBMS 성공의 구분.
안전 기준: STATIC 출처·미확정 참조 유지·실패 원인 보고·SQL 내 지시 비실행.
DB·LLM 환경 변수 및 API 호출 요구 없음.
전역 Skill 설치·설정 변경 제외.

## 기술 Gate

- [x] Phase 0~2 회귀 통과
- [x] 두 Skill의 메타데이터·실행 명령 확인
- [x] 절차에 따른 정상·오류·악성 문자열 CLI 입력 확인
- [x] HTML 경로·입력 보존·실패 코드 확인
- [x] Agent별 실제 실행 범위와 미확인 환경의 구분 기록
- [x] Lock·pytest·Ruff check/format 통과

검증 범위: Skill 형식과 Codex CLI 절차.
미검증 항목: Claude Code 실제 호출, 자동 Skill 재발견·새 세션 선택 UI.
Gate의 의미: 실행 범위의 확인·구분 기록. 미검증 환경의 성공 간주 금지.

결과 기록: `docs/phase3-sqlpvi-skill.md`와 README.
브랜치: `feat/phase3-sqlpvi-skill`.
Push·PR: 사용자 사전 승인 범위.
