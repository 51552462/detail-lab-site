import copy
import io
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from internal.ops_mvp import scenario
from internal.ops_mvp.workflow import Workflow, FlowError, DataError, OPERATOR as O, CLIENT_A as A, CLIENT_B as B


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.root = Path(self.temp.name)
        self.flow = Workflow(self.root); self.flow.provision()
        self.case = self.flow.submit(A, scenario.intake(), 'synthetic-test-key-001')['id']

    def tearDown(self):
        self.flow.close(); self.temp.cleanup()

    def rev(self):
        return self.flow.case(O, self.case)['revision']

    def understood(self):
        for state in ('reviewing', 'eligible', 'interview_scheduled'):
            scenario.step(self.flow, self.case, state)
        self.flow.interview(O, self.case, scenario.interview(), self.rev())
        self.flow.confirm_interview(A, self.case)
        self.flow.diagnose(O, self.case, scenario.diagnosis(), self.rev())

    def project(self):
        self.understood()
        self.flow.save_goal(O, self.case, scenario.goal(), self.rev())
        g = self.flow.latest_goal(self.case)
        for actor in (O, A):
            self.flow.approve_goal(actor, self.case, g['version'], g['digest'])
        for state in ('proposal', 'customer_decision', 'in_progress'):
            scenario.step(self.flow, self.case, state)

    def uploaded(self):
        self.project()
        return self.flow.upload(A, self.case, 'SYN-data', 'test.csv', scenario.csv_data(), '합성 집계', '2026-10-05', '2026-10-18', '건')

    def report(self):
        source = self.uploaded()
        self.flow.review_upload(O, self.case, 'SYN-data', source['version'], True)
        return self.flow.draft_report(O, self.case, 'weekly', '2026-10-05', '2026-10-18')

    def assertCode(self, code, function, *args, **kwargs):
        with self.assertRaises((FlowError, DataError)) as err:
            function(*args, **kwargs)
        self.assertIn(code, str(err.exception))

    def test_full_synthetic_case_and_input_trace(self):
        result = scenario.run(self.root / 'complete')
        self.assertEqual(result['state'], 'closed')
        self.assertEqual(len(result['events']), 32)
        reports = {r['body']['kind']: r for r in result['reports']}
        self.assertEqual([g['total'] for g in reports['weekly']['body']['groups']], ['21', '7'])
        self.assertEqual(reports['monthly']['body']['groups'][0]['total'], '28')
        self.assertEqual(len(reports['annual']['body']['groups']), 1)
        self.assertIn('전체 기간', reports['annual']['body']['missing'])
        self.assertTrue(all(not r['stale'] and r['state'] == 'approved' for r in result['reports']))
        traces = sum((g['trace'] for g in reports['weekly']['body']['groups']), [])
        self.assertEqual(len(traces), 14)
        self.assertEqual(sum(int(t['value']) for t in traces), 28)
        self.assertTrue(result['synthetic_only'])

    def test_idempotent_receipt_and_changed_payload_conflict(self):
        r = self.flow.submit(A, scenario.intake(), 'synthetic-test-key-001')
        self.assertEqual(r, {'id': self.case, 'duplicate': True})
        data = scenario.intake(); data['answers']['I04'] = '다른 합성 사건'
        self.assertCode('IDEMPOTENCY_CONFLICT', self.flow.submit, A, data, 'synthetic-test-key-001')
        self.assertEqual(len(self.flow.list_cases(O)), 1)

    def test_required_and_optional_intake_fields(self):
        data = scenario.intake()
        for key in ('I03', 'I06', 'I07'): data['answers'][key] = ''
        self.flow.submit(A, data, 'synthetic-optional-001')
        data['answers']['I04'] = ''
        self.assertCode('TEXT_LENGTH', self.flow.submit, A, data, 'synthetic-optional-002')

    def test_real_email_and_phone_rejected(self):
        for key, value in [('I09', 'actual@naver.com'), ('I04', '전화 010-1234-5678')]:
            data = scenario.intake(); data['answers'][key] = value
            self.assertCode('PERSONAL_DATA_REJECTED', self.flow.submit, A, data, 'synthetic-real-block')

    def test_synthetic_confirmation_and_site_ownership(self):
        data = scenario.intake(); data['synthetic_only'] = False
        self.assertCode('SYNTHETIC_CONFIRMATION_REQUIRED', self.flow.submit, A, data, 'synthetic-no-confirm')
        data = scenario.intake('SYN-B')
        self.assertCode('SITE_NOT_ALLOWED', self.flow.submit, A, data, 'synthetic-wrong-site')

    def test_one_tenant_two_sites_and_other_tenant_denied(self):
        data = scenario.intake(); data['site_id'] = 'SYN-A-SITE-2'
        self.flow.submit(A, data, 'synthetic-second-site')
        self.assertEqual(len(self.flow.list_cases(A)), 2)
        self.assertEqual(self.flow.list_cases(B), [])
        self.assertCode('NOT_FOUND', self.flow.detail, B, self.case)

    def test_contacts_are_separate_and_operator_only(self):
        self.assertNotIn('owner@example.invalid', json.dumps(self.flow.detail(A, self.case)))
        self.assertNotIn('I09', self.flow.detail(A, self.case)['answers'])
        self.assertCode('OPERATOR_REQUIRED', self.flow.contact, A, self.case)
        self.assertEqual(self.flow.contact(O, self.case)['email'], 'owner@example.invalid')
        self.assertFalse(self.flow.db.execute("SELECT name FROM main.sqlite_master WHERE name='contacts'").fetchall())

    def test_stale_case_and_invalid_transition_have_no_effect(self):
        revision = self.rev(); scenario.step(self.flow, self.case, 'reviewing')
        self.assertCode('STALE_CASE', self.flow.transition, O, self.case, 'eligible', revision, '담당', '다음', '2026-10-26', '기록')
        self.assertCode('INVALID_TRANSITION', scenario.step, self.flow, self.case, 'in_progress')
        self.assertEqual(self.flow.case(O, self.case)['state'], 'reviewing')

    def test_interview_task_created_once_on_reschedule(self):
        for state in ('reviewing', 'eligible', 'interview_scheduled', 'hold', 'reviewing', 'eligible', 'interview_scheduled'):
            scenario.step(self.flow, self.case, state)
        self.assertEqual(len(self.flow.detail(O, self.case)['tasks']), 1)

    def test_interview_and_diagnosis_need_customer_confirmation(self):
        for state in ('reviewing', 'eligible', 'interview_scheduled'): scenario.step(self.flow, self.case, state)
        bad = scenario.interview(); del bad['U10']
        self.assertCode('INTERVIEW_FIELDS_REQUIRED', self.flow.interview, O, self.case, bad, self.rev())
        self.flow.interview(O, self.case, scenario.interview(), self.rev())
        self.assertCode('CLIENT_CONFIRMATION_REQUIRED', self.flow.confirm_interview, O, self.case)
        self.assertCode('INTERVIEW_CONFIRMATION_REQUIRED', self.flow.diagnose, O, self.case, scenario.diagnosis(), self.rev())

    def test_no_automatic_fact_and_f_requires_reviewed_evidence(self):
        self.understood(); self.assertEqual(self.flow.detail(O, self.case)['claims'], [])
        self.assertCode('REVIEWED_EVIDENCE_REQUIRED', self.flow.add_claim, O, self.case, 'F', {'statement': '추측을 사실로 시도', 'evidence_id': 'fake'})
        self.assertCode('TEXT_LENGTH', self.flow.add_claim, O, self.case, 'H', {'statement': '반증 없는 가설', 'falsification': ''})

    def test_diagnosis_limited_to_one_or_two(self):
        self.understood()
        self.assertCode('SELECT_ONE_OR_TWO_MODULES', self.flow.diagnose, O, self.case, [], self.rev())
        self.assertCode('SELECT_ONE_OR_TWO_MODULES', self.flow.diagnose, O, self.case, scenario.diagnosis()*3, self.rev())

    def test_missing_agreement_term_blocks_goal(self):
        self.understood(); g = scenario.goal(); del g['cost']
        self.assertCode('GOAL_FIELDS_REQUIRED', self.flow.save_goal, O, self.case, g, self.rev())

    def test_dual_approval_blocks_start(self):
        self.understood(); self.flow.save_goal(O, self.case, scenario.goal(), self.rev())
        for state in ('proposal', 'customer_decision'): scenario.step(self.flow, self.case, state)
        self.assertCode('DUAL_APPROVAL_REQUIRED', scenario.step, self.flow, self.case, 'in_progress')

    def test_goal_revision_invalidates_prior_approval(self):
        self.project(); old = self.flow.latest_goal(self.case)
        self.flow.save_goal(O, self.case, scenario.goal(), self.rev())
        self.assertCode('STALE_GOAL', self.flow.approve_goal, A, self.case, old['version'], old['digest'])
        self.assertCode('DUAL_APPROVAL_REQUIRED', self.flow.agreed, self.case)

    def test_experiment_client_approval_and_nonuse_reason(self):
        self.project(); h = self.flow.add_claim(O, self.case, 'H', {'statement': '합성 가설', 'falsification': '반대 사례 확인'})
        exp = self.flow.create_experiment(O, self.case, scenario.experiment(h))
        self.assertCode('EXECUTION_NOT_APPROVED', self.flow.observe, O, self.case, exp, scenario.observation())
        self.flow.approve_experiment(A, self.case, exp)
        note = scenario.observation('not_used'); note['not_used_reason'] = ''
        self.assertCode('NONUSE_REASON_REQUIRED', self.flow.observe, O, self.case, exp, note)
        self.flow.observe(O, self.case, exp, scenario.observation('not_used'))
        self.assertCode('CLIENT_DECISION_REQUIRED', self.flow.decide, O, self.case, exp, scenario.decision('stop'))
        self.flow.decide(A, self.case, exp, scenario.decision('stop'))
        self.assertEqual(self.flow.detail(O, self.case)['experiments'][0]['decision']['choice'], 'stop')

    def test_upload_before_agreement_rejected(self):
        self.assertCode('PROJECT_NOT_STARTED', self.flow.upload, A, self.case, 'SYN-data', 'x.csv', scenario.csv_data(), '합성', '2026-10-05', '2026-10-18', '건')

    def test_upload_scope_and_unit_checks(self):
        self.project()
        args = [A, self.case, 'SYN-data', 'x.csv', scenario.csv_data(), '합성', '2026-10-05', '2026-10-18', '원']
        self.assertCode('DECLARED_UNIT_MISMATCH', self.flow.upload, *args)
        args[-1] = '건'; args[4] = scenario.csv_data().replace(b'SYN-A-SITE-1', b'SYN-A-SITE-2')
        self.assertCode('CASE_DATA_SCOPE_MISMATCH', self.flow.upload, *args)

    def test_pending_data_blocks_report_and_duplicate_is_not_reingested(self):
        source = self.uploaded()
        self.assertCode('LATEST_SOURCES_NOT_APPROVED', self.flow.draft_report, O, self.case, 'weekly', '2026-10-05', '2026-10-18')
        repeated = self.flow.upload(A, self.case, 'SYN-data', 'x.csv', scenario.csv_data(), '합성 집계', '2026-10-05', '2026-10-18', '건')
        self.assertTrue(repeated['duplicate']); self.assertEqual(repeated['version'], 1)

    def test_customer_cannot_approve_data_or_see_draft_report(self):
        report = self.report()
        self.assertCode('OPERATOR_REQUIRED', self.flow.review_upload, A, self.case, 'SYN-data', 1, True)
        self.assertEqual(self.flow.detail(A, self.case)['reports'], [])
        self.assertCode('OPERATOR_REQUIRED', self.flow.approve_report, A, self.case, report)
        self.flow.approve_report(O, self.case, report)
        self.assertEqual(len(self.flow.detail(A, self.case)['reports']), 1)

    def test_new_upload_invalidates_previous_report(self):
        report = self.report(); self.flow.approve_report(O, self.case, report)
        self.flow.upload(A, self.case, 'SYN-data', 'changed.csv', scenario.csv_data(delta=1), '합성 집계', '2026-10-05', '2026-10-18', '건')
        self.assertTrue(self.flow.detail(O, self.case)['reports'][0]['stale'])
        self.assertEqual(self.flow.detail(A, self.case)['reports'], [])
        self.assertCode('LATEST_SOURCES_NOT_APPROVED', self.flow.draft_report, O, self.case, 'monthly', '2026-10-05', '2026-10-18')

    def test_report_draft_stale_after_changed_work_record(self):
        report = self.report(); self.flow.add_work(O, self.case, '합성 기록', 10, 0)
        self.assertCode('STALE_REPORT', self.flow.approve_report, O, self.case, report)

    def test_overlapping_sources_are_not_added_twice(self):
        self.report()
        other = self.flow.upload(A, self.case, 'SYN-duplicate-period', 'x.csv', scenario.csv_data(), '다른 합성 출처', '2026-10-05', '2026-10-18', '건')
        self.flow.review_upload(O, self.case, 'SYN-duplicate-period', other['version'], True)
        self.assertCode('OVERLAPPING_SOURCES', self.flow.draft_report, O, self.case, 'weekly', '2026-10-05', '2026-10-18')

    def test_no_data_is_not_zero_or_fabricated_year(self):
        self.report()
        self.assertCode('NO_DATA_IN_PERIOD', self.flow.draft_report, O, self.case, 'annual', '2025-01-01', '2025-12-31')

    def test_xlsx_upload_uses_existing_parser(self):
        from openpyxl import Workbook
        import csv
        self.project(); book = Workbook(); sheet = book.active
        for row in csv.reader(io.StringIO(scenario.csv_data().decode())): sheet.append(row)
        data = io.BytesIO(); book.save(data); book.close()
        result = self.flow.upload(A, self.case, 'SYN-xlsx', 'x.xlsx', data.getvalue(), '합성 엑셀', '2026-10-05', '2026-10-18', '건')
        self.assertEqual(result['rows'], 14)

    def test_corrupt_oversized_and_extra_column_files(self):
        self.project()
        base = [A, self.case, 'SYN-data', 'x.xlsx', b'broken', '합성', '2026-10-05', '2026-10-18', '건']
        self.assertCode('INVALID_WORKBOOK', self.flow.upload, *base)
        base[3] = 'x.csv'; base[4] = b'x'*2000001
        self.assertCode('FILE_TOO_LARGE', self.flow.upload, *base)
        base[4] = scenario.csv_data().replace(b'row_key,', b'employee_name,row_key,')
        self.assertCode('HEADER_MISMATCH', self.flow.upload, *base)

    def test_handover_before_review_is_blocked(self):
        self.project()
        self.assertCode('HANDOVER_NOT_READY', scenario.step, self.flow, self.case, 'closed')

    def test_count_metric_rejects_fraction_and_negative(self):
        self.project()
        for value in (b'-1', b'0.5'):
            data=scenario.csv_data().replace(b'2026-10-05,3',b'2026-10-05,'+value)
            self.assertCode('INVALID_NUMBER' if value==b'-1' else 'INTEGER_REQUIRED',self.flow.upload,A,self.case,'SYN-data','x.csv',data,'합성','2026-10-05','2026-10-18','건')

    def test_external_workbook_relationship_rejected(self):
        from openpyxl import Workbook
        self.project();book=Workbook();book.active['A1']='외부 링크';book.active['A1'].hyperlink='https://example.invalid'
        data=io.BytesIO();book.save(data);book.close()
        self.assertCode('EXTERNAL_RELATIONSHIP_REJECTED',self.flow.upload,A,self.case,'SYN-ext','x.xlsx',data.getvalue(),'합성','2026-10-05','2026-10-18','건')


if __name__ == '__main__': unittest.main()
