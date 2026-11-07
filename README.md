# SQL Plan Visualizer (SQLPVI)

SQL 파일의 구조·참조·실행 계획을 HTML로 시각화하는 분석 도구.

[프로젝트 문서 보기](https://seo-gali.github.io/sql-plan-visualizer/)

## 현재 상태

| 구분 | 확인 결과 |
| --- | --- |
| 기술 Gate | Phase 0~10 통과 |
| 최종 전체 회귀 | 2026-11-05 기준 258 passed, Skip 없음, exit 0 |
| 실제 DB 검증 | PostgreSQL·MariaDB·SQL Server 통합 테스트 통과 |
| Agent 연동 | Codex 프로젝트 로컬 Skill 제공. Claude Code 연동은 선택 사항 |
| Agent 검증 | Codex Skill 절차·CLI 산출물 확인 |

검증 수치의 기준: 각 완료 문서의 실제 실행 시점. 문서 수정에 따른 재검증 결과로의 대체 금지.

## 분석 흐름

문서 그림: Mermaid 다이어그램. 표시 조건: Mermaid 지원 Markdown 뷰어.

```mermaid
flowchart TD
    SQL["SQL 파일"] --> Static["정적 구조·참조 분석"]
    Static --> Mode{"DB 모드 지정"}
    Mode -->|"기본 모드"|Report["공통 Report 모델"]
    Mode -->|"--database"|Safety["허용 SQL·최소 권한·Timeout 검증"]
    Safety --> Plan["Estimated 계획 또는 PostgreSQL Runtime 수집"]
    Plan --> Evidence["실측 근거 충족 시 개선 후보 추가"]
    Evidence --> Report
    Report --> Output["Standalone HTML / JSON"]
```

- 기본 동작: DB 접속 없는 정적 분석.
- `PARSED`: Parser 처리 성공 표시. 실제 DB 실행 가능성 보증 제외.
- SQL Flow: SQL 구조 표현. DBMS 실행 순서와의 구분.
- HTML: SQL Source·References·AST·SQL Flow·실행 계획 표시.
- 화면 조작: 한/영 전환, Hover·키보드 Focus 연결, 작은 화면 지원.
- 분석 대상: SQL 구조와 실행 근거. 일반 조회 결과 행 수집·반환 제외.

## DB별 지원 범위

| Vendor | 기본 Dialect | 접속 환경 변수 | Estimated | Runtime | Catalog / 참조 보강 | 개선 후보 |
| --- | --- | --- | --- | --- | --- | --- |
| `postgres` | `postgres` | `SQLPVI_POSTGRES_URL` | 지원 | 지원 | 지원 | 실측 디스크 정렬·해시 임시 파일 점검 |
| `mariadb` | `mysql` | `SQLPVI_MARIADB_URL` | 지원 | 미지원 | 미지원 | 미지원 |
| `sqlserver` | `tsql` | `SQLPVI_SQLSERVER_URL` | 지원 | 미지원 | 미지원 | 미지원 |

PostgreSQL URL 선택 순서: `SQLPVI_POSTGRES_URL` 우선, 값 부재 시 기존 `SQLPVI_DATABASE_URL` 사용.
MariaDB의 `mysql` 표기: Parser Dialect 이름. 별도 MySQL 서버 검증 완료 의미 제외.

## 설치와 정적 분석

실행 환경: Python 3.13.15, uv. 의존성 버전: `uv.lock` 기준.

```powershell
uv --cache-dir .uv-cache sync --locked
uv --cache-dir .uv-cache run sqlpvi analyze fixtures/sql/join.sql
uv --cache-dir .uv-cache run sqlpvi analyze fixtures/sql/join.sql --format json
```

기본 HTML 경로: 입력 파일 옆의 `.sqlpvi.html`. 출력 경로 지정: `--output`.
별도 출력 경로의 부모 폴더: 분석 성공 후 자동 생성. 입력 SQL 덮어쓰기 거부.

확인된 Windows 제약: uv의 setuptools 캐시 파일 접근 거부.
기존 editable 설치 환경의 실제 검증 방식: `uv run --no-sync`.
신규 환경의 정상 설치 확인과 기존 환경의 복구 절차 구분.

- PyMySQL 캐시 복구 이력: [Phase 8 기록](docs/phase8-mariadb.md#환경-제약과-한계).
- pymssql 설치·Lock 갱신 이력: [Phase 9 기록](docs/phase9-sqlserver.md#실패와-수정).
- `--no-sync` 적용 조건: 필요한 패키지와 버전이 확인된 기존 환경.

## 격리 DB 준비

공개 암호·무비밀번호 계정의 용도: loopback 전용 합성 데이터 Fixture.
운영 DB 및 실제 비밀값의 사용 제외.

```mermaid
flowchart LR
    Images["Compose 서비스 기동"] --> Ready["DB 상태 확인"]
    Ready --> Init["SQL Server 생성·권한 스크립트"]
    Init --> Reader["조회 전용 계정 연결"]
    Reader --> Verify["분석·통합 테스트"]
```

```powershell
docker compose up -d --wait postgres mariadb mssql
docker compose run --rm sqlserver-init
```

| 서비스 | Windows 접속 주소 | 준비 방식 |
| --- | --- | --- |
| PostgreSQL | `127.0.0.1:55432` | 새 인스턴스의 초기 Fixture 실행 |
| MariaDB | `127.0.0.1:53306` | 새 인스턴스의 초기 Fixture 실행 |
| SQL Server | `127.0.0.1:14330` | `sqlserver-init` 실행 |

SQL Server init 동작: 없는 DB·Table·Login·User 생성과 테스트 계정의 `GRANT` 재실행.
기존 데이터 삭제·초기화 미수행. 기존 계정에 대한 권한 부여의 재적용 가능성.

PostgreSQL·MariaDB의 기존 인스턴스: 초기 Fixture 파일 변경의 자동 재적용 없음.
과거 SQL Server 컨테이너 `sqlpvi-test-sqlserver-1`: 삭제 없이 DB 보존. 현재 분석 대상: 14330의 `mssql` 서비스.
보존 대상이 있는 환경의 `--remove-orphans` 사용 금지.
초기 51433 포트의 Windows 예약 구간 충돌 및 14330 전환 이력: [Phase 9 기록](docs/phase9-sqlserver.md#실패와-수정).

## DB 분석 실행

다음 예제의 전제: 필요한 패키지 설치 완료, 위 격리 Fixture 준비 완료.

### PostgreSQL

```powershell
$env:SQLPVI_POSTGRES_URL = 'postgresql://sqlpvi_reader@127.0.0.1:55432/sqlpvi'
uv --cache-dir .uv-cache run --no-sync sqlpvi analyze fixtures/sql/join.sql --database
```

`--database`: Estimated Plan 조회. Catalog의 Schema·Column·Index·통계 근거 표시.
충분한 Catalog 근거가 있는 참조만 `DATABASE` 출처로 보강.

```powershell
uv --cache-dir .uv-cache run --no-sync sqlpvi analyze fixtures/sql/sort-spill.sql --database --runtime --output artifacts/recommendation.html
```

`--database --runtime`: 조회 Query의 실제 실행과 Actual Rows·Loops·Time·Buffers 수집.
`--runtime` 단독 사용 및 다른 Vendor의 Runtime 요청 거부.

### MariaDB

```powershell
$env:SQLPVI_MARIADB_URL = 'mariadb://sqlpvi_reader@127.0.0.1:53306/sqlpvi'
uv --cache-dir .uv-cache run --no-sync sqlpvi analyze fixtures/sql/join.sql --vendor mariadb --database --output artifacts/mariadb-join.html
```

수집 방식: `EXPLAIN FORMAT=JSON`.
보존 필드: `access_type`, `key`, `rows`, `filtered`, `attached_condition`.
접속 조건: 계정에 직접 부여한 조회 권한. 세션 Role 해제와 쓰기·권한 위임 검사 적용.

### SQL Server

```powershell
$env:SQLPVI_SQLSERVER_URL = 'sqlserver://sqlpvi_reader:Sqlpvi-Fixture-2026!@127.0.0.1:14330/sqlpvi'
uv --cache-dir .uv-cache run --no-sync sqlpvi analyze fixtures/sql/join.sql --vendor sqlserver --database --output artifacts/sqlserver-estimated.html
```

수집 방식: `SET SHOWPLAN_XML ON`. 입력 Query 실행 없이 Estimated Plan 수집.
예외 처리: SHOWPLAN OFF·Rollback 시도와 연결 종료.
XML 안전성: Namespace 확인과 DTD·Entity 거부.
`SELECT 1`: DB의 `SELECT WITHOUT QUERY` 상태와 추정치 없음 상태 보존.

허용 Table Hint: 인자 없는 `NOLOCK`, `READUNCOMMITTED`, `FORCESEEK`, `FORCESCAN`.
잠금 강제·알 수 없는 Hint·인자 있는 Hint의 거부. 입력 Hint의 자동 추가 없음.
`NOLOCK`·`READUNCOMMITTED`의 일관된 결과·무잠금 보장 없음. 계획 수집의 Query 미실행 유지.

## 근거 기반 개선 후보

현재 규칙: PostgreSQL 실측 정렬·해시의 입력량·세션 메모리 점검 2종.
공통 조건: `DATABASE`·`RUNTIME`, 유효한 양수 Actual Rows·Loops, 확정된 Column 참조.

| 후보 | 추가 근거 |
| --- | --- |
| 디스크 정렬 | `Sort Space Type=Disk`, 유효한 양수 `Sort Space Used` |
| 해시 임시 파일 | `Hash` 노드, `Hash Batches>1`, 유효한 양수 `Temp Written Blocks` |

후보 내용: 근거 ID·실행 계획 링크·관측값·이유·조건·한계·검증 SQL.

- 근거 출처: `DATABASE`.
- 후보 출처: `RECOMMENDATION`.
- 근거 부족 시 결과: 빈 후보 목록.
- Seq Scan 또는 높은 Cost·시간만으로 인덱스 권고 금지.
- 검증 SQL의 자동 실행, 입력 수정, Index·Schema 변경 금지.
- 추천 로직의 DB·LLM 접속 및 추천 목적의 Runtime 자동 실행 없음.

## 전체 검증

전제: 세 DB 준비 완료, 필요한 패키지 설치 완료.
SQL Server 환경 변수 누락 시 해당 통합 테스트의 Skip 가능성.

```powershell
$env:SQLPVI_TEST_POSTGRES_URL = 'postgresql://sqlpvi_reader@127.0.0.1:55432/sqlpvi'
$env:SQLPVI_TEST_MARIADB_URL = 'mariadb://sqlpvi_reader@127.0.0.1:53306/sqlpvi'
$env:SQLPVI_TEST_SQLSERVER_URL = 'sqlserver://sqlpvi_reader:Sqlpvi-Fixture-2026!@127.0.0.1:14330/sqlpvi'
uv --cache-dir .uv-cache --offline lock --check
uv --cache-dir .uv-cache run --no-sync pytest tests -q --basetemp artifacts/pytest-current -p no:cacheprovider --tb=short
uv --cache-dir .uv-cache run --no-sync ruff check .
uv --cache-dir .uv-cache run --no-sync ruff format --check .
```

Temp 경로 접근 오류 시 대응: 사용 가능한 새 프로젝트 내부 경로를 `--basetemp`로 지정.

### 과거 실행 기록

| 기록 시점 | 당시 결과 | 근거 |
| --- | --- | --- |
| 2026-11-04, Phase 8 완료 | 127 passed, Skip 없음, exit 0 | [MariaDB 완료 기록](docs/phase8-mariadb.md) |
| 2026-11-04, Phase 9 완료 | 185 passed, Skip 없음, exit 0 | [SQL Server 완료 기록](docs/phase9-sqlserver.md) |
| 2026-11-04, Phase 10 완료 | 211 passed, Skip 없음, exit 0 | [추천 완료 기록](docs/phase10-recommendation.md) |
| 2026-11-05, 코드 개선 | 258 passed, Skip 없음, exit 0 | [출력·힌트·해시 개선 기록](docs/code-improvements-2026-11-05.md) |

## 문서 안내

- [공개 문서: 소개·작업 단계·검증 기록](https://seo-gali.github.io/sql-plan-visualizer/)
- [로컬 문서 첫 화면](docs/index.html)
- [전체 계약·최종 완료 기준](.project/plan.md)
- [전체 기획의 현행 정리본](기획서.md)
- [프로젝트 운영·승인 규칙](AGENTS.md)
- [화면·접근성 기준](design.md)
- [Phase별 구현 지침](docs/instructions)
- [Phase 10 구현·검증 기록](docs/phase10-recommendation.md)
- [이후 코드 개선·검증 기록](docs/code-improvements-2026-11-05.md)
- [대신 내린 선택 기록](docs/sqlpvi-decisions-2026-11-05.html)

문서 사이트 진입점: `docs/index.html`. 주제별 탭과 이전·다음 단계 이동 지원.
흐름도의 HTML/CSS 직접 표시와 인터넷 없는 열람 지원.
선택 기록·샘플 보고서의 `docs` 내부 상대 경로 연결. 문서 HTML의 별도 그림 파일·Mermaid 실행 도구 요구 없음.

GitHub 웹 게시 방법: 저장소 업로드 후 Settings → Pages → Deploy from a branch → 게시할 브랜치와 `/docs` 선택.
`docs/.nojekyll`: 별도 Jekyll 변환 없는 정적 파일 제공.
설정 근거: [GitHub Pages 게시 경로 안내](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site).
