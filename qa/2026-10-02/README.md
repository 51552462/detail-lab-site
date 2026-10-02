# 2026-10-02 독립 고객 흐름 검수

검수자: ChatGPT. Claude PR #9의 자기 보고를 소급해서 증명하는 문서가 아니다.

## 기준과 실제 실행

- 고객 화면 기준 SHA: `ff0a239711440e4463e149d1b2ae073a8f0511f4`.
- [이 SHA의 CI](https://github.com/51552462/detail-lab-site/actions/runs/36965462598): `check`, `customer-flows` 모두 성공.
- 독립 로컬 실행: 2026-10-02 13:39 KST, 360×800·1280×800. 실제 버튼·입력과 Chromium 클립보드를 사용해 22개 경로 통과, JS 오류 0건. 실행 기록과 여섯 HTML SHA-256은 [execution-report.json](execution-report.json)에 있다.
- 검증용 가상 입력만 사용했다. 신청·의견 제출, 실고객·유료 거래는 수행하지 않았다.
- 생성 기록의 `visualReview`는 스크립트가 화면을 읽지 않았다는 의미다. 아래는 별도로 이미지 파일을 실제 열어 읽은 기록이다.

## 입력 → 결과 → 복사

| 도구 | 직접 검증한 경로 | 실제 결과 관찰 |
|---|---|---|
| 센터 12문 | 첫째/마지막 답, 이전 답 유지·변경 | 결과의 12개 질문·답을 복사문에서 확인, 답 분기에 따라 복사문 달라짐 |
| 가게 12문 | 첫째/마지막 답, 이전 답 유지·변경 | 대표 개입 확인 카드·12개 답·다음 행동·복사 확인 |
| 교대 12문 | 첫째/마지막 답, 이전 답 유지·변경 | 교대 전달 확인 카드·12개 답·복사 확인 |
| 트레이너 12문 | 첫째/마지막 답, 이전 답 유지·변경 | 답 정리·다음 질문·12개 답·복사 확인 |
| 직장 선택 기록 | 빈 입력, 면접 전, A, A·B, B 끄기 | 들은 말과 문서 확인 구분, 화면 요약과 복사문 완전 일치, B 끄면 결과·복사에서 B 제거 |
| 수업 조건 대조 | 두 역할 7문, 빈 복수 선택, 이전 답, 동의 전 차단, 겹침/안 겹침 | 수요일·저녁 겹침과 조율 필요 분기, 여섯 대조 항목·복사문 일치 |

가로 넘침은 두 폭의 각 결과에서 없었다. 모든 입력·표시·복사 기록은 [copies](copies/)에 보존했다. DOM trace와 원본 PNG는 SHA별 CI artifact에 30일 보존된다.

## 실제 열린 결과 캡처

42개 원본 결과 구간을 읽을 수 있는 21개 연락 시트로 묶어 모두 열어 읽었다. 모바일은 원래 폭 그대로, 데스크톱 점검 화면은 결과가 들어 있는 중앙 660px만 잘랐고 직원 기록은 전체 폭을 유지했다. 축소로 글자를 읽을 수 없다는 문제를 피했다. 아래 파일과 원본 구간의 대응·파일 해시는 [screen-manifest.json](screen-manifest.json)에 있다.

- 센터: 리더십·의사결정 카드, 근거 펼침, 함께 확인할 것, 12개 질문·답, 신청·복사·다시 시작을 읽었다.
- 가게: 대표 개입 카드, 근거, 실제 직원과 확인할 내용, 12개 답과 복사·다음 행동을 읽었다.
- 교대: 교대 전달 카드, 근거, 담당자가 쓸 내용, 12개 답과 복사·다음 행동을 읽었다.
- 트레이너: 급여·정산 확인 주제, 확인 상대, 다음 질문, 12개 답을 읽었다. 질문/답의 글자 위계를 확인했다.
- 직원 기록: 요약 첫 줄부터 여섯 조건, A 문서 확인 1·들은 말 0·빈칸 5 / B 문서 확인 0·들은 말 1·빈칸 5, 여섯 후속 질문, 직접 쓴 질문·조건·다음 행동, 의견 링크를 끝까지 읽었다. 수정 후 요약 제목은 고정 메뉴 아래에 보인다.
- 대조: 겹침과 안 겹침 두 결과를 모두 읽었다. 겹침은 “겹치는 요일은 수요일”, 안 겹침은 “겹치는 요일이나 시간대가 없습니다”이며 실제 예약을 다시 확인하도록 안내한다. 복사·인쇄·초기화 버튼도 보인다.

- [360-center-01.webp](screens/360-center-01.webp) — 360-center-01.png, 360-center-02.png, 360-center-03.png
- [360-center-04.webp](screens/360-center-04.webp) — 360-center-04.png
- [360-store-01.webp](screens/360-store-01.webp) — 360-store-01.png, 360-store-02.png, 360-store-03.png
- [360-shift-01.webp](screens/360-shift-01.webp) — 360-shift-01.png, 360-shift-02.png, 360-shift-03.png
- [360-trainer-01.webp](screens/360-trainer-01.webp) — 360-trainer-01.png, 360-trainer-02.png, 360-trainer-03.png
- [360-employee-record-01.webp](screens/360-employee-record-01.webp) — 360-employee-record-01.png, 360-employee-record-02.png, 360-employee-record-03.png
- [360-matching-overlap-01.webp](screens/360-matching-overlap-01.webp) — 360-matching-overlap-01.png, 360-matching-overlap-02.png, 360-matching-overlap-03.png
- [360-matching-no-overlap-01.webp](screens/360-matching-no-overlap-01.webp) — 360-matching-no-overlap-01.png, 360-matching-no-overlap-02.png, 360-matching-no-overlap-03.png
- [1280-center-01.webp](screens/1280-center-01.webp) — 1280-center-01.png, 1280-center-02.png
- [1280-center-03.webp](screens/1280-center-03.webp) — 1280-center-03.png
- [1280-store-01.webp](screens/1280-store-01.webp) — 1280-store-01.png, 1280-store-02.png
- [1280-store-03.webp](screens/1280-store-03.webp) — 1280-store-03.png
- [1280-shift-01.webp](screens/1280-shift-01.webp) — 1280-shift-01.png, 1280-shift-02.png
- [1280-shift-03.webp](screens/1280-shift-03.webp) — 1280-shift-03.png
- [1280-trainer-01.webp](screens/1280-trainer-01.webp) — 1280-trainer-01.png, 1280-trainer-02.png
- [1280-employee-record-01.webp](screens/1280-employee-record-01.webp) — 1280-employee-record-01.png, 1280-employee-record-02.png
- [1280-employee-record-03.webp](screens/1280-employee-record-03.webp) — 1280-employee-record-03.png
- [1280-matching-overlap-01.webp](screens/1280-matching-overlap-01.webp) — 1280-matching-overlap-01.png, 1280-matching-overlap-02.png
- [1280-matching-overlap-03.webp](screens/1280-matching-overlap-03.webp) — 1280-matching-overlap-03.png
- [1280-matching-no-overlap-01.webp](screens/1280-matching-no-overlap-01.webp) — 1280-matching-no-overlap-01.png, 1280-matching-no-overlap-02.png
- [1280-matching-no-overlap-03.webp](screens/1280-matching-no-overlap-03.webp) — 1280-matching-no-overlap-03.png

## 수정한 고객 문제

직원 기록에서 정리 결과로 이동할 때 제목이 고정 메뉴에 가려지거나 부드러운 이동이 끝나기 전에 결과가 보일 수 있었다. 요약에 `scroll-margin-top:100px`를 주고 결과 이동을 즉시 수행한다. 빈 입력 안내와 정상 결과 두 경로에 동일하게 적용했다. 실제 생성·복사 뒤 요약 상단이 메뉴 하단보다 아래에 있는지 검사한다.

## 확인 범위와 남은 한계

- 이번에 여섯 결과 화면은 두 폭 모두 열었다. 직원 기록지의 결과 구간도 끝까지 열었다. 모든 원본 PNG를 각각 별도 창으로 연 것은 아니며, 위 연락 시트에 포함한 구간을 읽었다.
- 여섯 결과와 입력·복사 이외의 직원 설명 페이지 전체, 모든 입력 조합, 인쇄/PDF 파일 생성, 신청·의견 서버 수신은 이번 검수 범위에 포함되지 않았다.
- Claude PR #9의 원본 실행은 이 브라우저에서 Cloudflare 확인이 반복돼 열람하지 못했다. 실제 예약/API/수동 트리거 구분 및 그 실행이 이미지를 열었는지는 여전히 독립 미확인이다.
- Render 대시보드는 로그인 상태 확인이 필요하다. 이 로컬/CI 결과를 Render Live SHA 증거로 사용하지 않는다.
- 가격·고객 수·매출을 새로 주장하지 않는다.
