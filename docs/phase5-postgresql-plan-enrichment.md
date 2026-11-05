# Phase 5. PostgreSQL Plan Enrichment

2026-11-04 기술 Gate 통과.

Catalog에서 Schema/Column/타입/Nullability/Index 및 null_frac/n_distinct/reltuples를
조회하고 모든 후보의 Catalog 근거가 있을 때만 Column 연결을 보강한다.
Status는 기존 세 종류를 유지하고 Basis만 DATABASE로 구분한다. CTE를 동명 DB Table에
연결하지 않는다. 권한 부족은 Savepoint로 격리하고 Static 결과를 유지한다.
통계가 오래되거나 없을 수 있음을 표시한다.

실제 검증:

- 격리 DB에 alternate Schema, 권한 제한 Table, 미분석 Table Fixture 추가: exit 0.
- 전체 회귀 및 실제 DB 통합 테스트: **76 passed**, exit 0.
- 다중 Source의 name이 단일 후보가 되는 사례, Schema 동명 Table, 권한 부족 시
  Static 유지, 통계 없음, 실제 Index 정의를 확인했다.
- `uv lock --check`, Ruff check/format: 각각 exit 0.
- 실제 CLI로 `artifacts/postgres-enriched.html`/`.json` 생성: exit 0.
- 브라우저에서 Catalog Table 2개, Index, DATABASE Reference 8개와 Plan Filter 확인.

변동 통계값을 Golden Value로 고정하지 않았다. 상관/Derived Scope 등 Catalog와
직접 연결할 근거가 없는 Reference는 Static 상태를 유지한다. 자동 SQL/Schema/Index
변경은 없다. uv 자동 sync와 Git/Remote 제약은 이전 Phase와 같다.
