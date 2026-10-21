"""Executable fictional case. No statement here is a customer result or a price."""
from __future__ import annotations

import argparse
import csv
import io
import json
import time
from pathlib import Path

from .workflow import Workflow, OPERATOR, CLIENT_A, CLIENT_B


def intake(client='SYN-A'):
    return {'synthetic_only': True, 'site_id': client + '-SITE-1', 'alias': '합성 대표', 'channel': '이메일',
            'answers': {'I01': '합성 서비스업 / 예약제 업무 제공', 'I02': '운영 중 / 사업장 2곳',
                        'I03': '2~5명', 'I04': '합성 사례: 교대 후 요청의 완료 여부를 다음 담당자가 다시 물었다.',
                        'I05': '완료 기준을 같은 뜻으로 이해하고 누락을 확인하고 싶다.', 'I06': '미측정',
                        'I07': '메신저 공지를 해봤으나 실제 사용은 미확인', 'I08': '대표 본인', 'I09': 'owner@example.invalid'}}


def interview():
    return dict(zip([f'U{i:02d}' for i in range(1, 14)], [
        '합성 진술: 예약이 이어지는 운영을 원한다.', '합성 진술: 예약 고객에게 한 업무를 제공한다.',
        '합성 진술: 이용 전에 받고 제공이 끝난 뒤 정산한다. 원가 미확인.',
        '대표/교대 담당 역할만 기록. 실명 없음.', '대표가 없을 때 완료 판단을 다시 묻는다.',
        '문의→접수→담당 확인→제공→완료 기록. 전체 빈도는 미확인.', '확인 연락 처리시간 미측정.',
        '일반 인계와 예외 승인 구분이 필요하다.', '공지는 전달했으나 사용 기록이 없다.',
        '기존의 친절한 안내는 지킨다. 이는 합성 대표 진술이다.', '추가 업무 부담을 늘리지 않는 범위.',
        '희망: 교대 담당자가 처리 상황을 알 수 있는 하루.', '원격 기록 확인을 원함. 개인 사정은 받지 않음.',
    ]))


def diagnosis():
    return [{'code': 'D05', 'reason': '교대의 완료 기준을 확인하기 위해', 'known': '최근 사건 설명은 T, 원인은 H로 남음',
             'answer': '업무 시작과 완료 표기가 같은 양식에 있지 않다는 합성 진술',
             'material_request': '합성 14일 인계 집계만; 고객/직원 명단 제외', 'fallback': '자료가 없으면 다음 주 기록할 항목부터 합의',
             'unknown': '다른 교대와 예외 상황 빈도', 'next_judgment': '완료 표기 양식 하나를 시험할 수 있는가?'}]


def goal():
    return {'desired_outcome': '인계 누락 감소를 희망. 성과 보장 아님.', 'deliverable': '한 업무의 완료·인계 기준표와 재검토 기록',
            'included': '한 업무 양식 제작·사용 확인 1회', 'excluded': '직원 평가·노무 판단·상시 긴급 대응', 'strengths': '기존 친절한 안내 유지',
            'client_role': '내부 승인·공지·현장 사용과 기록', 'lab_role': '합의한 양식 제작·검수·설명',
            'baseline': '합성 2026-10-05~11 매일 누락 건수; 실제 자료 아님', 'metric': 'missed_handover:v1:건:sum',
            'start': '2026-10-12', 'end': '2026-10-18', 'hours': '2', 'cost': '0', 'revisions': '1',
            'approver_role': '합성 대표', 'stop_rule': '업무 부담·고객 혼선이 늘면 중단 후 이전 양식으로', 'review_on': '2026-10-19',
            'data_policy': '합성 자료만·루프백 시험·외부 AI/이메일 전송 없음. 실제 처리 동의 아님.'}


def experiment(hypothesis_id):
    return {'problem': '합성 교대의 완료 표기 누락', 'hypothesis_id': hypothesis_id, 'reason': '완료 기준 차이를 작은 양식으로 반증',
            'action': '기존 친절한 안내는 유지하고 한 업무에 완료 칸 추가', 'owner': '합성 현장 책임자',
            'user_role': '합성 교대 담당', 'risk': '입력이 추가 부담이 될 수 있음', 'rollback': '이전 기준표 v1 복귀', 'check_on': '2026-10-19'}


def observation(used='used'):
    return {'used': used, 'observed_on': '2026-10-18', 'observation': '합성 사용 기록에서 완료 칸을 확인했다.',
            'reaction': '합성 담당자의 편하다는 진술. 지표 개선과는 구분.', 'side_effect': '합성 상황에서 추가 부담 여부 미측정',
            'other_causes': '업무량·영업일·인력 변화가 다른 설명일 수 있음',
            'not_used_reason': '합성 운영 일정으로 사용하지 못함' if used == 'not_used' else ''}


