# SQL Plan Visualizer (SQLPVI)

SQL 파일의 구조·참조·실행 계획을 HTML로 시각화하는 분석 도구.

[프로젝트 문서 보기](https://seo-gali.github.io/sql-plan-visualizer/)

[그림으로 보는 사용 방법](docs/usage.html) · [웹 사용 안내](https://seo-gali.github.io/sql-plan-visualizer/usage.html)

[보안 점검 보고서](docs/security.html) · [보안 기준](SECURITY.md)

## 사용 방법

현재 연결 방식: **Codex → 로컬 SQLPVI Skill → SQLPVI CLI**.
MCP 서버·MCP 등록 설정의 현재 구현 없음.
입력: `.sql` 파일. 출력: SQL 구조·참조·실행 계획의 HTML 또는 JSON 리포트.

```mermaid
flowchart LR
    File["1. SQL 파일 준비"] --> Request["2. Codex에서 $sqlpvi 요청"]
    Request --> Skill["로컬 Skill의 CLI 호출"]
    Skill --> Analyze["SQL 구조·참조 분석"]
    Analyze --> HTML["3. HTML 생성 경로 확인"]
    HTML --> Browser["4. 브라우저에서 리포트 열기"]
```

### Step 1. 프로젝트와 SQL 파일 준비

작업 위치: 이 저장소의 프로젝트 폴더.
처음 설치: 아래 [설치 안내](#설치와-정적-분석)의 Core 설치.
첫 분석 입력: 저장소의 `fixtures/sql/join.sql`.

### Step 2. Codex 대화에서 요청

아래 내용의 입력 위치: **Codex 대화창**.
PowerShell 명령과의 구분.

```text
$sqlpvi
입력: fixtures/sql/join.sql
HTML 출력: artifacts/sqlpvi-join.html
```

Skill의 역할: SQLPVI CLI 실행과 실제 출력 확인.
성공 응답에서 확인할 항목: 종료 결과·생성한 HTML 경로.

직접 실행을 선택한 경우의 **PowerShell 명령**:

```powershell
uv --cache-dir .uv-cache run --no-sync sqlpvi analyze fixtures/sql/join.sql --output artifacts/sqlpvi-join.html
```

`--no-sync`의 전제: 아래 설치 절차로 필요한 패키지를 준비한 기존 환경.

### Step 3. HTML 리포트 열기

PowerShell의 열기 명령:

```powershell
Invoke-Item artifacts/sqlpvi-join.html
```

읽는 순서: SQL Source → References → SQL Flow → AST 상세.
`PARSED`: Parser 처리 성공. 실제 DB의 실행 가능성·객체 존재 보증 제외.
`AMBIGUOUS`·`UNRESOLVED`: 확정 근거가 부족한 참조.

### 반복 수정: 한 번 실행과 저장 감지

`--watch`: 같은 SQL 파일의 저장 후 정적 HTML 자동 재생성.
아래 명령의 최초 실행 후 PowerShell 유지.

```powershell
.\.venv\Scripts\sqlpvi.exe analyze artifacts/my-query.sql --output artifacts/my-query.html --watch
```

사용 순서: 메모장의 SQL 수정·Ctrl+S → 자동 분석 → 열린 HTML에서 F5.
종료: PowerShell의 Ctrl+C.

```mermaid
flowchart LR
    Save["SQL 수정·저장"] --> Watch["--watch의 변경 감지·자동 분석"]
    Watch --> HTML["같은 HTML 파일 갱신"]
    HTML --> Refresh["브라우저 F5로 확인"]
```

전제: 기존 설치와 분석할 SQL 파일 준비.
감지 기준: 0.5초 간격의 파일 내용 비교. 변경 없는 파일의 반복 분석 없음.
문법 오류·파일 부재: 터미널 오류 표시와 이전 HTML 유지. 수정 저장 후 재분석.
지원 범위: 정적 HTML. `--database`·JSON 출력과의 결합 거부.

### Step 4. DB 실행 계획이 필요한 경우

기본 파일 분석의 DB 접속 없음.
추가 조건: DB별 Extra·조회 전용 계정·접속 URL 준비 후 `--database` 명시.
DB 분석 명령은 [DB 분석 실행](#db-분석-실행)에서 선택.

```mermaid
flowchart TD
    SQL["SQL 파일"] --> Mode{"분석 선택"}
    Mode -->|"기본"|Static["DB 접속 없이 구조 분석"]
    Mode -->|"--database"|Estimated["선택 DB의 예상 실행 계획 조회"]
    Mode -->|"PostgreSQL --database --runtime"|Runtime["조회 Query 실제 실행·측정"]
    Static --> Report["HTML / JSON 리포트"]
    Estimated --> Report
    Runtime --> Report
```

Runtime 선택의 의미: 실제 조회 Query 실행. 명시적 요청이 필요한 별도 모드.
기본 Skill의 범위: 정적 파일 분석. DB 실행 요청의 자동 확대 금지.

## 현재 상태

| 구분 | 확인 결과 |
| --- | --- |
| 기술 Gate 기록 | 2026-11-04 Phase 0~10 당시 검증 통과 |
| 최종 전체 회귀 | 2026-11-05 기준 258 passed, Skip 없음, exit 0 |
| 최근 수정 검증 | 2026-11-19 보안 보강 후 DB 제외 267 passed. 통합 검사 52개 미실행 |
| Watch 재확인 | 2026-11-18 관련 검사 5 passed. 설치된 CLI의 저장 감지·오류 후 복구 확인 |
| 실제 DB 검증 이력 | 2026-11-05 전체 회귀에 세 DB 통합 테스트 포함. 이번 수정의 DB 재검증 미실행 |
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

### 정적 분석·참조 보강

2026-11-15 점검에서 발견한 문제의 [수정·검증 기록](docs/audit-fixes-2026-11-16.md).

- 윈도 함수: `Window` 노드 표시. 일반 `Aggregate`와의 구분.
- 집합 연산: `UNION`·`INTERSECT`·`EXCEPT` 뒤 `Sort → Offset → Limit` 연결.
- Catalog 재적용: 매번 원래 정적 후보에서 재판정. 이전 Metadata·경고의 갱신.

JSON의 `static_references`: 최초 정적 참조의 보존본. 기존 `references`: 현재 근거를 반영한 참조.
새 필드의 추가에 따른 엄격한 JSON 소비 코드의 확인 필요.

## DB별 지원 범위

| Vendor | 기본 Dialect | 접속 환경 변수 | Estimated | Runtime | Catalog / 참조 보강 | 개선 후보 |
| --- | --- | --- | --- | --- | --- | --- |
| `postgres` | `postgres` | `SQLPVI_POSTGRES_URL` | 지원 | 지원 | 지원 | 실측 디스크 정렬·해시 임시 파일 점검 |
| `mariadb` | `mysql` | `SQLPVI_MARIADB_URL` | 지원 | 미지원 | 미지원 | 미지원 |
| `sqlserver` | `tsql` | `SQLPVI_SQLSERVER_URL` | Loopback에서 지원 | 미지원 | 미지원 | 미지원 |

PostgreSQL URL 선택 순서: `SQLPVI_POSTGRES_URL` 우선, 값 부재 시 기존 `SQLPVI_DATABASE_URL` 사용.
MariaDB의 `mysql` 표기: Parser Dialect 이름. 별도 MySQL 서버 검증 완료 의미 제외.

### 보안 경계

- SQL 파일 상한: 1MiB. 일반 분석·Watch의 동일 기준.
- HTML: SQL·Metadata Escape, 검토된 JS·CSS Hash만 허용하는 CSP, Referrer 미전송.
- 원격 PostgreSQL: 인증서·호스트 이름 검증, TLS 1.2 이상 요구. Service·간접 대상에도 보수적 TLS 적용.
- 원격 MariaDB: 시스템 신뢰 저장소의 인증서·호스트 검증과 TLS 요구. PyMySQL 최소 1.2.3.
- SQL Server: 인증서 검증을 보장하지 못하는 원격 연결의 현재 차단. Loopback만 지원.
- PostgreSQL 계정: 관리 Role·DB/Schema 생성·테이블/Column 쓰기·Sequence 변경·권한 위임의 추가 검사.

리포트의 포함 정보: SQL 원문·DB 객체·실행 계획·확보된 Metadata.
기본 출력 `*.sqlpvi.html`의 Git 제외. 사용자 지정 HTML·JSON의 공개 전 개별 검토 필요.
Compose의 Trust·무비밀번호·공개 암호는 합성 Fixture 전용. 운영 배포의 사용 금지.

보안 검증의 범위·미확인 항목: [점검 보고서](docs/security.html).

## 설치와 정적 분석

실행 환경: Python 3.13.15, uv. 의존성 버전: `uv.lock` 기준.

```powershell
uv --cache-dir .uv-cache sync --locked --no-dev
uv --cache-dir .uv-cache run --no-dev sqlpvi analyze fixtures/sql/join.sql
uv --cache-dir .uv-cache run --no-dev sqlpvi analyze fixtures/sql/join.sql --format json
```

기본 실행 의존성: SQLGlot·Jinja2. DB Driver·pytest·Ruff의 필수 설치 제외.

기본 HTML 경로: 입력 파일 옆의 `.sqlpvi.html`. 출력 경로 지정: `--output`.
별도 출력 경로의 부모 폴더: 분석 성공 후 자동 생성. 입력 SQL 덮어쓰기 거부.

신규 설치 검증의 남은 제약: 기존 setuptools 캐시 접근 오류 이력과 새 캐시의 다운로드 차단.
2026-11-16 현재, 새 환경의 전체 설치 성공은 미확인. 기존 환경의 실행 성공과 별도 항목.
기존 editable 설치 환경의 실제 검증 방식: `uv run --no-sync`. 필요한 패키지·버전 확인 후 사용.

- PyMySQL 캐시 복구 이력: [Phase 8 기록](docs/phase8-mariadb.md#환경-제약과-한계).
- pymssql 설치·Lock 갱신 이력: [Phase 9 기록](docs/phase9-sqlserver.md#실패와-수정).
- `--no-sync` 적용 조건: 필요한 패키지와 버전이 확인된 기존 환경.

### DB별 선택 설치

사용할 DB 하나에 맞는 Extra 선택. 다음 명령의 예: PostgreSQL.

```powershell
uv --cache-dir .uv-cache sync --locked --no-dev --extra postgres
```

| 목적 | 선택 값 |
| --- | --- |
| PostgreSQL | `--extra postgres` |
| MariaDB | `--extra mariadb` |
| SQL Server | `--extra sqlserver` |
| 세 DB 모두 | `--all-extras` |

선택한 Extra 유지: 아래 DB 실행 예제의 `uv run --no-sync` 사용.
Extra 없는 동기화의 영향: 기존 환경에서 불필요한 DB Driver 제거 가능.
패키지 버전의 변경 없이 의존성 분류만 변경.

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

## 검증

### DB 없는 개발 검사

`dev` 그룹: pytest·Ruff. 기본 `uv sync`에 포함되는 개발 도구.

```powershell
uv --cache-dir .uv-cache sync --locked
uv --cache-dir .uv-cache run --no-sync pytest tests -m 'not integration' -q --basetemp artifacts/pytest-core -p no:cacheprovider --tb=short
uv --cache-dir .uv-cache run --no-sync ruff check src tests
uv --cache-dir .uv-cache run --no-sync ruff format --check src tests
```

정적 CLI·테스트 수집: 세 DB Driver 없이 사용 가능.
검증 기준: Script 개수·SQL 호출의 고정 위치 대신 원문 보존·안전 경계·연결 동작.

브라우저 계약 검사: [준비 코드](tests/browser/prepare_report.py)와 [Playwright 검사 함수](tests/browser/report_contract.js).
합성 Plan을 사용한 별도 검사. pytest의 자동 실행 대상과 실제 DB 검증에서 제외.
실행 절차: [수정 기록의 브라우저 검사](docs/audit-fixes-2026-11-16.md#브라우저-검사).

### 전체 DB 검사

전제: 세 DB 준비 완료, 필요한 패키지 설치 완료.
SQL Server 환경 변수 누락 시 해당 통합 테스트의 Skip 가능성.

```powershell
uv --cache-dir .uv-cache sync --locked --all-extras
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

- [문서 맵](docs/README.md): 현재 기준과 과거 근거의 용도별 안내.
- [그림 사용 안내](docs/usage.html): Codex 요청·직접 명령·리포트 읽기·DB 모드 선택.
- [보안 점검](docs/security.html) · [보안 기준](SECURITY.md): 적용한 보호·실제 검사·출시 전 남은 확인.
- [수정·검증 기록](docs/audit-fixes-2026-11-16.md): SQL Flow·Catalog·의존성·테스트 개선과 남은 제약.
- [전체 점검·확장 설계](docs/architecture-review-2026-11-15.md): 수정 전 문제와 확장 제안의 근거.
- [작업 계약](.project/plan.md) · [화면 설계](design.md) · [운영 규칙](AGENTS.md): 현재 개발 기준.
- [과거 기록 목록](docs/archive/README.md): Phase 0~10·기획 정리본·선택 기록.
- [공개 작업 기록](https://seo-gali.github.io/sql-plan-visualizer/) · [로컬 HTML](docs/index.html): 2026-11-04~07의 경위·검증 기록.

문서 사이트 진입점: `docs/index.html`. 과거 작업 기록의 주제별 탭과 이전·다음 이동 지원.
흐름도의 HTML/CSS 직접 표시와 인터넷 없는 열람 지원.
선택 기록·샘플 보고서의 `docs` 내부 상대 경로 연결. 문서 HTML의 별도 그림 파일·Mermaid 실행 도구 요구 없음.

GitHub 웹 게시 방법: 저장소 업로드 후 Settings → Pages → Deploy from a branch → 게시할 브랜치와 `/docs` 선택.
`docs/.nojekyll`: 별도 Jekyll 변환 없는 정적 파일 제공.
설정 근거: [GitHub Pages 게시 경로 안내](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site).
