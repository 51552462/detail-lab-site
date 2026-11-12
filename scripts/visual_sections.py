"""Customer-facing explanatory visuals. No customer data or performance figures."""
from html import escape

CASES = [
    dict(key='decisions', label='대표에게 몰리는 결정', title='대표가 없는 날, 예약 변경 한 건이 멈춘다면.',
         goal='담당자가 처리할 일과 대표가 확인할 예외를 구분합니다.',
         before='예약을 바꿔달라는 요청이 들어오면 담당자가 매번 대표에게 확인하는 상황을 가정합니다.',
         make='예약 변경의 처리 범위·승인 예외·고객 안내를 한 장에 정리합니다.',
         check='대표에게 물어본 이유, 미처리와 잘못된 안내, 처리표의 실제 사용을 함께 봅니다.',
         metrics=[('확인 요청','어떤 결정이 모였나요?','일상 처리와 대표 승인이 필요한 예외를 구분'),('처리 누락','끝나지 않은 일은 없나요?','연락이 줄어도 미처리·고객 혼선이 늘면 재검토'),('기준 사용','담당자가 실제로 썼나요?','문서 전달과 현장에서 사용한 기록을 구분')],
         rows=[('처리 가능한 요청','현장 담당','직접 처리할 범위 정리'),('기준 밖 요청','대표·책임자','확인할 예외 합의'),('남은 안내와 약속','다음 담당','인계할 기록 정리')],
         decision='확인 연락이 줄었다는 이유만으로 성공으로 보지 않습니다. 고객 안내가 끝났고 담당자가 기준을 쓸 수 있었는지까지 살핍니다.'),
    dict(key='questions', label='반복되는 고객 문의', title='같은 설명을 반복하는 이유부터 살핍니다.',
         goal='고객이 필요한 안내를 찾고, 담당자도 같은 기준으로 답하도록 정리합니다.',
         before='이용 방법을 안내했는데 고객이 다시 묻거나 담당자마다 답이 다른 상황을 가정합니다.',
         make='반복 질문 한 종류의 안내 문장·보여줄 위치·답변 기준을 정리합니다.',
         check='같은 문의의 재발, 안내를 본 고객의 이해, 다른 안내와의 충돌을 확인합니다.',
         metrics=[('재문의','어떤 설명을 다시 묻나요?','같은 문의의 기준과 발생 기간을 맞춰 기록'),('안내 일치','말과 문서가 같나요?','담당자 답변·메뉴·안내문 버전을 대조'),('고객 이해','다음 행동을 알았나요?','문의가 줄어도 포기·오해가 늘었는지 함께 확인')],
         rows=[('반복 질문 한 종류','대표·담당자','실제 질문 장면 모으기'),('안내 문장과 위치','디테일랩·대표','제공 내용과 조건 대조'),('사용 후 반응','현장 담당','고객의 이해와 불편 기록')],
         decision='문의가 줄어든 이유가 안내 개선인지, 방문 감소나 문의 포기인지 구분합니다. 같은 조건의 기록으로 다시 판단합니다.'),
    dict(key='handover', label='업무 분담과 인수인계', title='다음 사람이 다시 묻지 않아도 이어갈 수 있도록.',
         goal='누가 맡고, 어디까지 끝내고, 무엇을 넘길지 같은 기준으로 정합니다.',
         before='담당이 바뀌면 고객에게 한 약속이나 남은 업무를 다시 확인해야 하는 상황을 가정합니다.',
         make='한 업무의 담당·완료 기준·남은 약속·인계 위치를 정리합니다.',
         check='빠진 정보, 재작업, 실제 인계표 사용과 새로 생긴 작성 부담을 확인합니다.',
         metrics=[('인계 누락','무엇이 빠졌나요?','다음 담당자가 필요했던 정보와 전달 내용을 대조'),('재작업','같은 일을 다시 했나요?','업무량 변화와 인계 문제로 생긴 재작업을 구분'),('현장 부담','계속 사용할 수 있나요?','찾는 시간·중복 입력·기록할 항목을 함께 점검')],
         rows=[('요청과 담당','현재 담당','누가 맡는지 표시'),('완료와 남은 약속','인계 담당','끝난 일과 남은 일 분리'),('다음 확인','다음 담당','인계받은 내용과 실제 처리 대조')],
         decision='누락이 줄어도 기록 시간이 과도하게 늘면 항목과 전달 방식을 고칩니다. 기존에 잘되는 인계 방식은 유지합니다.')
]

