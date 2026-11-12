"""Customer-facing explanatory visuals. No customer data or performance figures."""
from html import escape

CASES = [{'key': 'judgment',
  'label': '판단이 막힐 때',
  'title': '가격을 낮출지, 설명을 바꿀지 혼자 결정하기 어렵다면.',
  'goal': '고객이 멈춘 지점과 다른 가능성을 살펴, 무엇부터 바꿀지 정합니다.',
  'before': '대표가 직접 상담하지만 구매로 이어지지 않는 문의가 있어, 가격·홍보·안내 중 무엇을 바꿀지 고민하는 상황을 가정합니다.',
  'make': '익명 문의 요약과 현재 안내를 비교하고, 필요한 자료·사례와 선택지의 이유를 정리합니다.',
  'check': '판단할 근거가 생겼는지, 미확인 사항은 무엇인지, 선택한 안내가 실제 사용됐는지 봅니다.',
  'metrics': [('판단 근거', '어떤 이유로 선택했나요?', '대표의 설명·실제 기록·외부 참고 자료를 구분'),
              ('고객 흐름', '고객은 어디에서 멈췄나요?', '문의·안내·구매의 정의와 기간을 맞춰 비교'),
              ('다른 가능성', '우리가 놓친 조건은 없나요?', '유입·상품·영업일 등 다른 설명과 자료의 빈틈도 기록')],
  'rows': [('고민과 지킬 방향', '대표', '최근 장면·기존 시도·원하는 변화'),
           ('자료와 선택지 검토', '디테일랩', '확인 질문·출처·조건·장단점'),
           ('선택과 적용 후 반응', '대표·디테일랩', '선택 이유와 실제 사용, 다음 점검')],
  'decision': '자료를 비교해도 모르는 부분은 남겨둡니다. 구매가 늘거나 줄어도 한 가지 원인으로 단정하지 않고, 다음에 확인할 내용을 정합니다.'},
 {'key': 'execution',
  'label': '실행이 밀릴 때',
  'title': '생각해 둔 개선이, 오늘도 급한 일에 밀렸다면.',
  'goal': '이번에 할 일과 나눠 맡을 일을 좁혀, 실제 사용할 자료로 옮깁니다.',
  'before': '고객 안내를 고치고 싶지만 찾아볼 자료가 쌓여 있고, 당장 해야 하는 일 때문에 미루는 상황을 가정합니다.',
  'make': '확인할 질문과 필요한 조사 범위를 정리합니다. 대표가 선택한 방향에 맞춰 안내 한 장과 사용 순서를 만듭니다.',
  'check': '약속한 자료를 완성했는지와 실제 썼는지를 구분하고, 쓰지 못했다면 이유를 듣습니다.',
  'metrics': [('진행', '다음에 누가 무엇을 하나요?', '조사·대표 결정·제작·적용의 담당과 다음 날짜 기록'),
              ('실제 사용', '만든 자료를 꺼내 썼나요?', '전달한 파일과 실제 사용한 버전·장면을 구분'),
              ('현장 부담', '일이 더 복잡해지지 않았나요?', '설명·찾기·중복 입력 등 새로 생긴 부담도 확인')],
  'rows': [('맡길 일과 범위', '대표·디테일랩', '이번 결과물·일정·완료 기준'),
           ('조사와 자료 제작', '디테일랩', '검토 내용·초안·합의한 수정'),
           ('적용과 반응 확인', '대표·실제 사용자', '사용·미사용 이유와 고객 반응')],
  'decision': '자료를 보냈다는 이유만으로 끝내지 않습니다. 시간·권한·설명·도구 중 어디에서 실행이 멈췄는지 보고, 합의한 범위에서 수정할 일을 정합니다.'},
 {'key': 'strengths',
  'label': '강점을 전하고 싶을 때',
  'title': '대표가 공들이는 일이, 고객에게는 잘 보이지 않는다면.',
  'goal': '지키고 싶은 방식과 실제 제공 가치를 고객이 이해할 수 있게 정리합니다.',
  'before': '서비스에 들이는 정성과 방식은 있는데 소개글에는 가격과 시설만 남아 있는 상황을 가정합니다.',
  'make': '대표가 중요하게 보는 과정, 실제 제공 내용, 고객의 선택 이유를 비교해 한 상품의 설명과 제공 조건을 다듬습니다.',
  'check': '고객이 어떤 차이를 이해했는지, 기대와 실제 제공이 맞는지, 대표도 자연스럽게 설명할 수 있는지 봅니다.',
  'metrics': [('실제 근거', '무엇을 다르게 하고 있나요?', '좋다는 표현 대신 제공 과정과 구체적인 장면을 확인'),
              ('고객 이해', '고객은 어떤 말로 이해했나요?', '고객의 설명·반복 질문·잘못된 기대를 기록'),
              ('사업의 색깔', '대표가 지키려는 방식인가요?', '운영 여건·실제 제공 범위·원하는 방향과 대조')],
  'rows': [('지키고 싶은 가치', '대표', '공들이는 과정·이유·고객 경험'),
           ('현재 표현과 참고 자료', '디테일랩', '소개·상담 문구·고객 반응 비교'),
           ('새 안내의 적용', '대표·디테일랩', '승인한 설명·버전·사용 후 반응')],
  'decision': '보기 좋은 문구라도 실제 제공과 다르면 고칩니다. 대표가 중요하게 보는 점을 고객도 가치 있게 느끼는지는 반응으로 다시 확인합니다.'},
 {'key': 'decisions',
  'label': '대표에게 몰리는 결정',
  'title': '대표가 없는 날, 예약 변경 한 건이 멈춘다면.',
  'goal': '담당자가 처리할 일과 대표가 확인할 예외를 구분합니다.',
  'before': '예약을 바꿔달라는 요청이 들어오면 담당자가 매번 대표에게 확인하는 상황을 가정합니다.',
  'make': '예약 변경의 처리 범위·승인 예외·고객 안내를 한 장에 정리합니다.',
  'check': '대표에게 물어본 이유, 미처리와 잘못된 안내, 처리표의 실제 사용을 함께 봅니다.',
  'metrics': [('확인 요청', '어떤 결정이 모였나요?', '일상 처리와 대표 승인이 필요한 예외를 구분'),
              ('처리 누락', '끝나지 않은 일은 없나요?', '연락이 줄어도 미처리·고객 혼선이 늘면 재검토'),
              ('기준 사용', '담당자가 실제로 썼나요?', '문서 전달과 현장에서 사용한 기록을 구분')],
  'rows': [('처리 가능한 요청', '현장 담당', '직접 처리할 범위 정리'), ('기준 밖 요청', '대표·책임자', '확인할 예외 합의'), ('남은 안내와 약속', '다음 담당', '인계할 기록 정리')],
  'decision': '확인 연락이 줄었다는 이유만으로 성공으로 보지 않습니다. 고객 안내가 끝났고 담당자가 기준을 쓸 수 있었는지까지 살핍니다.'}]

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
    return '''<section class="ed-section iv-section" id="impact"><p class="ed-kicker">FROM WORK TO EVIDENCE</p><div class="ed-heading"><h2>무엇이 달라졌는지,<br>함께 볼 기록을 만듭니다.</h2><p>판단이 막힐 때, 실행이 밀릴 때, 좋은 점을 전하고 싶을 때. 아래에서 고민을 고르면 디테일랩과 나눠 맡을 일, 남길 자료와 확인할 반응이 보입니다.</p></div><div class="iv-dashboard"><div class="iv-dashboard-top"><div><span class="iv-logo">DL</span><span>운영 기록 미리보기</span></div><span class="iv-example">화면 구성 예시 · 가상 상황</span></div><div class="iv-tabs" role="tablist" aria-label="살펴볼 운영 고민">'''+''.join(tabs)+'''</div>'''+''.join(panels)+'''<div class="iv-dashboard-foot"><span>고민 정리 → 조사와 선택 → 적용 → 반응과 다음 판단</span><a href="/outputs.html">보고서에서는 어떻게 정리하나요? ↗</a></div></div><p class="ed-small iv-disclosure">가상 상황으로 설명한 결과물 구성 예시입니다. 실제 고객 성과나 고객용 시스템의 운영 화면이 아닙니다. 현재 홈페이지는 고객 자료를 자동 수집하거나 분석하지 않습니다.</p></section>'''

