"use strict";
const linked = [...document.querySelectorAll("[data-range]")];
function highlight(target) {
  const range = target instanceof Element ? target.closest("[data-range]")?.dataset.range : null;
  for (const node of linked) node.classList.toggle("active", Boolean(range) && node.dataset.range === range);
}
document.addEventListener("mouseover", event => highlight(event.target));
document.addEventListener("focusin", event => highlight(event.target));
document.addEventListener("mouseout", event => highlight(event.relatedTarget));
document.addEventListener("focusout", event => highlight(event.relatedTarget));
function drawFlow() {
  const diagram = document.getElementById("flow-diagram");
  const svg = document.getElementById("flow-edges");
  const bounds = diagram.getBoundingClientRect();
  svg.replaceChildren();
  for (const node of document.querySelectorAll(".flow-node")) {
    const box = node.getBoundingClientRect();
    for (const input of node.dataset.inputs.split(" ").filter(Boolean)) {
      const source = document.getElementById(input);
      if (!source) continue;
      const from = source.getBoundingClientRect();
      const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
      path.setAttribute("d", `M 42 ${from.top + from.height / 2 - bounds.top} H 18 V ${box.top + box.height / 2 - bounds.top} H 42`);
      path.setAttribute("stroke", "#627d92");
      path.setAttribute("fill", "none");
      svg.append(path);
    }
  }
}
window.addEventListener("resize", drawFlow);
drawFlow();
const korean = {
  "Review hash spilling": "해시 임시 파일 사용 점검",
  "The measured hash used multiple batches and wrote temporary blocks. Review hash input size and per-session memory settings.": "실측 해시 작업의 여러 배치 및 임시 블록 기록 확인. 해시 입력 행 수와 세션별 메모리 설정 점검.",
  "Hash spilling alone does not prove a problem or justify an index or a global memory increase.": "해시 임시 파일 사용만으로 성능 문제 확정 불가. 인덱스 추가·전역 메모리 증설의 단독 근거로 사용 불가.",
  "Compare hash batches, temporary blocks, output rows, and timings in an isolated read-only test session.": "격리된 조회 전용 테스트 세션에서 해시 배치 수·임시 블록·출력 행 수·실행 시간 비교.",
  "Recommendations": "개선 후보",
  "RECOMMENDATION": "RECOMMENDATION · 개선 후보",
  "Review disk sorting": "디스크 정렬 점검",
  "Observed evidence": "관측 근거",
  "Reason": "제안 이유",
  "Conditions": "적용 조건",
  "Limitations": "한계",
  "Verification": "검증 방법",
  "Suggested SQL (text only)": "검증 SQL (텍스트 전용)",
  "The measured sort used disk storage. Review sort input size and per-session work_mem.": "실제 정렬에서 디스크를 사용했습니다. 정렬 입력량과 세션별 work_mem을 점검하세요.",
  "Use a representative workload, preserve result semantics, and account for concurrent queries.": "대표 부하에서 결과 의미를 보존하고 동시 실행 쿼리를 고려해야 합니다.",
  "A disk sort alone does not prove a problem or justify an index or a global memory increase.": "디스크 정렬만으로 문제를 확정하거나 인덱스 추가·전역 메모리 증가를 권고하지 않습니다.",
  "Compare sort space, output rows, buffers, and timings in an isolated read-only test session.": "격리된 조회 전용 테스트 세션에서 정렬 공간, 출력 행 수, 버퍼와 실행 시간을 비교하세요.",
  "RUNTIME": "RUNTIME · 실제 실행",
  "Actual execution time (ms):": "실제 실행 시간(ms):",
  "Runtime mode executed the read-only query; actual metrics are environment-dependent.": "Runtime 모드에서 조회 전용 쿼리를 실제 실행했습니다. 측정값은 실행 환경에 따라 달라집니다.",
  "Database Metadata": "DB 메타데이터",
  "Column": "컬럼",
  "Data type": "데이터 타입",
  "Nullable": "NULL 허용",
  "Null fraction": "NULL 비율",
  "Distinct estimate": "고유값 수 추정",
  "Indexes": "인덱스",
  "No indexes visible.": "조회 가능한 인덱스가 없습니다.",
  "Catalog statistics are estimates and may be stale.": "Catalog 통계는 추정값이며 최신 데이터 분포와 다를 수 있습니다.",
  "Skip to SQL source": "SQL 원문으로 이동",
  "Overview": "개요",
  "References": "참조",
  "SQL Flow nodes": "SQL Flow 노드",
  "SQL Source": "SQL 원문",
  "Reference": "참조",
  "Kind / Alias": "유형 / 별칭",
  "Scope": "범위",
  "Status": "상태",
  "Basis / Candidates": "출처 / 후보",
  "PARSED": "PARSED · 파싱됨",
  "STATIC": "STATIC · 정적 분석",
  "DATABASE": "DATABASE · DB 근거",
  "ESTIMATED": "ESTIMATED · 예상 계획",
  "RESOLVED": "RESOLVED · 연결됨",
  "AMBIGUOUS": "AMBIGUOUS · 후보가 여러 개",
  "UNRESOLVED": "UNRESOLVED · 확인 불가",
  "PARSED does not establish database executability or object existence.": "파싱 성공은 DB 실행 가능성이나 객체의 존재를 보증하지 않습니다.",
  "SQL Flow describes SQL structure, not the DBMS execution order.": "SQL Flow는 SQL 구조를 나타냅니다. 실제 DBMS 실행 순서는 실행 계획에서 확인합니다.",
  "Source mapping covers parser-provided token ranges only.": "원문 연결은 파서가 제공한 토큰 위치에만 적용됩니다.",
  "Hover or focus a token to highlight its references and tree nodes.": "토큰에 마우스를 올리거나 키보드로 이동하면 연결된 참조와 트리 노드가 강조됩니다.",
  "Source binding status; database object existence is not checked in static mode.": "SQL 원문에서의 연결 상태입니다. 정적 분석만으로 DB 객체의 존재를 확인하지 않습니다.",
  "No explicit table or column references.": "명시적인 테이블 또는 컬럼 참조가 없습니다.",
  "SQL structure · STATIC · This is not a database execution plan.": "SQL 구조 · STATIC · DB 실행 계획과 구분해 표시합니다.",
  "Scan": "Scan · 테이블 참조",
  "Project": "Project · 출력 컬럼",
  "Filter": "Filter · 필터",
  "Join": "Join · 조인",
  "Aggregate": "Aggregate · 집계",
  "Sort": "Sort · 정렬",
  "Distinct": "Distinct · 중복 제거",
  "Limit": "Limit · 행 수 제한",
  "Offset": "Offset · 시작 위치",
  "CTE": "CTE · 공통 테이블 식",
  "Subquery": "Subquery · 서브쿼리",
  "output": "출력",
  "Inputs:": "입력:",
  "Execution Plan": "실행 계획",
  "Estimated rows:": "예상 행 수:",
  "Cost:": "비용:",
  "SQLPVI · Evidence before assumptions · Input SQL is preserved.": "SQLPVI · 근거를 바탕으로 분석합니다 · 입력 SQL은 변경하지 않습니다."
};
const languagePicker = document.getElementById("language");
function setLanguage(language) {
  const selected = language === "ko" ? "ko" : "en";
  document.documentElement.lang = selected;
  languagePicker.value = selected;
  for (const element of document.querySelectorAll("[data-i18n]")) {
    const original = element.dataset.i18n || element.textContent;
    element.dataset.i18n = original;
    element.textContent = selected === "ko" ? korean[original] || original : original;
  }
  try { localStorage.setItem("sqlpvi-language", selected); } catch { /* Storage may be unavailable for local files. */ }
  drawFlow();
}
let initialLanguage = navigator.language.startsWith("ko") ? "ko" : "en";
try { initialLanguage = localStorage.getItem("sqlpvi-language") || initialLanguage; } catch { /* The picker still works without storage. */ }
languagePicker.addEventListener("change", () => setLanguage(languagePicker.value));
setLanguage(initialLanguage);