def impact_section():
    tabs=[];panels=[]
    for i,c in enumerate(CASES):
        k=c['key'];active=i==0
        tabs.append(f'<button type="button" role="tab" id="impact-tab-{k}" aria-controls="impact-panel-{k}" aria-selected="{str(active).lower()}" tabindex="{0 if active else -1}" data-impact-tab>{escape(c["label"])}</button>')
        metrics=''.join(f'<div class="iv-metric"><span class="iv-metric-label">{escape(a)}</span><strong>{escape(b)}</strong><p>{escape(d)}</p></div>' for a,b,d in c['metrics'])
        rows=''.join(f'<div class="iv-record"><span>{escape(a)}</span><span>{escape(b)}</span><span>{escape(d)}</span></div>' for a,b,d in c['rows'])
        hidden='' if active else ' hidden'
        panels.append(f'''<div class="iv-panel" id="impact-panel-{k}" role="tabpanel" aria-labelledby="impact-tab-{k}" tabindex="0"{hidden}>
          <div class="iv-panel-heading"><div><p class="iv-eyebrow">이번에 함께 정할 목표</p><h3>{escape(c['title'])}</h3><p>{escape(c['goal'])}</p></div><span class="iv-status">목표·범위 합의</span></div>
          <div class="iv-story"><div><span>01 / 현재 장면</span><p>{escape(c['before'])}</p></div><div><span>02 / 함께 만들 자료</span><p>{escape(c['make'])}</p></div><div><span>03 / 적용 후 확인</span><p>{escape(c['check'])}</p></div></div>
          <div class="iv-subhead"><h4>어떤 영향을 함께 볼까요?</h4><span>실제 고객 자료를 받기 전에는 수치를 채우지 않습니다.</span></div>
          <div class="iv-metrics">{metrics}</div>
          <div class="iv-records" role="group" aria-label="업무와 기록의 구성 예시"><div class="iv-record iv-record-header"><span>확인할 일</span><span>참여 역할</span><span>남길 기준과 기록</span></div>{rows}</div>
          <div class="iv-decision"><span>다음 판단</span><p>{escape(c['decision'])}</p></div>
        </div>''')
    return '''<section class="ed-section iv-section" id="impact"><p class="ed-kicker">FROM WORK TO EVIDENCE</p><div class="ed-heading"><h2>무엇이 달라졌는지,<br>함께 볼 기록을 만듭니다.</h2><p>만든 문서가 실제 쓰였는지, 어떤 일이 달라졌는지 살핍니다. 아래에서 고민을 고르면 함께 만들 자료와 확인할 기록을 볼 수 있습니다.</p></div><div class="iv-dashboard"><div class="iv-dashboard-top"><div><span class="iv-logo">DL</span><span>운영 기록 미리보기</span></div><span class="iv-example">화면 구성 예시 · 가상 상황</span></div><div class="iv-tabs" role="tablist" aria-label="살펴볼 운영 고민">'''+''.join(tabs)+'''</div>'''+''.join(panels)+'''<div class="iv-dashboard-foot"><span>상황 이해 → 기준 정리 → 실제 사용 → 다음 판단</span><a href="/outputs.html">보고서에서는 어떻게 정리하나요? ↗</a></div></div><p class="ed-small iv-disclosure">가상 상황으로 설명한 결과물 구성 예시입니다. 실제 고객 성과나 고객용 시스템의 운영 화면이 아닙니다. 현재 홈페이지는 고객 자료를 자동 수집하거나 분석하지 않습니다.</p></section>'''

def direction_section():
    return '''<section class="ed-section iv-direction" id="direction"><p class="ed-kicker">PEOPLE, WORK & RECORDS</p><div class="ed-heading"><h2>함께 만든 방식이,<br>그 사업장의 일로 남도록.</h2><p>디테일랩이 지향하는 것은 운영자가 자신의 사업을 더 잘 이해하고, 필요한 일을 계속 이어갈 수 있는 상태입니다. 목표는 대표와 함께 정합니다.</p></div><div class="iv-direction-grid"><figure class="iv-cycle"><img src="/assets/operating-cycle.svg" width="620" height="520" loading="lazy" alt="대표와 목표를 정하고, 업무 기준을 만들어 실제로 사용한 뒤 기록을 다시 확인하는 순환 구조"><figcaption>사람과 현장을 이해하는 일, 다음 판단에 쓸 기록을 남기는 일을 연결합니다.</figcaption></figure><div class="iv-model"><article><span>01 / 운영 실행·개선 파트너</span><h3>현장에서 쓸 방식을 함께 만듭니다.</h3><p>운영자의 이야기를 듣고, 이번 목표와 맡길 일을 정합니다. 필요한 안내·역할·인계 기준을 실제 사용하는 장면에 맞춰 정리합니다.</p></article><article><span>02 / 운영 데이터·시스템 기반</span><h3>실제로 쓰인 방식과 반응을 남깁니다.</h3><p>상황·자료 출처·실행·수정 이력을 연결해 다음 점검에 사용합니다. 반복되는 업무의 도구화와 자동화는 수요와 자료 처리 조건을 확인해 확장합니다.</p></article><p class="iv-model-note">베타는 한 가지 운영 문제와 정해진 결과물에 집중합니다. 정기 데이터 관리·고객 계정·자동 업로드는 별도로 준비할 범위입니다.</p></div></div><figure class="iv-goals"><picture><source media="(max-width:600px)" srcset="/assets/operating-goals-mobile.svg"><img src="/assets/operating-goals.svg" width="1180" height="360" loading="lazy" alt="함께 정할 운영 목표의 예시: 대표에게 몰리는 결정을 나누고, 고객에게 안내가 일치하며, 담당이 바뀌어도 일이 이어지는 모습"></picture><figcaption>대표의 시간·고객의 이해·업무의 연속성은 함께 정할 수 있는 목표의 예시입니다. 결과를 보장하는 성과 수치가 아닙니다.</figcaption></figure><div class="iv-next"><p>우리 사업장에서는 어떤 변화를 먼저 볼까요?</p><a class="ed-button" href="/beta.html">운영 점검 무료 베타 살펴보기 ↗</a></div></section>'''

def compact_visual():
    return '''<figure class="iv-service-visual"><img src="/assets/operating-cycle.svg" width="620" height="520" loading="lazy" alt="상황 이해, 목표와 업무 기준, 현장 사용, 기록과 재점검을 연결하는 디테일랩의 작업 구조"><figcaption>합의한 일 → 실제 사용 → 남은 기록 → 다음 판단</figcaption></figure><p><a class="ed-link" href="/#impact">고민별로 함께 볼 운영 기록 살펴보기 →</a></p>'''
