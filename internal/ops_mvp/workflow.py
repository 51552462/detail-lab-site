"""Loopback, SYN- fixtures only. No production privacy/security approval is implied."""
from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import tempfile
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timezone, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path

from internal.data_mvp.pipeline import Store, DataError, iso_date, MAX_BYTES
from .catalog import INTAKE, INTERVIEW, MODULES, TRANSITIONS, GOAL_FIELDS


class FlowError(ValueError):
    def __init__(self, code, status=400):
        self.code, self.status = code, status
        super().__init__(code)


@dataclass(frozen=True)
class Actor:
    id: str
    role: str
    client_id: str | None = None


OPERATOR = Actor('SYN-OPERATOR', 'operator')
CLIENT_A = Actor('SYN-OWNER-A', 'client', 'SYN-A')
CLIENT_B = Actor('SYN-OWNER-B', 'client', 'SYN-B')


def now():
    return datetime.now(timezone.utc).isoformat()


def dumps(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def digest(value):
    return hashlib.sha256(dumps(value).encode()).hexdigest()


def uid(prefix):
    return 'SYN-' + prefix + '-' + uuid.uuid4().hex


def require(condition, code, status=400):
    if not condition:
        raise FlowError(code, status)


def text(value, required=True, maximum=2000):
    require(isinstance(value, str), 'TEXT_REQUIRED')
    value = value.strip()
    require(len(value) <= maximum and (bool(value) or not required), 'TEXT_LENGTH')
    # This rejects common identifiers; it cannot prove arbitrary text contains no PII.
    require(not re.search(r'\b\d{6}[- ]?[1-8]\d{6}\b|01[016789][- ]?\d{3,4}[- ]?\d{4}|[\w.+-]+@(?!example\.invalid\b)[\w.-]+', value), 'PERSONAL_DATA_REJECTED')
    return value


def numeric(value, integer=False):
    try:
        number = Decimal(str(value))
        require(number.is_finite() and number >= 0 and number <= Decimal('1000000000000'), 'INVALID_NUMBER')
        if integer:
            require(number == number.to_integral_value(), 'INTEGER_REQUIRED')
        return str(number)
    except (InvalidOperation, TypeError):
        raise FlowError('INVALID_NUMBER') from None


class Workflow:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.db = sqlite3.connect(self.root / 'operations.sqlite3', timeout=5)
        self.db.row_factory = sqlite3.Row
        self.db.executescript(Path(__file__).with_name('schema.sql').read_text())
        self.db.execute('ATTACH DATABASE ? AS private', (str(self.root / 'contacts.sqlite3'),))
        self.db.execute('CREATE TABLE IF NOT EXISTS private.contacts(case_id TEXT PRIMARY KEY, email TEXT NOT NULL, alias TEXT NOT NULL, channel TEXT NOT NULL)')
        self.db.commit()
        for name in ('operations.sqlite3', 'contacts.sqlite3'):
            os.chmod(self.root / name, 0o600)

    def close(self):
        self.db.close()

    def provision(self):
        """Only fixed synthetic tenants. No arbitrary customer registration endpoint."""
        with self.db:
            for client in ('SYN-A', 'SYN-B'):
                self.db.execute('INSERT OR IGNORE INTO clients VALUES (?,?)', (client, '합성 업무 흐름 시험만'))
                for suffix in ('1', '2'):
                    self.db.execute('INSERT OR IGNORE INTO sites VALUES (?,?,?)', (client + '-SITE-' + suffix, client, '합성 서비스업'))
        for client in ('SYN-A', 'SYN-B'):
            store = Store(self.root / 'data', client)
            try:
                for suffix in ('1', '2'):
                    site = client + '-SITE-' + suffix
                    for metric, unit, definition in [
                        ('missed_handover', '건', '하루 마감 기준 완료 표기가 빠진 인계 요청 수; 0도 직접 기록'),
                        ('handling_minutes', '분', '하루 처리시간 합계; 영업일/인력 변화 별도 확인'),
                    ]:
                        if not store.db.execute('SELECT 1 FROM metrics WHERE site_id=? AND metric_id=? AND definition_version=?', (site, metric, 'v1')).fetchone():
                            store.add_metric(client, site, metric, 'v1', unit, definition)
            finally:
                store.close()

    def case(self, actor, case_id, operator=False):
        require(isinstance(actor, Actor) and actor.role in ('operator', 'client'), 'AUTH_REQUIRED', 401)
        if operator:
            require(actor.role == 'operator', 'OPERATOR_REQUIRED', 403)
        row = self.db.execute('SELECT * FROM cases WHERE id=?', (case_id,)).fetchone()
        require(row is not None and (actor.role == 'operator' or actor.client_id == row['client_id']), 'NOT_FOUND', 404)
        return dict(row)

    def event(self, actor, case_id, action, detail=None, bump=True):
        self.db.execute('INSERT INTO events(case_id,occurred_at,action,actor_id,actor_role,detail) VALUES (?,?,?,?,?,?)',
                        (case_id, now(), action, actor.id, actor.role, dumps(detail or {})))
        if bump:
            self.db.execute('UPDATE cases SET revision=revision+1,updated_at=? WHERE id=?', (now(), case_id))

    def version(self, case, expected):
        require(type(expected) is int and case['revision'] == expected, 'STALE_CASE', 409)

    def submit(self, actor, data, key):
        require(actor.role == 'client' and actor.client_id in ('SYN-A', 'SYN-B'), 'SYNTHETIC_CLIENT_REQUIRED', 403)
        require(data.get('synthetic_only') is True, 'SYNTHETIC_CONFIRMATION_REQUIRED')
        require(re.fullmatch(r'[A-Za-z0-9_-]{12,100}', str(key)) is not None, 'IDEMPOTENCY_KEY_REQUIRED')
        answers = data.get('answers', {})
        require(set(answers) == {q[0] for q in INTAKE}, 'QUESTION_SET_MISMATCH')
        clean = {qid: text(answers[qid], mandatory, 1500) for qid, _, mandatory in INTAKE}
        email = clean.pop('I09').lower()
        require(re.fullmatch(r'[a-z0-9._+-]{1,64}@example\.invalid', email) is not None, 'SYNTHETIC_EMAIL_REQUIRED')
        site = data.get('site_id')
        require(self.db.execute('SELECT 1 FROM sites WHERE id=? AND client_id=?', (site, actor.client_id)).fetchone() is not None, 'SITE_NOT_ALLOWED', 403)
        alias, channel = text(data.get('alias', ''), False, 60), text(data.get('channel', '이메일'), True, 40)
        payload_hash = digest([clean, email, site, alias, channel])
        with self.db:
            prior = self.db.execute('SELECT id,payload_hash FROM cases WHERE client_id=? AND idempotency_key=?', (actor.client_id, key)).fetchone()
            if prior:
                require(prior['payload_hash'] == payload_hash, 'IDEMPOTENCY_CONFLICT', 409)
                return {'id': prior['id'], 'duplicate': True}
            case_id, timestamp = uid('CASE'), now()
            self.db.execute('INSERT INTO cases(id,client_id,site_id,created_at,updated_at,state,revision,answers,idempotency_key,payload_hash,owner,next_action,due,notice) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                            (case_id, actor.client_id, site, timestamp, timestamp, 'received', 1, dumps(clean), key, payload_hash,
                             '미배정', '기본 검토 담당 배정', '', '접수 기록만 완료. 인터뷰·계약 확정 아님'))
            self.db.execute('INSERT INTO private.contacts VALUES (?,?,?,?)', (case_id, email, alias, channel))
            self.event(actor, case_id, 'received', {'question_version': 'v2-I01-I09'}, bump=False)
        return {'id': case_id, 'duplicate': False}

    def list_cases(self, actor):
        require(actor.role in ('operator', 'client'), 'AUTH_REQUIRED', 401)
        query = 'SELECT id,client_id,site_id,state,revision,created_at,updated_at,owner,next_action,due,notice FROM cases'
        rows = self.db.execute(query + (' ORDER BY created_at DESC' if actor.role == 'operator' else ' WHERE client_id=? ORDER BY created_at DESC'),
                               () if actor.role == 'operator' else (actor.client_id,)).fetchall()
        return [dict(r) for r in rows]

    def detail(self, actor, case_id):
        case = self.case(actor, case_id)
        case['answers'] = json.loads(case['answers'])
        case['interview'] = json.loads(case['interview']) if case['interview'] else None
        for table in ('tasks', 'claims', 'evidence', 'modules', 'goals', 'experiments', 'reports', 'events', 'work_logs'):
            records = [dict(r) for r in self.db.execute(f'SELECT * FROM {table} WHERE case_id=?', (case_id,))]
            for r in records:
                for field in ('body', 'detail', 'observations', 'decision'):
                    if r.get(field):
                        r[field] = json.loads(r[field])
                if table == 'reports':
                    r['stale'] = r['fingerprint'] != self.fingerprint(case_id)
            case[table] = records
        if actor.role == 'client':
            case['reports'] = [r for r in case['reports'] if r['state'] == 'approved' and not r['stale']]
        # No contact values or client tokens in ordinary dashboard/portal responses.
        return case

    def contact(self, actor, case_id):
        self.case(actor, case_id, operator=True)
        return dict(self.db.execute('SELECT * FROM private.contacts WHERE case_id=?', (case_id,)).fetchone())

    def transition(self, actor, case_id, target, expected, owner, next_action, due, notice):
        with self.db:
            case = self.case(actor, case_id, operator=True)
            self.version(case, expected)
            require(target in TRANSITIONS[case['state']], 'INVALID_TRANSITION', 409)
            owner, next_action, notice = text(owner), text(next_action), text(notice)
            due = iso_date(due)
            if target == 'in_progress':
                self.agreed(case_id)
            if target == 'closed' and case['state'] == 'in_progress':
                require(self.ready_to_handover(case_id), 'HANDOVER_NOT_READY', 409)
            self.db.execute('UPDATE cases SET state=?,owner=?,next_action=?,due=?,notice=? WHERE id=?', (target, owner, next_action, due, notice, case_id))
            if target == 'interview_scheduled':
                self.db.execute('INSERT OR IGNORE INTO tasks VALUES (?,?,?,?,?,?)', (uid('TASK'), case_id, 'interview', owner, due, 'open'))
            self.event(actor, case_id, 'state_changed', {'from': case['state'], 'to': target, 'notice_recorded_only': True})

    def interview(self, actor, case_id, answers, expected):
        with self.db:
            case = self.case(actor, case_id, operator=True)
            self.version(case, expected)
            require(case['state'] == 'interview_scheduled', 'INTERVIEW_NOT_SCHEDULED', 409)
            require(set(answers) == {q[0] for q in INTERVIEW}, 'INTERVIEW_FIELDS_REQUIRED')
            clean = {k: text(v) for k, v in answers.items()}
            self.db.execute('UPDATE cases SET interview=?,state=?,interview_confirmed=0 WHERE id=?', (dumps(clean), 'interview_done', case_id))
            self.db.execute('UPDATE tasks SET state=? WHERE case_id=? AND kind=?', ('done', case_id, 'interview'))
            self.event(actor, case_id, 'interview_recorded', {'source': 'v2-U01-U13', 'confirmation': 'pending'})

    def confirm_interview(self, actor, case_id):
        with self.db:
            case = self.case(actor, case_id)
            require(actor.role == 'client' and case['interview'] is not None, 'CLIENT_CONFIRMATION_REQUIRED', 403)
            require(not case['interview_confirmed'], 'ALREADY_CONFIRMED', 409)
            self.db.execute('UPDATE cases SET interview_confirmed=1 WHERE id=?', (case_id,))
            self.event(actor, case_id, 'interview_confirmed', {'meaning': '사실관계 확인만; 합성 시험' })

    def diagnose(self, actor, case_id, selections, expected):
        with self.db:
            case = self.case(actor, case_id, operator=True)
            self.version(case, expected)
            require(case['interview_confirmed'], 'INTERVIEW_CONFIRMATION_REQUIRED', 409)
            require(isinstance(selections, list) and 1 <= len(selections) <= 2, 'SELECT_ONE_OR_TWO_MODULES')
            require(len({s.get('code') for s in selections}) == len(selections), 'DUPLICATE_MODULE')
            for selection in selections:
                require(selection.get('code') in MODULES, 'UNKNOWN_MODULE')
                clean = {field: text(selection.get(field, '')) for field in ('reason', 'known', 'answer', 'material_request', 'fallback', 'unknown', 'next_judgment')}
                self.db.execute('INSERT INTO modules VALUES (?,?,?) ON CONFLICT(case_id,code) DO UPDATE SET body=excluded.body', (case_id, selection['code'], dumps(clean)))
            # Replacing chosen modules is explicit and logged; old versions remain in events.
            self.db.execute('DELETE FROM modules WHERE case_id=? AND code NOT IN (' + ','.join('?' for _ in selections) + ')', (case_id, *(s['code'] for s in selections)))
            self.event(actor, case_id, 'diagnosis_selected', {'selections': selections})

    def add_evidence(self, actor, case_id, body):
        with self.db:
            self.case(actor, case_id, operator=True)
            clean = {k: text(body.get(k, '')) for k in ('label', 'excerpt', 'source_version')}
            clean['observed_on'] = iso_date(body.get('observed_on'))
            evidence_id = uid('EVIDENCE')
            self.db.execute('INSERT INTO evidence VALUES (?,?,?,?,?)', (evidence_id, case_id, dumps(clean), digest(clean), actor.id))
            self.event(actor, case_id, 'evidence_reviewed', {'evidence_id': evidence_id, 'digest': digest(clean)})
        return evidence_id

    def add_claim(self, actor, case_id, kind, body):
        with self.db:
            self.case(actor, case_id, operator=True)
            require(kind in ('F', 'T', 'H', 'U'), 'INVALID_CLAIM_KIND')
            clean = {'statement': text(body.get('statement', ''))}
            if kind == 'F':
                ref = body.get('evidence_id')
                require(self.db.execute('SELECT 1 FROM evidence WHERE id=? AND case_id=?', (ref, case_id)).fetchone() is not None, 'REVIEWED_EVIDENCE_REQUIRED')
                clean['evidence_id'] = ref
            if kind == 'T':
                clean.update(role=text(body.get('role', '')), said_on=iso_date(body.get('said_on')))
            if kind == 'H':
                clean['falsification'] = text(body.get('falsification', ''))
            if kind == 'U':
                clean['next_question'] = text(body.get('next_question', ''))
            clean['conflict_with'] = text(body.get('conflict_with', ''), False, 100)
            if clean['conflict_with']:
                require(self.db.execute('SELECT 1 FROM claims WHERE id=? AND case_id=?', (clean['conflict_with'], case_id)).fetchone() is not None, 'CONFLICT_CLAIM_NOT_FOUND')
            claim_id = uid('CLAIM')
            self.db.execute('INSERT INTO claims VALUES (?,?,?,?)', (claim_id, case_id, kind, dumps(clean)))
            self.event(actor, case_id, 'claim_recorded', {'id': claim_id, 'kind': kind})
        return claim_id

    def save_goal(self, actor, case_id, body, expected):
        with self.db:
            case = self.case(actor, case_id, operator=True)
            self.version(case, expected)
            require(case['state'] in ('interview_done', 'proposal', 'customer_decision', 'in_progress', 'hold'), 'DIAGNOSIS_REQUIRED', 409)
            require(case['interview_confirmed'] and self.db.execute('SELECT 1 FROM modules WHERE case_id=?', (case_id,)).fetchone() is not None, 'DIAGNOSIS_REQUIRED', 409)
            require(set(body) == set(GOAL_FIELDS), 'GOAL_FIELDS_REQUIRED')
            clean = {k: text(v) for k, v in body.items() if k not in ('hours', 'cost', 'revisions')}
            clean.update(hours=numeric(body['hours']), cost=numeric(body['cost']), revisions=numeric(body['revisions'], integer=True))
            require(Decimal(clean['hours']) > 0, 'HOURS_REQUIRED')
            for k in ('start', 'end', 'review_on'):
                clean[k] = iso_date(clean[k])
            require(clean['start'] <= clean['end'] <= clean['review_on'], 'GOAL_DATE_ORDER')
            require(clean['metric'] in ('missed_handover:v1:건:sum', 'handling_minutes:v1:분:sum'), 'REGISTERED_METRIC_REQUIRED')
            version = self.db.execute('SELECT COALESCE(MAX(version),0)+1 FROM goals WHERE case_id=?', (case_id,)).fetchone()[0]
            agreement_digest = digest({'goal': clean, 'basis': self.diagnostic_basis(case_id)})
            self.db.execute('INSERT INTO goals(case_id,version,body,digest) VALUES (?,?,?,?)', (case_id, version, dumps(clean), agreement_digest))
            # Any scope revision pauses running experiments until the new agreement is approved.
            self.db.execute('UPDATE experiments SET state=? WHERE case_id=? AND state=?', ('paused_scope_change', case_id, 'running'))
            self.event(actor, case_id, 'goal_version_created', {'version': version, 'digest': agreement_digest})
        return version

    def latest_goal(self, case_id):
        row = self.db.execute('SELECT * FROM goals WHERE case_id=? ORDER BY version DESC LIMIT 1', (case_id,)).fetchone()
        require(row is not None, 'GOAL_REQUIRED', 409)
        return dict(row)

    def approve_goal(self, actor, case_id, version, expected_digest):
        with self.db:
            self.case(actor, case_id)
            goal = self.latest_goal(case_id)
            require(goal['version'] == version and goal['digest'] == expected_digest, 'STALE_GOAL', 409)
            self.check_goal_basis(case_id, goal)
            column = 'lab_approved' if actor.role == 'operator' else 'client_approved'
            require(not goal[column], 'ALREADY_APPROVED', 409)
            self.db.execute(f'UPDATE goals SET {column}=1 WHERE case_id=? AND version=?', (case_id, version))
            self.event(actor, case_id, 'goal_approved', {'version': version, 'digest': expected_digest, 'side': actor.role})

    def agreed(self, case_id):
        goal = self.latest_goal(case_id)
        self.check_goal_basis(case_id, goal)
        require(goal['lab_approved'] and goal['client_approved'], 'DUAL_APPROVAL_REQUIRED', 409)
        return goal

    def diagnostic_basis(self, case_id):
        case = self.db.execute('SELECT answers,interview,interview_confirmed FROM cases WHERE id=?', (case_id,)).fetchone()
        basis = {'case': dict(case)}
        for table in ('claims', 'evidence', 'modules'):
            basis[table] = [dict(row) for row in self.db.execute(f'SELECT * FROM {table} WHERE case_id=? ORDER BY rowid', (case_id,))]
        return basis

    def check_goal_basis(self, case_id, goal):
        current = digest({'goal': json.loads(goal['body']), 'basis': self.diagnostic_basis(case_id)})
        require(current == goal['digest'], 'GOAL_BASIS_CHANGED', 409)

    def create_experiment(self, actor, case_id, body):
        with self.db:
            case = self.case(actor, case_id, operator=True)
            require(case['state'] == 'in_progress', 'PROJECT_NOT_STARTED', 409)
            goal = self.agreed(case_id)
            clean = {k: text(body.get(k, '')) for k in ('problem', 'hypothesis_id', 'reason', 'action', 'owner', 'user_role', 'risk', 'rollback', 'check_on')}
            clean['check_on'] = iso_date(clean['check_on'])
            require(self.db.execute('SELECT 1 FROM claims WHERE id=? AND case_id=? AND kind=?', (clean['hypothesis_id'], case_id, 'H')).fetchone() is not None, 'HYPOTHESIS_REQUIRED')
            clean['metric'] = json.loads(goal['body'])['metric']
            experiment_id = uid('EXP')
            self.db.execute('INSERT INTO experiments(id,case_id,goal_version,body,state) VALUES (?,?,?,?,?)', (experiment_id, case_id, goal['version'], dumps(clean), 'planned'))
            self.event(actor, case_id, 'experiment_planned', {'id': experiment_id, 'goal_version': goal['version']})
        return experiment_id

    def experiment(self, actor, case_id, experiment_id):
        case = self.case(actor, case_id)
        row = self.db.execute('SELECT * FROM experiments WHERE id=? AND case_id=?', (experiment_id, case_id)).fetchone()
        require(row is not None, 'NOT_FOUND', 404)
        return case, dict(row)

    def approve_experiment(self, actor, case_id, experiment_id):
        with self.db:
            _, experiment = self.experiment(actor, case_id, experiment_id)
            require(actor.role == 'client' and experiment['state'] == 'planned', 'CLIENT_APPROVAL_REQUIRED', 403)
            require(self.agreed(case_id)['version'] == experiment['goal_version'], 'STALE_EXPERIMENT', 409)
            self.db.execute('UPDATE experiments SET client_approved=1 WHERE id=?', (experiment_id,))
            self.event(actor, case_id, 'experiment_approved', {'id': experiment_id})

    def observe(self, actor, case_id, experiment_id, body):
        with self.db:
            self.case(actor, case_id, operator=True)
            case, experiment = self.experiment(actor, case_id, experiment_id)
            require(case['state'] == 'in_progress' and experiment['state'] in ('planned', 'running') and experiment['client_approved'], 'EXECUTION_NOT_APPROVED', 409)
            require(self.agreed(case_id)['version'] == experiment['goal_version'], 'STALE_EXPERIMENT', 409)
            require(body.get('used') in ('used', 'not_used'), 'USE_STATE_REQUIRED')
            clean = {k: text(body.get(k, ''), k not in ('not_used_reason',)) for k in ('observation', 'reaction', 'side_effect', 'other_causes', 'not_used_reason')}
            clean.update(used=body['used'], observed_on=iso_date(body.get('observed_on')))
            if clean['used'] == 'not_used':
                require(bool(clean['not_used_reason']), 'NONUSE_REASON_REQUIRED')
            observations = json.loads(experiment['observations']) + [clean]
            self.db.execute('UPDATE experiments SET observations=?,state=? WHERE id=?', (dumps(observations), 'running', experiment_id))
            self.event(actor, case_id, 'use_recorded', {'experiment_id': experiment_id, 'observation': clean})

    def decide(self, actor, case_id, experiment_id, body):
        with self.db:
            _, experiment = self.experiment(actor, case_id, experiment_id)
            require(actor.role == 'client', 'CLIENT_DECISION_REQUIRED', 403)
            require(experiment['state'] in ('running', 'paused_scope_change') and json.loads(experiment['observations']), 'OBSERVATION_REQUIRED', 409)
            require(body.get('choice') in ('keep', 'modify', 'stop'), 'INVALID_DECISION')
            clean = {k: text(body.get(k, '')) for k in ('reason', 'handover', 'owner', 'next_review')}
            clean.update(choice=body['choice'], next_review=iso_date(clean['next_review']), decided_by=actor.id)
            self.db.execute('UPDATE experiments SET decision=?,state=? WHERE id=?', (dumps(clean), 'reviewed', experiment_id))
            self.event(actor, case_id, 'client_decision', {'experiment_id': experiment_id, 'decision': clean})

    def upload(self, actor, case_id, source_id, filename, content, origin, start, end, declared_unit):
        case = self.case(actor, case_id)
        require(case['state'] == 'in_progress', 'PROJECT_NOT_STARTED', 409)
        goal = self.agreed(case_id)
        require(len(content) <= MAX_BYTES, 'FILE_TOO_LARGE', 413)
        suffix = Path(filename).suffix.lower()
        require(suffix in ('.csv', '.xlsx'), 'UNSUPPORTED_FILE_TYPE')
        require(re.fullmatch(r'SYN-[A-Za-z0-9_-]{1,60}', source_id) is not None, 'SYNTHETIC_SOURCE_REQUIRED')
        require(declared_unit == json.loads(goal['body'])['metric'].split(':')[2], 'DECLARED_UNIT_MISMATCH')
        origin = text(origin)
        store = Store(self.root / 'data', case['client_id'])
        try:
            with tempfile.NamedTemporaryFile(suffix=suffix) as file:
                file.write(content); file.flush()
                # Validate scope before ingest: the existing pipeline knows the tenant,
                # while this layer also restricts the file to this case's one site/metric.
                from internal.data_mvp.pipeline import read_rows
                _, rows = read_rows(file.name)
                metric_id, definition, _, _ = json.loads(goal['body'])['metric'].split(':')
                require(all(r['site_id'] == case['site_id'] and r['metric_id'] == metric_id and r['definition_version'] == definition for r in rows), 'CASE_DATA_SCOPE_MISMATCH')
                for row in rows:
                    numeric(row['value'], integer=metric_id == 'missed_handover')
                other = self.db.execute('SELECT 1 FROM uploads u JOIN cases c ON c.id=u.case_id WHERE c.client_id=? AND u.source_id=? AND u.case_id<>?', (case['client_id'], source_id, case_id)).fetchone()
                require(other is None, 'SOURCE_OWNED_BY_OTHER_CASE', 409)
                result = store.ingest(case['client_id'], source_id, file.name, origin, start, end)
            with self.db:
                self.db.execute('INSERT OR IGNORE INTO uploads VALUES (?,?,?)', (case_id, source_id, result['version']))
                if not result['duplicate']:
                    self.event(actor, case_id, 'upload_pending', result)
            return result
        finally:
            store.close()

    def review_upload(self, actor, case_id, source_id, version, approve):
        case = self.case(actor, case_id, operator=True)
        require(self.db.execute('SELECT 1 FROM uploads WHERE case_id=? AND source_id=? AND version=?', (case_id, source_id, version)).fetchone() is not None, 'NOT_FOUND', 404)
        store = Store(self.root / 'data', case['client_id'])
        try:
            store.review(case['client_id'], source_id, version, actor.id, approve=approve)
            with self.db:
                self.event(actor, case_id, 'upload_reviewed', {'source_id': source_id, 'version': version, 'approve': approve})
        finally:
            store.close()

    def sources(self, case_id):
        case = dict(self.db.execute('SELECT * FROM cases WHERE id=?', (case_id,)).fetchone())
        store = Store(self.root / 'data', case['client_id'])
        try:
            ids = [r[0] for r in self.db.execute('SELECT DISTINCT source_id FROM uploads WHERE case_id=? ORDER BY source_id', (case_id,))]
            return [dict(store.db.execute('SELECT * FROM sources WHERE source_id=? ORDER BY version DESC LIMIT 1', (source_id,)).fetchone()) for source_id in ids]
        finally:
            store.close()

    def fingerprint(self, case_id):
        case = self.db.execute('SELECT answers,interview,interview_confirmed FROM cases WHERE id=?', (case_id,)).fetchone()
        inputs = {'case': dict(case), 'sources': self.sources(case_id)}
        for table in ('claims', 'evidence', 'modules', 'goals', 'experiments', 'work_logs', 'tasks'):
            inputs[table] = [dict(row) for row in self.db.execute(f'SELECT * FROM {table} WHERE case_id=? ORDER BY rowid', (case_id,))]
        return digest(inputs)

    def draft_report(self, actor, case_id, kind, start, end):
        case = self.case(actor, case_id, operator=True)
        goal = self.agreed(case_id)
        require(kind in ('weekly', 'monthly', 'annual'), 'INVALID_REPORT_KIND')
        start, end = iso_date(start), iso_date(end)
        require(start <= end, 'INVALID_REPORT_PERIOD')
        sources = self.sources(case_id)
        require(sources and all(s['state'] == 'approved' for s in sources), 'LATEST_SOURCES_NOT_APPROVED', 409)
        store = Store(self.root / 'data', case['client_id'])
        records, seen = [], set()
        try:
            for source in sources:
                for record in store.report(case['client_id'], source['source_id'])['records']:
                    if not start <= record['observed_on'] <= end:
                        continue
                    point = (record['site_id'], record['metric_id'], record['definition_version'], record['observed_on'])
                    require(point not in seen, 'OVERLAPPING_SOURCES', 409)
                    seen.add(point); records.append(record)
        finally:
            store.close()
        groups = {}
        for r in records:
            when = date.fromisoformat(r['observed_on'])
            period = (when - timedelta(days=when.weekday())).isoformat() if kind == 'weekly' else when.strftime('%Y-%m')
            key = (period, r['site_id'], r['metric_id'], r['definition_version'], r['unit'])
            group = groups.setdefault(key, {'period': period, 'site_id': r['site_id'], 'metric_id': r['metric_id'], 'definition_version': r['definition_version'], 'unit': r['unit'], 'definition': r['definition'], 'method': 'sum', 'total': Decimal(0), 'days': [], 'trace': []})
            group['total'] += Decimal(r['value']); group['days'].append(r['observed_on'])
            group['trace'].append({k: r[k] for k in ('source_id', 'version', 'row_key', 'observed_on', 'value')})
        output = []
        for group in groups.values():
            group['total'] = str(group['total']); group['observed_days'] = len(set(group.pop('days')))
            output.append(group)
        detail = self.detail(actor, case_id)
        body = {'synthetic_only': True, 'kind': kind, 'period_start': start, 'period_end': end,
                'goal_version': goal['version'], 'goal': json.loads(goal['body']), 'groups': output,
                'sources': sources, 'claims': detail['claims'], 'experiments': detail['experiments'],
                'work_logs': detail['work_logs'], 'tasks': detail['tasks'],
                'missing': '미측정 날짜는 0으로 채우지 않음. 기록된 날짜의 합계이며 전체 기간 합계·효과·연간 추세로 일반화하지 않음.',
                'market': '공식 경제 데이터 미연동. 관련 외부 변화는 미확인.',
                'ai': '외부 AI API 미호출. 입력값을 추적하는 결정적 보고 초안.',
                'limits': '합성 사례. 전후 차이의 원인·고객 만족·장기 지속성·매출 효과는 검증하지 않음.'}
        require(bool(records), 'NO_DATA_IN_PERIOD', 409)
        report_id = uid('REPORT')
        with self.db:
            self.db.execute('INSERT INTO reports(id,case_id,body,fingerprint,state) VALUES (?,?,?,?,?)', (report_id, case_id, dumps(body), self.fingerprint(case_id), 'draft'))
            self.event(actor, case_id, 'report_drafted', {'report_id': report_id}, bump=False)
        return report_id

    def approve_report(self, actor, case_id, report_id):
        with self.db:
            self.case(actor, case_id, operator=True)
            row = self.db.execute('SELECT * FROM reports WHERE id=? AND case_id=?', (report_id, case_id)).fetchone()
            require(row is not None, 'NOT_FOUND', 404)
            require(row['state'] == 'draft' and row['fingerprint'] == self.fingerprint(case_id), 'STALE_REPORT', 409)
            self.db.execute('UPDATE reports SET state=?,reviewer=?,approved_at=? WHERE id=?', ('approved', actor.id, now(), report_id))
            self.event(actor, case_id, 'report_approved', {'report_id': report_id}, bump=False)

    def add_work(self, actor, case_id, activity, minutes, cost):
        with self.db:
            self.case(actor, case_id, operator=True)
            self.db.execute('INSERT INTO work_logs VALUES (?,?,?,?,?,?,?)', (uid('WORK'), case_id, text(activity), int(numeric(minutes, integer=True)), numeric(cost), actor.id, now()))
            self.event(actor, case_id, 'work_logged', {'activity': activity, 'minutes': minutes})

    def ready_to_handover(self, case_id):
        experiments = self.db.execute('SELECT state,decision FROM experiments WHERE case_id=?', (case_id,)).fetchall()
        reports = self.db.execute('SELECT state,fingerprint FROM reports WHERE case_id=?', (case_id,)).fetchall()
        return bool(experiments) and all(e['state'] == 'reviewed' and e['decision'] for e in experiments) and any(r['state'] == 'approved' and r['fingerprint'] == self.fingerprint(case_id) for r in reports)
