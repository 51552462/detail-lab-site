# 2026-10-20 PR25 검수 기록

시작 main cd4fe146f5a15efe1c6c9eec04ec81a594d732d3. 이번 변경은 공개 승인 전. [PR25](https://github.com/51552462/detail-lab-site/pull/25).

## 실행과 증거

초기 head4da33ad CI run39358254212,merge3d1656bd:48개 360/1280 경로·오류0·199캡처. 화면 점검에서 business 문의목록 저대비/버튼 붙음/모바일 제목 줄바꿈을 발견했다. 수정 head2843a41eac7f4164e1a0394f363bb4d339a4125e의 CI [39358735447](https://github.com/51552462/detail-lab-site/actions/runs/39358735447) check/customer-flows/synthetic-data 성공. 테스트 merge fb7b376bf89e03d7953e45949d3f90af20fae18f. artifact12236820525 SHA256 ef45107b7a55d4705fe6fef3a52b0d92ec3e4872379a1140584ece4e48fcd023.

합성자료13시험은 로컬+CI통과. 브라우저48흐름은 기존44와 신규홈/서비스4(두폭)이며 모두 실고객 제출이 아닌 합성입력. JS오류0. 초기/최종캡처199개 모두를 직접봤다고 주장하지 않는다.

## 직접 읽은 화면

초기 artifact12236790157의 360/1280-page-index-hero,360/1280-page-business-hero. 모바일 새콘텐츠:360-new-case-away/brand/sales/team-01~02,360-new-data-02,360-new-deliverables-01~03,360-new-home-about-01~02,360-new-home-concerns-01~04,360-new-home-faq-01~02,360-new-home-philosophy-01~02,360-new-home-system-01~03,360-new-market-01~02,360-new-responsibility-01~03. 360-new-contact-01에서저대비 발견.

초기 데스크톱:1280-new-deliverables-01,1280-new-case-sales-01~02,1280-new-case-team-01~02(양옆brand도함께),1280-new-home-philosophy-01,1280-new-home-faq-01. 역할/가설/지표/가상표시·양식구성·줄바꿈을읽음.

기존 여섯도구 대표모바일 결과 전체구간:360-center-01~05,360-store-01~04,360-shift-01~04,360-trainer-01~03,360-employee-record-01~04,360-matching-overlap-01~04. 가상입력/선택근거/다음행동/복사·도구/베타경계가 유지됨을 읽음. trainer의5명이상+기억불가는 기존미완료로기록하며 이번에원본도구동작변경없음.

최종 artifact12236820525:360/1280-page-business-hero,360-new-contact-01~03,1280-new-contact-01. 수정된2줄모바일제목·12px버튼간격·밝은질문목록·복사실패수동양식을 확인. 다른콘텐츠/도구는초기와동일이며 최종CI로회귀.

## 못 한 것

나머지초기/최종캡처,모든질문개별화면,모든매칭분기시각검수,PC여섯결과전체,모바일실기기·카카오인앱·실제인쇄/PDF,Form수신·이메일발송,Render관리LiveSHA,고객이해/사용·유료거래는이번에검증하지않음. 자동통과와사람이읽은범위를구분함.

## 보존과 승인

index/business/areas 외기존10HTML코드·Form·동의·베타조건변경없음. 기존모든로컬URL/앵커정적검사통과. 공개사이트는기존main유지. 일반문서·합성코드만PR에저장,고객원본/연락처/민감파일없음. 공개승인뒤병합·실사이트를별도확인한다.

