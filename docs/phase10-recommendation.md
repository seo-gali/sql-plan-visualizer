# Phase 10. Evidence 기반 Recommendation

2026-11-04 기술 Gate 통과. Phase 9 Gate 통과 후 구현했다.
Git 저장소가 없어 Branch/Commit/Push/PR과 사용자 Merge는 수행하지 못했다.

이 문서의 수치·구현 범위: 2026-11-04 당시 기록.
현재 후속 변경: [2026-11-05 출력·힌트·해시 개선 기록](code-improvements-2026-11-05.md).

## 구현과 범위

`src/sqlpvi/recommend.py`의 순수 규칙은 기존 Report를 읽어 후보 목록을 반환한다.
CLI가 수집 완료 후 호출하며 DB/LLM 접속이나 파일 변경을 수행하지 않는다.
현재 규칙은 PostgreSQL Runtime의 실행된 `Sort`에서 디스크 사용을 관측한 경우의
입력량·세션별 `work_mem` 점검 한 가지다. 인덱스 생성·전역 메모리 증가를 단정하지 않는다.

DATABASE/RUNTIME/PostgreSQL 출처, Disk Sort, 유효한 양수 공간/Actual Rows/Loops,
확정된 Column 참조를 모두 요구한다. Estimated/다른 Vendor/불확실 Reference,
미실행/누락/비정상 측정값에서는 후보를 생성하지 않는다. Seq Scan과 높은 Cost/시간을
보편 임계값으로 취급하지 않는다. 여러 Disk Sort는 한 후보의 여러 근거로 묶는다.

각 후보는 `RECOMMENDATION` 출처이며 근거 ID/실제 Plan Node ID/관측 사실,
이유/적용 조건/한계/검증 방법/검증 SQL을 포함한다. SQL은 텍스트로만 제시한다.
근거 링크는 동일 HTML의 실제 실행 계획 노드로 이동한다. 문구는 한/영 전환을 지원한다.

수정 범위: Report의 Evidence/Recommendation 모델, CLI 연결, HTML/언어 사전,
추천 모듈과 단위/통합 테스트. `sort.sql` 및 `sort-spill.sql` Fixture를 추가했다.
신규 의존성과 Lock 변경은 이 Phase에서 없다. 삭제 파일도 없다.

## 실제 검증

```powershell
$env:SQLPVI_TEST_POSTGRES_URL = 'postgresql://sqlpvi_reader@127.0.0.1:55432/sqlpvi'
$env:SQLPVI_TEST_MARIADB_URL = 'mariadb://sqlpvi_reader@127.0.0.1:53306/sqlpvi'
$env:SQLPVI_TEST_SQLSERVER_URL = 'sqlserver://sqlpvi_reader:Sqlpvi-Fixture-2026!@127.0.0.1:14330/sqlpvi'
uv --cache-dir .uv-cache run --no-sync pytest tests -q --basetemp artifacts/pytest-phase10-database -p no:cacheprovider --tb=short
uv --cache-dir .uv-cache --offline lock --check
uv --cache-dir .uv-cache run --no-sync ruff check .
uv --cache-dir .uv-cache run --no-sync ruff format --check .
```

- 전체: **211 passed in 17.71s**, exit 0, Skip 없음. PostgreSQL/MariaDB/SQL Server 실제 회귀 포함.
- 추천 단위/통합: **26 passed**. 실제 PostgreSQL Runtime을 세션 `work_mem=64kB`와
  `8MB`로 비교해 전자의 Disk Sort에서 후보 생성, 후자의 Memory Sort에서 미생성을 확인했다.
  이 값은 테스트 세션만의 설정이며 제품의 자동 변경이나 보편 임계값이 아니다.
- 작은 Table Seq Scan, 높은 Cost/시간의 Memory Sort, 미확정 Reference,
  누락/0/음수/문자열/Bool/NaN/Infinity 근거에서 오권고 방지 확인.
- 각 후보의 근거가 실제 RUNTIME Sort Node를 가리키며 측정값이 존재함을 검증했다.
- 입력 파일/Report 보존과 반복 호출 일관성, JSON 직렬화와 HTML Escape 확인.
- CLI의 DB 수집 연결이 1회이며 제안 SQL을 다시 실행하지 않음을 확인했다.
- 실제 실행 전후 입력 SQL, orders 행 수/합계, public Index 정의가 동일함을 확인했다.
- Lock/Ruff check/format 각각 exit 0. Ruff가 57개 파일의 포맷을 확인했다.

추가 실제 CLI:

```powershell
$env:SQLPVI_POSTGRES_URL = 'postgresql://sqlpvi_reader@127.0.0.1:55432/sqlpvi'
uv --cache-dir .uv-cache run --no-sync sqlpvi analyze fixtures/sql/sort-spill.sql --database --runtime --output artifacts/recommendation.html
uv --cache-dir .uv-cache run --no-sync sqlpvi analyze fixtures/sql/sort-spill.sql --database --runtime --format json --output artifacts/recommendation.json
```

각각 exit 0. 입력 Hash 보존 확인. 이 Fixture는 조회 전용 Cross Join으로 10만 행을
정렬하며 실제 `Sort Space Type=Disk`, `Sort Space Used=2552`, Actual Rows=100000,
Actual Loops=1을 관측했다. 이 수치는 Golden/임계값이 아닌 해당 실행의 관측 결과다.
`evidence-plan-0`이 실제 `plan-0`을 가리키는 후보 1개가 생성됐다.

브라우저에서 RECOMMENDATION/DATABASE 구분, 조건/한계/검증 SQL, 근거 링크 이동,
한/영 전환을 확인했다. 390px 화면에서 페이지 가로 넘침 없이 근거 링크의 키보드 Focus를
확인했다. 외부 Resource 0개, Console Error/Warning 0개, SQL 실행 UI 없음.

## 한계

추천 범위는 실측 PostgreSQL Disk Sort 점검 규칙에 한정한다. Static-only, Estimated-only,
MariaDB/SQL Server 추천과 자동 SQL/Index 최적화는 구현하지 않았다. 근거가 없는 후보를
만들지 않는 것이 현재 동작이다. Runtime도 사용자의 `--database --runtime` 지정에서만 실행한다.
증거가 있어도 성능 문제나 개선 효과를 확정하지 않으며 대표 부하/동시성을 포함한 검증이 필요하다.

uv 캐시/일반 sync와 DockSlate CLI 접근 제약, 중지·보존한 이전 SQL Server 컨테이너는
Phase 9 기록과 같다. 임시 HTTP 서버는 브라우저 검증 종료 후 정리한다.

## 근거

- [PostgreSQL EXPLAIN의 정렬 관측 정보](https://www.postgresql.org/docs/18/using-explain.html)
- [work_mem과 동시 작업의 메모리 사용](https://www.postgresql.org/docs/18/runtime-config-resource.html)
