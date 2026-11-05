# Phase 9. Microsoft SQL Server

2026-11-04 기술 Gate 통과. Git 저장소가 없어 Branch/Commit/Push/PR은 수행하지 못했다.

## 구현

사용자 승인으로 `pymssql==2.4.6`과 Lock을 추가했다. 추가 ODBC 설치 없이
`--vendor sqlserver`/`tsql`/`SQLPVI_SQLSERVER_URL`로 Estimated Plan을 수집한다.
수집기는 `src/sqlpvi/db/sqlserver.py`, 입력 모델은 기존 `Report`/`ExecutionPlan`이다.

`SET SHOWPLAN_XML ON`과 OFF는 각각 독립 배치로 실행한다. 입력 Query는 실행하지 않는다.
SHOWPLAN 단계의 예외에서도 OFF와 Rollback을 시도하고 연결을 닫는다.
SQL Server의 Read-only 접속 의도는 라우팅 힌트이므로 쓰기 방지는 실제 최소 권한,
Statement/함수/테이블 Hint Allowlist 및 SHOWPLAN 미실행으로 적용한다.
Server/Database/Object/Column 유효 권한과 GRANT OPTION을 확인하고 Writer/Admin을 거부한다.
암호화 연결, Login/Query Timeout 5초, Lock Timeout 1초를 사용한다. Runtime은 거부한다.

표준 XML Parser로 Namespace를 확인하고 DTD/Entity 선언 및 Bytes 입력을 거부한다.
단일 SELECT 계획의 Physical/Logical 연산, Rows/Cost, Node ID와 Object/Index 필드를 보존한다.
하위 RelOp를 중복 연결하거나 자식의 Table을 부모의 Table로 추측하지 않는다.
`SELECT WITHOUT QUERY`에는 DB가 제공하지 않은 Rows/Cost를 만들어 넣지 않는다.

## 실제 실행

사용자가 일반 PowerShell에서 Lock/드라이버 설치와 Compose를 실행했다.
SQL Server 2022 Developer `mssql` 서비스와 `sqlserver-init`을 통해 격리 Fixture를 준비했다.
이후 이 셸에서 세 DB에 직접 연결해 검증했다.

```powershell
$env:SQLPVI_TEST_POSTGRES_URL = 'postgresql://sqlpvi_reader@127.0.0.1:55432/sqlpvi'
$env:SQLPVI_TEST_MARIADB_URL = 'mariadb://sqlpvi_reader@127.0.0.1:53306/sqlpvi'
$env:SQLPVI_TEST_SQLSERVER_URL = 'sqlserver://sqlpvi_reader:Sqlpvi-Fixture-2026!@127.0.0.1:14330/sqlpvi'
uv --cache-dir .uv-cache run --no-sync pytest tests -q --basetemp artifacts/pytest-phase9-database -p no:cacheprovider --tb=short
uv --cache-dir .uv-cache --offline lock --check
uv --cache-dir .uv-cache run --no-sync ruff check .
uv --cache-dir .uv-cache run --no-sync ruff format --check .
```

- **185 passed in 18.67s**, exit 0, Skip 없음. SQL Server 실제 통합 테스트 16개 포함.
- SELECT/JOIN/Aggregate/CTE/Subquery SHOWPLAN 확인.
- 나누기 오류 Query는 SHOWPLAN으로 성공하고 실제 실행은 실패해 입력 미실행을 검증했다.
- 성공과 잘못된 Column 오류 후 동일 연결에서 `SELECT 42`가 XML이 아닌 값으로 반환됨을
  확인했다. Collector 종료 후 연결 사용도 거부됨을 확인했다.
- SA, Schema Writer, Column Writer, GRANT OPTION 계정 거부.
- Reader의 실제 쓰기 거부와 데이터 보존, SHOWPLAN 권한 부족/인증/SQL 오류 마스킹 통과.
- 실제 Driver Query Timeout과 Collector Lock Timeout 통과. Lock 검증용 변경은 롤백했다.
- DTD/외부 Entity/잘못된 Namespace/음수·비정상 추정치/다중 Statement/테이블 잠금 Hint 거부.
- 잠금 Hint 검사는 공통 안전 경계에 추가했으며 PostgreSQL/MariaDB 회귀도 통과했다.
- Lock/Ruff check/format 각각 exit 0. 53개 파일의 포맷 확인.

```powershell
$env:SQLPVI_SQLSERVER_URL = 'sqlserver://sqlpvi_reader:Sqlpvi-Fixture-2026!@127.0.0.1:14330/sqlpvi'
uv --cache-dir .uv-cache run --no-sync sqlpvi analyze fixtures/sql/join.sql --vendor sqlserver --database --output artifacts/sqlserver-estimated.html
uv --cache-dir .uv-cache run --no-sync sqlpvi analyze fixtures/sql/join.sql --vendor sqlserver --database --format json --output artifacts/sqlserver-estimated.json
```

각각 exit 0. JSON의 PARSED/tsql/sqlserver/ESTIMATED/DATABASE와 Hash Match,
Clustered Index Scan, Schema/Table/Index를 다시 확인했다. HTML/JSON의 접속 URL/암호
비노출 및 입력 SQL Hash 보존을 확인했다.
브라우저에서 DATABASE 출처, 실제 연산/추정 Rows/PK_orders, SVG 연결선 4개를 확인했다.
외부 Resource 0개, Console Error/Warning 0개였다.

## 실패와 수정

- 이 셸의 PyPI 연결과 DockSlate CLI 권한 제한 때문에 패키지/컨테이너 준비는 사용자가
  일반 PowerShell에서 실행했다. 기존 환경의 `uv sync` 캐시 오류는 남아 있어 `--no-sync` 사용.
- 초기 51433은 Windows 예약 TCP 구간 51356~51455 안에 있었다. 컨테이너가 Healthy여도
  Windows 리스너가 없고 접속이 실패했다. `netsh interface ipv4 show excludedportrange
  protocol=tcp`와 `netstat -ano -p TCP`로 확인했다. 예약 구간을 변경하지 않고 14330으로 수정했다.
- 기존 `sqlpvi-test-sqlserver-1`과 DB를 중지·보존하고 새 `mssql` 컨테이너에서 검증했다.
  DB/Volume 삭제·초기화 및 `--remove-orphans`는 수행하지 않았다.
- 첫 SQL Server 통합 실행에서 상수 SELECT가 `SELECT WITHOUT QUERY`를 반환해 파싱이
  실패했다. 실제 XML 형태를 확인하고 해당 상태를 보존하도록 수정한 뒤 전체 회귀를 통과했다.

SQL Server Runtime과 Catalog Reference 보강은 범위 밖이다. Compose의 공개 암호는
loopback 격리 Fixture 전용이다. XML/접속 안전성을 적용했지만 신뢰된 개발/테스트 DB에서 사용한다.

## 공식 근거

- [SET SHOWPLAN_XML](https://learn.microsoft.com/en-us/sql/t-sql/statements/set-showplan-xml-transact-sql)
- [sys.fn_my_permissions](https://learn.microsoft.com/en-us/sql/relational-databases/system-functions/sys-fn-my-permissions-transact-sql)
- [pymssql 연결/Timeout](https://pymssql.readthedocs.io/en/stable/ref/pymssql.html)
- [SQL Server 컨테이너](https://learn.microsoft.com/en-us/sql/linux/install-upgrade/quickstart-install-docker)
