# Phase 7. Multi-DBMS Architecture

2026-11-04 기술 Gate 통과.

PostgreSQL Adapter를 `src/sqlpvi/db/postgres.py`로 이동하고 Statement 안전 경계를
`db/safety.py`로 분리했다. `database.py`는 Vendor 선택과 URL Migration을 담당한다.
기존 내부 PostgreSQL 진입점도 유지했다. Renderer는 기존 Report 모델만 받는다.

실제 검증:

- 전체 회귀와 실제 PostgreSQL Estimated/Runtime: **83 passed**, exit 0.
- 새 `SQLPVI_POSTGRES_URL` 우선과 기존 `SQLPVI_DATABASE_URL` fallback 테스트 통과.
- 실제 CLI에서 새 URL과 의도적으로 잘못된 기존 URL을 함께 지정해 새 경로 성공 확인.
- `--vendor postgres` 실제 HTML 생성: exit 0.
- 미지원 Vendor와 Vendor/Dialect 불일치 거부 확인.
- `uv lock --check`, Ruff check/format, Compose config: 각각 exit 0.

다른 Vendor 드라이버는 이 Phase에 추가하지 않았다. Common Plan 필드와 Vendor
세부 필드를 유지했으며 서로 다른 Scan 이름을 같은 실행 방식으로 단정하지 않는다.
uv/Git 환경 제약은 이전과 같다.
