# 보안 기준

현재 범위: 로컬 SQL 분석 CLI·Standalone HTML·명시적인 DB 실행 계획 수집.
웹 API·로그인·세션·관리자 경로·파일 업로드·결제 기능의 현재 구현 없음.

## 입력·출력

- SQL 파일의 최대 크기: UTF-8 파일 기준 1MiB. 일반 분석·Watch의 동일 기준.
- SQL·식별자·DB 근거의 HTML Escape. 검증된 Script·Style Hash만 허용하는 CSP.
- 외부 리소스·Form 전송·Base URL 변경의 기본 차단. Referrer 미전송.
- SQL 원본 덮어쓰기·Hardlink 출력 거부. 분석 실패 시 기존 출력 유지.
- 기본 생성 파일 `*.sqlpvi.html`의 Git 제외. 사용자 지정 HTML·JSON 출력의 개별 공개 전 검토 필요.

리포트의 포함 정보: SQL 원문·참조·DB 객체·실행 계획·확보된 Metadata.
자동 개인정보 가림·SQL 리터럴 암호화의 미제공. 민감한 리포트의 공개 저장소·Pages 게시 금지.

## DB 경계

| 대상 | 보호 기준 |
| --- | --- |
| 공통 | 명시적 `--database`, 단일 Query·함수 Allowlist, 최소 권한, Timeout, 접속정보 비노출 |
| PostgreSQL | Read-only Transaction, 관리 Role·쓰기/권한 위임·Schema/DB 생성 권한 검사 |
| 원격 PostgreSQL | `verify-full`, TLS 1.2 이상, 인증서·호스트 이름 검증, 암호화 없는 경로로의 대체 금지 |
| MariaDB | Read-only Transaction·직접 권한 검사·Role 해제·Local Infile 차단 |
| 원격 MariaDB | 시스템 신뢰 저장소 기반 인증서·호스트 검증, TLS 미지원 서버 거부, PyMySQL 1.2.3 이상 실행 시 확인 |
| SQL Server | Loopback 호스트만 허용, 암호화 요구, 권한 검사·SHOWPLAN 미실행 경계·Rollback |
| Watch | 정적 HTML만 허용. DB 실행·JSON과의 결합 거부 |

Loopback 예외: `localhost`·Loopback IP, PostgreSQL의 명시적 Unix Socket.
원격 SQL Server의 차단 사유: 현재 연결 설정에서 인증서 신원 검증을 보장하지 못하는 상태.
PostgreSQL 접속 Service·간접 호스트·원격 Hostaddr: 로컬 예외를 적용하지 않는 보수적 TLS 요구.

Metadata 값의 전달: Driver 매개변수 바인딩 사용.
분석 대상 SQL의 처리: AST 허용 검사 후 계획 명령에 전달. SQL 문장 전체를 값 매개변수로 바꾸는 방식의 제외.
Runtime: PostgreSQL의 명시적 `--database --runtime`에서만 실제 조회 실행.

DB 사용의 기본 범위: 신뢰할 수 있는 Local·Development·Test 환경.
Read-only·허용 검사를 DBMS·View·함수 전체의 격리 보장으로 간주하지 않는 기준.

## Secret·Fixture

실제 접속정보: 코드·리포트 대신 실행 환경에 전달. `.env`의 Git 제외와 `.env.example`의 빈 Key 유지.
접속 URL·Driver 원문 예외·비밀번호의 HTML·오류 출력 금지.

`compose.yaml`·Fixture의 공개 암호, PostgreSQL Trust, MariaDB 무비밀번호 Root:
Loopback 전용 합성 테스트의 의도된 설정. 운영 DB·실제 비밀값에 대한 재사용 금지.
이 설정을 유지한 Compose의 외부·운영 배포 금지.

유출 확인 시 순서: 발급처에서 키 폐기 → 최소 권한의 새 키 발급 → 환경에 반영 → 이전 키 거부 확인.
파일에서 문자열을 지우는 작업만으로 폐기 완료를 판정하지 않는 기준.
Git 히스토리 재작성·운영 계정 변경의 별도 사용자 승인 경계 유지.

## 검증·공개 문서 관리

```powershell
.\.venv\Scripts\python.exe -m pytest tests -m 'not integration' -q
.\.venv\Scripts\python.exe -m ruff check src tests tools
.\.venv\Scripts\python.exe tools/update_html_csp.py
```

공개 HTML의 JS·CSS 수정 후 CSP Hash 갱신과 브라우저 동작 확인 필요.
Hash 갱신 도구의 대상: 검토된 저장소의 `docs` HTML. 다운로드한 미검토 HTML의 허용 목록 생성 용도로 사용 금지.

별도 검증: 실제 DB 권한·TLS·Timeout 통합 검사, 최신 Advisory 조회, 컨테이너·Runtime 취약점 검사.
GitHub Pages의 HTTPS 강제·HTTP 보안 헤더·보안 알림: 호스팅 설정의 별도 확인 필요.
CLI 오류 출력을 중앙 보안 관제·운영 모니터링으로 간주하지 않는 기준.

취약점 기록의 포함 항목: 영향 버전·재현 절차·비밀값 없는 최소 Fixture·영향 범위.
공개 Issue·리포트에 실제 토큰·비밀번호·민감한 SQL·접속 URL 기재 금지.

[2026-11-18 보안 점검·수정 보고서](docs/security.html)

[2026-11-21 외부 리소스 무결성 대조](docs/resource-integrity-2026-11-21.md): 패키지 원본·설치 파일과 이미지 digest·Config 비교. 로컬 Layer·Volume 내용의 미검증 구분.
