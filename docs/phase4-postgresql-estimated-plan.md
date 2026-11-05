# Phase 4. PostgreSQL Estimated Plan

2026-11-04 기술 Gate 통과. 사용자 승인 후 전용 PostgreSQL 18.6-alpine 컨테이너와
Fixture를 생성했다. 기존 DB는 사용하지 않았다.

## 구현

`--database`에서만 `SQLPVI_DATABASE_URL`을 사용한다. Psycopg 3.3.7로
Read-only Transaction, Connection/Statement/Lock Timeout, 최소 권한 계정 검사,
SELECT/함수 Allowlist를 적용하고 EXPLAIN FORMAT JSON을 공통 Report 모델로 변환한다.
중첩 DML, SELECT INTO, 잠금, 다중 Statement, 미허용 함수/사용자 타입 Cast를 거부한다.
Driver 오류는 종류만 표시하며 URL/원문 Exception은 출력하지 않는다.
HTML에 Vendor, ESTIMATED, DATABASE와 실제 Plan 트리/필드를 표시한다.

## 실제 검증

- `docker compose up -d --wait postgres`: exit 0, Healthy.
- `SQLPVI_TEST_POSTGRES_URL`을 승인된 격리 DB로 지정해 전체 pytest 실행:
  **72 passed**, exit 0. 실제 SELECT/JOIN/Aggregate/CTE/Subquery Plan을 확인했다.
- 실제 Reader의 Read-only 및 쓰기 거부/데이터 보존을 확인했다.
- 실제 Statement Timeout과 Collector의 1초 Lock Timeout을 확인했다.
- Superuser 연결 거부 및 Driver 오류 Credential 비노출 테스트 통과.
- `uv lock --check`, Ruff check/format: 각각 exit 0.
- CLI로 `artifacts/postgres-estimated.html` 및 `.json` 생성: exit 0.
  JSON의 PARSED/postgres/ESTIMATED/Aggregate 구조를 다시 읽어 확인했다.
- 브라우저에서 실행 계획, customers/orders, DATABASE 출처,
  HTML 접속 URL/계정 비노출을 assert로 확인했다.

## 환경 및 한계

공용 pytest Temp의 권한 충돌로 최초 회귀는 68 passed/3 setup errors였다.
확인된 프로젝트 내부 `artifacts/pytest-phase4`와 별도 Cache로 바꿔 전체 통과했다.
테스트 DB는 loopback에만 공개한 전용 컨테이너이며 무비밀번호 trust 설정은
이 격리 Fixture 전용이다. Production 사용법으로 제공하지 않는다.
Estimated는 Runtime 측정이 아니다. 허용한 SQL이라도 Planner가 DB 객체 코드를
평가할 수 있어 신뢰된 개발/테스트 DB와 최소 권한 계정을 사용해야 한다.
uv 자동 sync와 Git/Remote 제약은 이전 Phase와 같다.
