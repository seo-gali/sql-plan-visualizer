# 출력·힌트·해시 개선 기록

2026-11-05 검증 결과: **258 passed in 18.89s**, Skip 없음, exit 0.
실제 PostgreSQL·MariaDB·SQL Server 통합 검사의 포함.
2026-11-04의 Phase 완료 수치와 구분한 후속 변경 기록.

## 변경 동작

| 변경 | 이전 | 현재 |
| --- | --- | --- |
| 새 출력 폴더 | 파일 저장 실패 | 분석 성공 후 부모 폴더 자동 생성 |
| SQL Server Table Hint | 종류와 무관한 거부 | 인자 없는 읽기·접근 경로 Hint 4종 허용 |
| PostgreSQL 추천 | 디스크 정렬 1종 | 디스크 정렬·해시 임시 파일 2종 |

```mermaid
flowchart LR
    Input["SQL 원문 보존"] --> Guard["SQL·권한 검사"]
    Guard --> Plan["실행 계획 수집"]
    Plan --> Evidence{"PostgreSQL 실측 근거"}
    Evidence -->|"디스크 정렬"|Sort["정렬 입력량·메모리 점검"]
    Evidence -->|"여러 해시 배치 + 임시 블록"|Hash["해시 입력량·메모리 점검"]
    Sort --> Output["새 폴더 생성 후 HTML·JSON 저장"]
    Hash --> Output
    Evidence -->|"근거 부족·다른 모드"|Output
    Input -->|"기본 정적 분석"|Output
```

정적 분석: DB 수집 없이 출력 경로의 자동 생성 지원.
추천: 수집된 계획만 사용. 추천 목적의 추가 DB 접속·SQL 실행 없음.

## 허용 범위와 근거

SQL Server 허용 목록: `NOLOCK`, `READUNCOMMITTED`, `FORCESEEK`, `FORCESCAN`.
인자 없는 형태만 허용. 원문에 있는 Hint의 보존과 SHOWPLAN 계획 수집.
`UPDLOCK` 등 잠금 강제 Hint, 알 수 없는 Hint, `INDEX(...)` 등 인자 있는 Hint의 거부.
Hint의 자동 삽입 없음. `NOLOCK`의 결과 일관성·스키마 잠금 부재 보장 없음.

해시 후보 조건: PostgreSQL·`DATABASE`·`RUNTIME`·확정된 Column 참조.
추가 조건: 실제 `Hash` 노드, `Hash Batches>1`, 양수 `Temp Written Blocks`, 양수 Actual Rows·Loops.
Bool·문자열·NaN·Infinity·누락값의 근거 사용 금지.
여러 관측 노드의 동일 종류 후보로의 묶음. 근거별 실제 계획 노드 링크.
성능 문제 확정·인덱스 추가·전역 메모리 증설의 자동 권고 제외.

