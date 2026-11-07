# Phase 3. SQLPVI Skill 작업 지침

적용 시점: Phase 3 구현 단계. 선행 조건: Phase 2 기술 Gate 통과.
분석 근거: Agent의 실제 CLI 실행 결과.
Gate 근거: [완료 기록](../phase3-sqlpvi-skill.md), 2026-11-04 기준.

## 구현 범위

프로젝트 로컬 Skill 위치:

- Codex: `.agents/skills/sqlpvi/SKILL.md`
- 선택 연동 — Claude Code: `.claude/skills/sqlpvi/SKILL.md`

계약 내용: CLI 실행·입력 보존·결과 경로 보고·PARSED와 DBMS 성공의 구분.
안전 기준: STATIC 출처·미확정 참조 유지·실패 원인 보고·SQL 내 지시 비실행.
DB·LLM 환경 변수 및 API 호출 요구 없음.
전역 Skill 설치·설정 변경 제외.

## 기술 Gate

- [x] Phase 0~2 회귀 통과
- [x] 두 Skill의 메타데이터·실행 명령 확인
- [x] 절차에 따른 정상·오류·악성 문자열 CLI 입력 확인
- [x] HTML 경로·입력 보존·실패 코드 확인
- [x] Codex의 실제 CLI 실행과 산출물 확인
- [x] Lock·pytest·Ruff check/format 통과

검증 범위: Skill 형식과 Codex CLI 절차·산출물.
Claude Code 연동: 선택 사항. SQLPVI Core·CLI·MVP 완료의 필수 조건에서 제외.

결과 기록: `docs/phase3-sqlpvi-skill.md`와 README.
브랜치: `feat/phase3-sqlpvi-skill`.
Push·PR: 사용자 사전 승인 범위.
