# Phase 3. SQLPVI Skill

2026-11-04 기술 Gate 통과. Codex와 Claude Code의 프로젝트 로컬 Skill을 추가했다.

## 구현 및 검증

- `.agents/skills/sqlpvi/SKILL.md`, `.claude/skills/sqlpvi/SKILL.md`에
  실제 CLI 실행/출력 확인, 실패 보고, PARSED/STATIC/Reference 상태 구분,
  SQL 입력 보존과 SQL 내 지시 비실행을 명시했다. 전역 설정은 수정하지 않았다.
- 공식 Skill Creator의 `quick_validate.py`를 두 파일에 실행:
  각각 **Skill is valid!**, exit 0.
- 검증기의 PyYAML 부재로 최초 실행은 실패했다. PyYAML 6.0.3을
  `artifacts/skill-validator-deps`에만 설치해 재실행했다. 앱 의존성은 추가하지 않았다.
- 현재 Codex가 Skill 절차대로 `uv run --no-sync sqlpvi analyze ...`를 실행하고
  생성 HTML과 JSON을 실제로 읽어 PARSED와 출력 존재를 확인했다.
- 악성 문자열 HTML 생성 성공, 잘못된 SQL은 exit 1 / 결과 파일 미생성을 확인했다.
- 회귀: **47 passed**, exit 0. `uv lock --check`, Ruff check/format 각각 exit 0.

## 검증 범위 및 한계

Codex의 절차 수행과 파일 형식은 확인했다. 실행 중 세션의 자동 Skill 재발견과
새 세션의 선택 UI는 검증하지 않았다. Claude Code CLI는 설치되지 않아
실제 `/sqlpvi` 호출은 미검증이며 실행한 것으로 주장하지 않는다.
uv 자동 sync 접근 거부와 Git/Remote 부재는 이전 Phase와 같다.

근거: [Codex 로컬 Skill 위치](https://learn.chatgpt.com/docs/build-skills),
[Claude Code 프로젝트 Skill](https://code.claude.com/docs/en/skills).