근거: [PostgreSQL의 해시 배치·디스크 사용 설명](https://www.postgresql.org/docs/18/using-explain.html),
[Microsoft의 Table Hint 설명](https://learn.microsoft.com/en-us/sql/t-sql/queries/hints-transact-sql-table?view=sql-server-ver17).

## 실제 검증

변경 전 관련 검사: **9 failed, 102 passed**, exit 1.
재현 항목: 새 출력 폴더 2건, 허용 Hint 5건, 해시 추천 2건.
변경 후 동일 검사: **111 passed**, exit 0.

```powershell
$env:SQLPVI_TEST_POSTGRES_URL = 'postgresql://sqlpvi_reader@127.0.0.1:55432/sqlpvi'
$env:SQLPVI_TEST_MARIADB_URL = 'mariadb://sqlpvi_reader@127.0.0.1:53306/sqlpvi'
$env:SQLPVI_TEST_SQLSERVER_URL = 'sqlserver://sqlpvi_reader:Sqlpvi-Fixture-2026!@127.0.0.1:14330/sqlpvi'
uv --cache-dir .uv-cache run --no-sync pytest tests -q --basetemp artifacts/pytest-code-improvements-20261105 -p no:cacheprovider --tb=short
uv --cache-dir .uv-cache --offline lock --check
```

| 검사 | 실제 결과 |
| --- | --- |
| 전체 pytest | 258 passed, Skip 없음, exit 0 |
| Ruff check | All checks passed, exit 0 |
| Ruff format --check | 58 files already formatted, exit 0 |
| Offline Lock 검사 | 16 packages, exit 0. 파일 갱신 없음 |
| 입력 보존 | 기존 Hardlink 덮어쓰기 거부, 출력 폴더 오류 시 원문 보존 |
| SQL 오류 | 실패한 분석의 출력 폴더 생성 없음 |
| SQL Server 실제 Hint | 허용 4종의 Estimated Plan 수집·Actual Rows 없음 확인 |
| PostgreSQL 실제 해시 | 테스트 세션 64kB에서 후보 생성, 8MB에서 미생성 |
| 데이터·Index | 실측 전후 orders 행 수·합계·public Index 정의 동일 |

해시 시험 조건: 해당 테스트 세션의 `work_mem` 제한과 Merge/Nested Loop Join 비활성화.
제품의 자동 설정 변경 없음. 보편 성능 임계값으로의 사용 금지.
별도 화면 확인용 실측: Hash Batches=8, Temp Written Blocks=31, Actual Rows=10000, Loops=1.
해당 실행의 관측값이며 고정 정답값 아님.

브라우저 확인: 새 해시 후보의 한영 전환, 근거 링크의 실제 노드 이동, 키보드 Focus, SQL 원문 보존.
1366px·390px 화면의 가로 넘침 없음. 외부 Resource·Console Error/Warning 없음.
선택 기록 HTML: 1366×768에서 전체 항목 표시, 390px에서 가로 넘침 없는 세로 탐색.

## 주신 MCP 글과의 구분

비교 기준: 사용자가 제공한 글의 설명. 외부 도구의 현재 전체 기능 평가 제외.

| 항목 | 글의 mcp-server-mysql | 현재 SQLPVI |
| --- | --- | --- |
| 주목적 | AI의 DB 구조 확인·일반 조회 | SQL 파일의 구조·참조·실행 계획 시각화 |
| 연결 방식 | MCP 서버 | CLI·로컬 Skill |
| 실행 결과 | 질문에 대한 조회 결과 | HTML·JSON 분석 보고서 |
| 쓰기 | 글의 설명상 별도 설정으로 허용 | 쓰기 허용 옵션 없음 |
| 개인정보 가림·SSH | 글에서 소개한 기능 | 미구현 |

공통점: 읽기 중심 접근과 DB 권한 경계.
이번 반영: 필요한 조회의 과도한 차단 완화와 실측 근거의 추천 확대.
일반 DB 질의 비서·MCP 서버로의 기능 전환 없음.

## 변경 파일과 한계

구현: `cli.py`, `db/safety.py`, `recommend.py`, `assets/report.js`.
검사: HTML·SQL Server·추천 단위 검사와 SQL Server·추천 통합 검사.
Fixture 추가: `fixtures/sql/hash-spill.sql`. 삭제 파일·신규 의존성·버전·Lock 변경 없음.
현재 안내: README·기획서·Phase 10 지침. 과거 Phase 10 기록의 수치 보존.
최종 재검토의 추가 수정: README의 옛 SQL Server ‘중지 상태’ 단정 제거. 사용자의 재기동 화면 반영.

코드 개선 당시 미해결: Windows uv 신규 설치 권한 오류, Mermaid 실제 렌더링, Claude Code 실제 호출.
후속 확인 당시 문서 그림 10개의 실제 렌더링·SVG 연결 완료. 이후 사용자 요청에 따른 별도 SVG 삭제와 Markdown Mermaid 직접 표시로 전환.
uv 신규 설치는 미완료.
시도별 명령·결과·경위: [문서 첫 화면](index.html).
Git 저장소·Remote 부재에 따른 Push·PR 미수행.
대신 내린 선택: [한 화면 HTML 기록](sqlpvi-decisions-2026-11-05.html).
