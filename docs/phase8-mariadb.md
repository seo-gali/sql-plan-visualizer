# Phase 8. MariaDB

기록 기준: 2026-11-04 Phase 8 완료 시점.
기술 Gate: 통과. Git 상태: 저장소 부재에 따른 Branch·Commit·Push·PR 미수행.
최신 상태: [README](../README.md).

## 구현

| 항목 | 구현 내용 |
| --- | --- |
| 수집기 | `src/sqlpvi/db/mariadb.py`, PyMySQL |
| CLI / Dialect | `--vendor mariadb` / `mysql` |
| 접속 변수 | `SQLPVI_MARIADB_URL` |
| 수집 방식 | `EXPLAIN FORMAT=JSON` |
| 모델 | 기존 Report·ExecutionPlan |
| Vendor 구조 | query_block·nested_loop 등 원래 구조 보존 |
| Vendor 필드 | access_type·key·rows·filtered·attached_condition 보존 |

변환 원칙: rows·filtered의 임의 결합 및 PostgreSQL Scan과의 동치화 금지.
Renderer 입력: 기존 Report 모델 유지.

안전 경계: 공유 Statement·함수 Allowlist, Read-only Transaction,
5초 Statement Timeout, 1초 Lock Timeout, Connection·Socket Timeout.
파일 입력 옵션: `local_infile=False`.
권한 검사: 세션 Role 해제, 전역·DB·Table·Column의 쓰기 권한·GRANT OPTION 거부.
오류 출력: Driver 오류 종류만 표시.
MariaDB Runtime: CLI·Collector에서 거부.

Driver Import 시점: MariaDB 연결 요청 시점.
PyMySQL 미설치 환경의 정적 분석·PostgreSQL 경로 유지.

격리 Fixture: Schema·Table·Column Writer와 GRANT OPTION 검사 계정 제공.
해당 계정의 사용 범위: loopback 전용 테스트 DB.

## 실제 검증

DB 준비: 사용자의 일반 PowerShell에서 PostgreSQL·MariaDB Compose 기동과 Healthy 확인.
이후 검증: Codex 셸에서 두 DB에 직접 연결.

```powershell
uv --cache-dir .uv-cache pip install --python .venv/Scripts/python.exe --no-deps --offline pymysql==1.2.3
$env:SQLPVI_TEST_POSTGRES_URL = 'postgresql://sqlpvi_reader@127.0.0.1:55432/sqlpvi'
$env:SQLPVI_TEST_MARIADB_URL = 'mariadb://sqlpvi_reader@127.0.0.1:53306/sqlpvi'
uv --cache-dir .uv-cache run --no-sync pytest tests -q --basetemp artifacts/pytest-phase8-database -p no:cacheprovider --tb=short
uv --cache-dir .uv-cache --offline lock --check
uv --cache-dir .uv-cache run --no-sync ruff check .
uv --cache-dir .uv-cache run --no-sync ruff format --check .
```

| 검증 | 당시 결과 |
| --- | --- |
| PyMySQL 설치 | 기존 Lock의 1.2.3 설치, exit 0 |
| 전체 회귀 | 127 passed in 14.71s, Skip 없음, exit 0 |
| MariaDB 실제 계획 | SELECT·JOIN·Aggregate·CTE·Subquery 통과 |
| PostgreSQL 회귀 | Estimated·Runtime·Catalog·권한·Timeout 통과 |
| 최소 권한 | Global·Schema·Table·Column Writer와 GRANT OPTION 거부 |
| 쓰기 방지 | Reader 거부·데이터 보존, Root Read-only 거부 코드 1792 확인 |
| Timeout | Statement 코드 1969, Collector Lock Timeout 확인 |
| 입력·오류 | 쓰기·복수 Statement·파일 출력·함수·Runtime 거부와 Credential 비노출 |
| HTML·CLI | Vendor 문자열 Escape·URL 검증·Driver 미설치·Static 경로 통과 |
| Lock·Ruff | 각 exit 0, 포맷 확인 49개 파일 |

위 수치의 범위: Phase 8 당시 실행. 이후 단계 결과로의 덮어쓰기 없음.

### 실제 CLI

```powershell
$env:SQLPVI_MARIADB_URL = 'mariadb://sqlpvi_reader@127.0.0.1:53306/sqlpvi'
uv --cache-dir .uv-cache run --no-sync sqlpvi analyze fixtures/sql/aggregate.sql --vendor mariadb --database --output artifacts/mariadb-estimated.html
uv --cache-dir .uv-cache run --no-sync sqlpvi analyze fixtures/sql/aggregate.sql --vendor mariadb --database --format json --output artifacts/mariadb-estimated.json
uv --cache-dir .uv-cache run --no-sync sqlpvi analyze fixtures/sql/join.sql --vendor mariadb --database --output artifacts/mariadb-join.html
uv --cache-dir .uv-cache run --no-sync sqlpvi analyze fixtures/sql/join.sql --vendor mariadb --database --format json --output artifacts/mariadb-join.json
```

네 명령의 결과: 각각 exit 0.
JSON 확인: PARSED·mysql·mariadb·ESTIMATED·DATABASE와 Table 필드.
안전성 확인: HTML/JSON의 접속 URL 비노출, JOIN 입력 SQL Hash 보존.

브라우저 검증: Playwright의 로컬 HTTP 경로로 두 HTML 확인.
JOIN 관측: Vendor·Estimated·DATABASE, access_type·key·rows·filtered·attached_condition,
orders_customer_idx, 유효한 SVG 연결선 4개.
외부 Resource: 0개. Console Error·Warning: 0개.

## 환경 제약과 한계

초기 상태: PyMySQL 미설치·DB 미기동. 당시 로컬 결과: 99 passed·28 skipped.
일반 sync 실패: setuptools 84.2.1 캐시의 entry_points.txt 접근 거부 코드 5.
복구 경로: 사용자의 설치 시도로 준비된 Wheel의 오프라인 설치와 기존 editable 환경 사용.
Phase 8 복구 작업의 보안 설정·ACL·의존성 버전·Lock 변경 없음.
일반 sync의 캐시 오류: 해당 시점의 미해결 제약.

DockSlate CLI: Codex 셸의 접근 거부에 따른 수명주기 조작 미검증.
DB 검증 범위: 사용자가 기동한 loopback 인스턴스.
DB·Volume 삭제·초기화 없음. 브라우저 검증용 임시 HTTP 서버 종료 완료.

기능 한계: MariaDB Runtime·Catalog 기반 참조 보강 미제공.
접속 권한: Role 경유가 아닌 계정 직접 조회 권한 필요.
Estimated 사용 전제: 신뢰된 개발·테스트 DB와 최소 권한 계정.

Phase 8 기록 시점의 후속 상태: Phase 9~10 착수 전.
이후 진행 결과: [Phase 9](phase9-sqlserver.md)·[Phase 10](phase10-recommendation.md).