def decision(choice='modify'):
    return {'choice': choice, 'reason': '수치 변화의 원인은 미확정. 부담을 더 확인한다.', 'handover': '기준표 v2·사용법·미확인 목록·중단 기준 인계',
            'owner': '합성 현장 책임자', 'next_review': '2026-10-26'}


def csv_data(client='SYN-A', delta=0):
    file = io.StringIO(newline='')
    writer = csv.writer(file)
    writer.writerow(['row_key', 'site_id', 'metric_id', 'definition_version', 'observed_on', 'value'])
    for day, value in zip(range(5, 19), [3, 2, 4, 3, 2, 3, 4, 1, 1, 0, 1, 2, 1, 1]):
        writer.writerow([f'SYN-row-{day}', client + '-SITE-1', 'missed_handover', 'v1', f'2026-10-{day:02d}', value + delta])
    return file.getvalue().encode()


def step(flow, case_id, state):
    flow.transition(OPERATOR, case_id, state, flow.case(OPERATOR, case_id)['revision'], '합성 운영자',
                    '다음 합성 단계 확인', '2026-10-26', '합성 시험 기록만. 자동 발송하지 않음.')


def run(root):
    started = time.perf_counter()
    flow = Workflow(root); flow.provision()
    case_id = flow.submit(CLIENT_A, intake(), 'synthetic-scenario-001')['id']
    try:
        for state in ('reviewing', 'eligible', 'interview_scheduled'):
            step(flow, case_id, state)
        flow.interview(OPERATOR, case_id, interview(), flow.case(OPERATOR, case_id)['revision'])
        flow.confirm_interview(CLIENT_A, case_id)
        flow.diagnose(OPERATOR, case_id, diagnosis(), flow.case(OPERATOR, case_id)['revision'])
        evidence_id = flow.add_evidence(OPERATOR, case_id, {'label': '합성 기준표 발췌', 'excerpt': '완료 칸이 없는 합성 기준표', 'source_version': 'SYN-v1', 'observed_on': '2026-10-05'})
        flow.add_claim(OPERATOR, case_id, 'F', {'statement': '합성 기준표 발췌에 완료 칸이 없다.', 'evidence_id': evidence_id})
        flow.add_claim(OPERATOR, case_id, 'T', {'statement': '대표는 교대 후 다시 묻는다고 설명함.', 'role': '합성 대표', 'said_on': '2026-10-05'})
        hypothesis = flow.add_claim(OPERATOR, case_id, 'H', {'statement': '완료 뜻의 차이가 인계 누락에 영향을 줄 수 있다.', 'falsification': '완료 기준을 같게 이해해도 같은 누락이 발생하는가?'})
        flow.add_claim(OPERATOR, case_id, 'U', {'statement': '다른 교대의 같은 문제 빈도', 'next_question': '다음 주 같은 정의로 셀 수 있는가?'})
        version = flow.save_goal(OPERATOR, case_id, goal(), flow.case(OPERATOR, case_id)['revision'])
        g = flow.latest_goal(case_id)
        flow.approve_goal(OPERATOR, case_id, version, g['digest'])
        flow.approve_goal(CLIENT_A, case_id, version, g['digest'])
        for state in ('proposal', 'customer_decision', 'in_progress'):
            step(flow, case_id, state)
        exp_id = flow.create_experiment(OPERATOR, case_id, experiment(hypothesis))
        flow.approve_experiment(CLIENT_A, case_id, exp_id)
        flow.observe(OPERATOR, case_id, exp_id, observation())
        upload = flow.upload(CLIENT_A, case_id, 'SYN-handover', 'synthetic.csv', csv_data(), '합성 14일 집계; 실제 고객 없음', '2026-10-05', '2026-10-18', '건')
        flow.review_upload(OPERATOR, case_id, 'SYN-handover', upload['version'], True)
        flow.decide(CLIENT_A, case_id, exp_id, decision())
        flow.add_work(OPERATOR, case_id, '합성 가정 시간: 실제 서비스 소요시간 아님', 30, 0)
        reports = []
        for kind in ('weekly', 'monthly', 'annual'):
            report_id = flow.draft_report(OPERATOR, case_id, kind, '2026-10-05', '2026-10-18')
            flow.approve_report(OPERATOR, case_id, report_id); reports.append(report_id)
        step(flow, case_id, 'closed')
        result = flow.detail(OPERATOR, case_id)
        result['synthetic_only'] = True
        result['execution_elapsed_seconds'] = round(time.perf_counter() - started, 4)
        result['elapsed_meaning'] = '소프트웨어 합성 시험 경과시간. 고객 업무시간·자동화 절감 효과가 아님.'
        return result
    finally:
        flow.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', required=True)
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    result = run(args.root)
    path = Path(args.out); path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(json.dumps({'synthetic_only': True, 'case_id': result['id'], 'state': result['state'],
                      'events': len(result['events']), 'reports': len(result['reports']), 'output': str(path)}))
