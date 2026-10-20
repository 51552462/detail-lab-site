"""Existing v2 questions, not a new interview framework. Synthetic test only."""
INTAKE = [
 ('I01', '어떤 업장이고 주로 무엇을 제공하나요?', True),
 ('I02', '운영 중·시작 준비·재시작 중 어디에 해당하나요? 사업장은 몇 곳인가요?', True),
 ('I03', '대표를 포함해 함께 일하는 사람은 대략 몇 명인가요?', False),
 ('I04', '최근에 가장 걸렸던 한 장면을 설명해 주세요. 언제 어떤 일이 있었나요?', True),
 ('I05', '무엇이 달라지면 이번 대화가 도움이 됐다고 느끼시겠어요?', True),
 ('I06', '그 일로 시간이 늘거나 놓친 일이 있나요? 모르면 비워 두셔도 됩니다.', False),
 ('I07', '이미 바꿔 본 방법과 그 뒤 반응은 어땠나요?', False),
 ('I08', '이 일을 바꿀 때 누가 결정하나요?', True),
 ('I09', '회신받을 이메일과 편한 호칭을 알려 주세요. 추가 대화는 이메일·예약 통화 중 어떤 편이 좋나요?', True),
]
INTERVIEW = [
 ('U01', '이 사업을 시작할 때 무엇을 하고 싶었고 지금은 무엇이 중요해졌나요?'),
 ('U02', '가장 자주 선택되는 상품과 그 고객의 이용 이유는 무엇인가요?'),
 ('U03', '돈은 언제 받고 제공은 언제 끝나나요?'),
 ('U04', '누가 어떤 일을 맡고 어디까지 결정하나요?'),
 ('U05', '대표가 하루 빠지면 무엇이 멈추나요?'),
 ('U06', '최근 문의 한 건이 이용 종료까지 간 순서를 말해 주세요.'),
 ('U07', '지난주 가장 오래 붙잡고 있던 일은 무엇인가요?'),
 ('U08', '자주 다시 묻는 일과 드물지만 어려운 일은 각각 무엇인가요?'),
 ('U09', '이미 시도한 방법과 잘 안 쓰인 이유는 무엇인가요?'),
 ('U10', '최근 만족스러웠던 일은 무엇이고 무엇 덕분이라고 보시나요?'),
 ('U11', '지금 고치기 어렵거나 걱정되는 것은 무엇인가요?'),
 ('U12', '6개월~1년 뒤 어떤 하루가 됐으면 하나요?'),
 ('U13', '사업 밖 시간을 어떻게 쓰고 싶나요? 현재 쓰는 도구 중 일이 줄거나 늘어난 것은?'),
]
MODULES = {
 'D01': ('매출·수익', '결제 금액·제공한 서비스 금액·환불 중 어떤 수치가 줄었나요?', '총액에 무엇이 포함됐나요? 누락 결제와 중복은?'),
 'D02': ('고객 응대·재방문', '문의했지만 이용하지 않은 최근 한 건은 어디에서 끝났나요?', '무응답·취소·이유를 들은 건을 구분할 수 있나요?'),
 'D03': ('직원·조직·교육', '각자가 맡았다고 생각한 일과 실제로 맡은 일이 달랐던 사례는?', '규정이 없는가, 못 찾는가, 예외가 많은가?'),
 'D04': ('대표 업무시간·운영 자율성', '최근 쉬는 날 들어온 연락 중 즉시 대표만 결정해야 했던 것은?', '다음 한 주에 어떤 연락을 셀 수 있나요?'),
 'D05': ('업무 프로세스', '일을 받은 때부터 끝났다고 아는 때까지 누가 무엇을 남기나요?', '한 건을 현장 책임자와 확인할 수 있나요?'),
 'D06': ('상품·서비스', '고객이 산다고 이해한 내용과 실제 받는 것은 같은가요?', '한 상품의 제공 시간을 기록할 수 있나요?'),
 'D07': ('브랜드·콘셉트', '고객이 어떤 이유로 이곳을 골랐다고 직접 말했나요?', '실제 선택 이유를 확인할 수 있나요?'),
 'D08': ('마케팅·홍보', '어떤 고객이 어느 경로로 문의했는지 확인 가능한가요?', '문의 출처 한 칸부터 기록할 수 있나요?'),
 'D09': ('데이터·업무 자동화', '반복 작업의 입력과 최종 결과를 한 건씩 보여줄 수 있나요?', '공식 내보내기·API·관리 권한이 있나요?'),
 'D10': ('외부 경제·시장', '최근 외부 변화가 어떤 거래나 비용에 닿았다고 보시나요?', '기간·지역·단위가 같은 실제 기록이 있나요?'),
}
STATES = {
 'received': '접수됨', 'reviewing': '기본 검토', 'needs_info': '추가 질문 필요',
 'eligible': '진행 가능', 'out_of_scope': '범위 밖', 'interview_scheduled': '인터뷰 예정',
 'interview_done': '인터뷰 완료', 'proposal': '제안 준비', 'customer_decision': '고객 결정',
 'in_progress': '프로젝트 진행', 'hold': '보류', 'closed': '종료',
}
TRANSITIONS = {
 'received': ['reviewing', 'hold'], 'reviewing': ['needs_info', 'eligible', 'out_of_scope', 'hold'],
 'needs_info': ['reviewing', 'hold', 'closed'], 'eligible': ['interview_scheduled', 'hold'],
 'out_of_scope': ['closed'], 'interview_scheduled': ['hold'],
 'interview_done': ['proposal', 'hold'], 'proposal': ['customer_decision', 'hold'],
 'customer_decision': ['in_progress', 'hold', 'closed'], 'in_progress': ['hold', 'closed'],
 'hold': ['reviewing', 'closed'], 'closed': [],
}
GOAL_FIELDS = ['desired_outcome', 'deliverable', 'included', 'excluded', 'strengths',
 'client_role', 'lab_role', 'baseline', 'metric', 'start', 'end', 'hours', 'cost',
 'revisions', 'approver_role', 'stop_rule', 'review_on', 'data_policy']
SOURCE_NOTION = {
 'intake': 'https://app.notion.com/p/3fef6ead7401812f9480e6f5549c0316',
 'goal_report': 'https://app.notion.com/p/3fff6ead74018174923cc832cce3da75',
 'data': 'https://app.notion.com/p/3fef6ead74018152a04ccaf57cc0a522',
}