def direction_section():
    return '''<section class="ed-section iv-direction" id="direction"><p class="ed-kicker">PEOPLE, WORK & RECORDS</p><div class="ed-heading"><h2>한 번 나눈 고민이,<br>다음 판단의 밑바탕이 되도록.</h2><p>대표가 사업을 이끄는 곁에서, 생각을 정리하고 필요한 일을 나눠 맡습니다. 그때의 판단과 실제 반응을 남겨 다음 고민에도 꺼내 볼 수 있게 합니다.</p></div><div class="iv-direction-grid"><figure class="iv-cycle"><img src="/assets/operating-cycle.svg" width="620" height="520" loading="lazy" alt="대표의 고민을 듣고 조사와 비교로 선택을 도우며, 나눠 맡아 실행한 뒤 반응을 보고 다음 판단으로 이어지는 구조"><figcaption>대표와 나눈 생각이 조사·실행·반응을 거쳐, 다음 판단의 근거로 남습니다.</figcaption></figure><div class="iv-model"><article><span>01 / 운영 실행·개선 파트너</span><h3>생각을 나누고, 할 일을 나눠 맡습니다.</h3><p>대표가 직접 일하며 겪는 고민을 듣고 놓친 부분을 짚습니다. 필요한 자료를 찾아 비교하고, 선택한 방향을 안내·업무 자료와 적용 계획으로 구체화합니다.</p></article><article><span>02 / 운영 데이터·시스템 기반</span><h3>판단과 반응이 다음 일에 이어집니다.</h3><p>왜 그 일을 골랐는지, 실제 썼는지, 무엇이 달랐는지 연결해 남깁니다. 기록이 쌓이면 반복되는 질문과 업무를 찾아, 필요한 도구와 시스템으로 발전시킵니다.</p></article><p class="iv-model-note">베타는 한 가지 운영 문제와 정해진 결과물에 집중합니다. 정기 데이터 관리·고객 계정·자동 업로드는 별도로 준비할 범위입니다.</p></div></div><figure class="iv-goals"><picture><source media="(max-width:600px)" srcset="/assets/operating-goals-mobile.svg"><img src="/assets/operating-goals.svg" width="1180" height="360" loading="lazy" alt="함께 정할 운영 목표의 예시: 판단할 근거를 정리하고, 미뤄둔 아이디어를 실행하며, 사업의 좋은 점을 고객에게 전하는 모습"></picture><figcaption>판단의 여유·실행의 진척·사업의 색깔은 함께 정할 수 있는 목표의 예시입니다. 결과를 보장하는 성과 수치가 아닙니다.</figcaption></figure><div class="iv-next"><p>우리 사업장에서는 어떤 변화를 먼저 볼까요?</p><a class="ed-button" href="/beta.html">운영 점검 무료 베타 살펴보기 ↗</a></div></section>'''

def compact_visual():
    return '''<figure class="iv-service-visual"><img src="/assets/operating-cycle.svg" width="620" height="520" loading="lazy" alt="고민을 듣고 조사·선택·실행·반응과 재검토를 연결하는 디테일랩의 작업 구조"><figcaption>나눈 고민 → 조사와 선택 → 적용과 반응 → 다음 판단</figcaption></figure><p><a class="ed-link" href="/#impact">고민별로 함께 볼 운영 기록 살펴보기 →</a></p>'''
