"""Internet-facing, fixture-only rehearsal. No free text, files or real accounts.

The loopback harness stays unchanged. This WSGI app invokes the same Workflow
with server-owned fixtures, in a different temporary workspace per browser.
"""
from __future__ import annotations

import json
import os
import secrets
import sqlite3
import tempfile
import threading
import time
from dataclasses import dataclass, field
from http.cookies import SimpleCookie
from pathlib import Path
from urllib.parse import urlsplit

from . import catalog, scenario
from .workflow import CLIENT_A, CLIENT_B, OPERATOR, FlowError, Workflow, require

WEB = Path(__file__).with_name('hosted_web')
ROLES = {'operator': OPERATOR, 'client_a': CLIENT_A, 'client_b': CLIENT_B}
STEPS = [
    ('client_a', '가상 고객 접수', '준비된 9문항으로 한 가지 인계 문제를 접수합니다.'),
    ('operator', '사업 이해 인터뷰', '진행 범위를 검토하고 상품·고객·대표의 일·강점을 기록합니다.'),
    ('client_a', '인터뷰 사실 확인', '대표의 설명이 맞게 기록됐는지 가상 고객의 자리에서 확인합니다.'),
    ('operator', '근거와 가설 정리', '업무 흐름 한 영역을 선택하고 사실·진술·가설·미확인을 구분합니다.'),
    ('operator', '공동 목표 초안', '원하는 성과와 직접 제공할 결과물·역할·중단 조건을 구분합니다.'),
    ('client_a', '같은 목표 버전 승인', '가상 고객이 같은 목표와 범위를 승인해야 실행이 열립니다.'),
    ('operator', '작은 실험 계획', '한 업무의 완료 칸을 추가하는 계획과 되돌릴 방법을 기록합니다.'),
    ('client_a', '현장 적용 승인', '목표 승인과 별도로 이 실험을 적용할지 결정합니다.'),
    ('operator', '사용과 반응 기록', '사용 여부·반응·부작용·다른 원인 가능성을 남깁니다.'),
    ('client_a', '가상 집계 제출', '서버가 준비한 14일 집계만 제출합니다. 실제 파일은 받지 않습니다.'),
    ('operator', '자료 검수', '14행과 단위·출처를 열어 본 뒤 보고서 사용을 승인합니다.'),
    ('client_a', '유지·수정·중단 판단', '다른 원인과 부담을 더 확인하기 위해 수정과 다음 점검을 기록합니다.'),
    ('operator', '보고서 검수·승인', '관측된 기간으로 주간·월간·연간 형식 보고서를 만들고 검수합니다.'),
    ('operator', '인계와 종료', '합의·실험 판단·현재 승인 보고서를 확인한 뒤 종료합니다.'),
]


@dataclass
class Trial:
    temporary: tempfile.TemporaryDirectory
    expires: float
    csrf: str = field(default_factory=lambda: secrets.token_urlsafe(32))
    role: str = 'client_a'
    stage: int = 0
    case_id: str | None = None
    hypothesis_id: str | None = None
    experiment_id: str | None = None
    previewed: bool = False
    failed: bool = False

    @property
    def root(self):
        return Path(self.temporary.name)


class App:
    def __init__(self, origin, *, parent=None, ttl=3600, maximum=24):
        parts = urlsplit(origin)
        require(parts.scheme in ('https', 'http') and parts.netloc and parts.path in ('', '/'), 'INVALID_PUBLIC_ORIGIN')
        require(parts.scheme == 'https' or parts.hostname in ('127.0.0.1', 'localhost'), 'HTTPS_REQUIRED')
        self.origin, self.host = origin.rstrip('/'), parts.netloc
        self.secure = parts.scheme == 'https'
        self.cookie_name = '__Host-dl_trial' if self.secure else 'dl_trial_local'
        self.parent, self.ttl, self.maximum = parent, ttl, maximum
        self.trials = {}
        self.lock = threading.RLock()

    def close(self):
        for trial in self.trials.values():
            trial.temporary.cleanup()
        self.trials.clear()

    def sweep(self):
        # Only server-created, bounded, synthetic temporary directories expire.
        for key, trial in list(self.trials.items()):
            if trial.expires <= time.monotonic():
                trial.temporary.cleanup()
                del self.trials[key]

    def session(self, environ, mutation=False):
        cookie = SimpleCookie()
        try:
            cookie.load(environ.get('HTTP_COOKIE', ''))
            key = cookie[self.cookie_name].value
            trial = self.trials[key]
        except (KeyError, ValueError):
            raise FlowError('TRIAL_EXPIRED', 401) from None
        if mutation:
            require(secrets.compare_digest(environ.get('HTTP_X_CSRF_TOKEN', ''), trial.csrf), 'CSRF_REJECTED', 403)
        return trial

    def state(self, trial):
        flow = Workflow(trial.root)
        try:
            case = None
            if trial.case_id and trial.role != 'client_b':
                case = flow.detail(ROLES[trial.role], trial.case_id)
                case['sources'] = flow.sources(trial.case_id)
            return {'stage': trial.stage, 'role': trial.role, 'csrf': trial.csrf,
                    'expires_in': max(0, int(trial.expires - time.monotonic())),
                    'steps': STEPS, 'case': case, 'states': catalog.STATES,
                    'intake': catalog.INTAKE, 'interview_questions': catalog.INTERVIEW,
                    'goal_fields': catalog.GOAL_FIELDS, 'previewed': trial.previewed,
                    'failed': trial.failed, 'synthetic_only': True,
                    'revision': os.environ.get('RENDER_GIT_COMMIT', 'local')[:12]}
        finally:
            flow.close()

    def step(self, trial):
        require(not trial.failed, 'TRIAL_RESTART_REQUIRED', 409)
        require(trial.stage < len(STEPS), 'TRIAL_COMPLETE', 409)
        require(trial.role == STEPS[trial.stage][0], 'ROLE_REQUIRED', 403)
        if trial.stage == 10:
            require(trial.previewed, 'PREVIEW_REQUIRED', 409)
        flow = Workflow(trial.root)
        try:
            stage, case_id = trial.stage, trial.case_id
            if stage == 0:
                trial.case_id = flow.submit(CLIENT_A, scenario.intake(), 'hosted-fixture-intake-001')['id']
            elif stage == 1:
                for state in ('reviewing', 'eligible', 'interview_scheduled'):
                    scenario.step(flow, case_id, state)
                flow.interview(OPERATOR, case_id, scenario.interview(), flow.case(OPERATOR, case_id)['revision'])
            elif stage == 2:
                flow.confirm_interview(CLIENT_A, case_id)
            elif stage == 3:
                flow.diagnose(OPERATOR, case_id, scenario.diagnosis(), flow.case(OPERATOR, case_id)['revision'])
                evidence = flow.add_evidence(OPERATOR, case_id, {'label': '합성 기준표 발췌', 'excerpt': '완료 칸이 없는 합성 기준표', 'source_version': 'SYN-v1', 'observed_on': '2026-10-05'})
                flow.add_claim(OPERATOR, case_id, 'F', {'statement': '합성 기준표 발췌에 완료 칸이 없다.', 'evidence_id': evidence})
                flow.add_claim(OPERATOR, case_id, 'T', {'statement': '대표는 교대 후 다시 묻는다고 설명함.', 'role': '합성 대표', 'said_on': '2026-10-05'})
                trial.hypothesis_id = flow.add_claim(OPERATOR, case_id, 'H', {'statement': '완료 뜻의 차이가 인계 누락에 영향을 줄 수 있다.', 'falsification': '완료 기준을 같게 이해해도 같은 누락이 발생하는가?'})
                flow.add_claim(OPERATOR, case_id, 'U', {'statement': '다른 교대의 같은 문제 빈도', 'next_question': '다음 주 같은 정의로 셀 수 있는가?'})
            elif stage == 4:
                goal = scenario.goal()
                goal['data_policy'] = '가상 자료만 · 방문자별 임시 체험 · 최대 1시간 또는 서버 재시작 때 정리 · 실제 고객 동의 아님'
                version = flow.save_goal(OPERATOR, case_id, goal, flow.case(OPERATOR, case_id)['revision'])
                flow.approve_goal(OPERATOR, case_id, version, flow.latest_goal(case_id)['digest'])
            elif stage == 5:
                goal = flow.latest_goal(case_id)
                flow.approve_goal(CLIENT_A, case_id, goal['version'], goal['digest'])
            elif stage == 6:
                for state in ('proposal', 'customer_decision', 'in_progress'):
                    scenario.step(flow, case_id, state)
                trial.experiment_id = flow.create_experiment(OPERATOR, case_id, scenario.experiment(trial.hypothesis_id))
            elif stage == 7:
                flow.approve_experiment(CLIENT_A, case_id, trial.experiment_id)
            elif stage == 8:
                flow.observe(OPERATOR, case_id, trial.experiment_id, scenario.observation())
            elif stage == 9:
                flow.upload(CLIENT_A, case_id, 'SYN-handover', 'synthetic.csv', scenario.csv_data(), '가상 14일 집계 · 실제 고객 자료 없음', '2026-10-05', '2026-10-18', '건')
            elif stage == 10:
                flow.review_upload(OPERATOR, case_id, 'SYN-handover', 1, True)
            elif stage == 11:
                flow.decide(CLIENT_A, case_id, trial.experiment_id, scenario.decision())
            elif stage == 12:
                for kind in ('weekly', 'monthly', 'annual'):
                    report_id = flow.draft_report(OPERATOR, case_id, kind, '2026-10-05', '2026-10-18')
                    flow.approve_report(OPERATOR, case_id, report_id)
            elif stage == 13:
                scenario.step(flow, case_id, 'closed')
            trial.stage += 1
        except Exception:
            # Multi-DB work can partially commit. Do not claim a rollback or
            # repeat that stage blindly; offer a new isolated rehearsal.
            trial.failed = True
            raise
        finally:
            flow.close()

    def __call__(self, environ, start_response):
        headers = {'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff',
                   'Referrer-Policy': 'no-referrer', 'X-Robots-Tag': 'noindex, nofollow',
                   'Content-Security-Policy': "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'"}
        if self.secure:
            headers['Strict-Transport-Security'] = 'max-age=31536000'
        status, payload, kind = 200, {}, 'application/json; charset=utf-8'
        with self.lock:
            try:
                require(environ.get('HTTP_HOST') == self.host, 'HOST_NOT_ALLOWED', 403)
                method, path = environ.get('REQUEST_METHOD'), environ.get('PATH_INFO')
                require(method in ('GET', 'POST'), 'METHOD_NOT_ALLOWED', 405)
                self.sweep()
                if method == 'GET' and path == '/health':
                    payload = {'ok': True, 'mode': 'fixture-only', 'revision': os.environ.get('RENDER_GIT_COMMIT', 'local')[:12]}
                elif method == 'GET' and path in ('/', '/app.css', '/trial.css', '/trial.js', '/robots.txt'):
                    file, kind = {'/': ('index.html', 'text/html; charset=utf-8'), '/trial.js': ('trial.js', 'text/javascript; charset=utf-8'), '/app.css': ('app.css', 'text/css; charset=utf-8'), '/trial.css': ('trial.css', 'text/css; charset=utf-8'), '/robots.txt': ('robots.txt', 'text/plain; charset=utf-8')}[path]
                    asset = Path(__file__).with_name('web') / file if file == 'app.css' else WEB / file
                    payload = asset.read_bytes()
                elif path in ('/api/trial', '/api/preview') and method == 'GET':
                    trial = self.session(environ)
                    if path == '/api/preview':
                        require(trial.role == 'operator' and trial.stage == 10, 'PREVIEW_NOT_AVAILABLE', 403)
                        flow = Workflow(trial.root)
                        try:
                            payload = flow.preview_upload(OPERATOR, trial.case_id, 'SYN-handover', 1)
                            trial.previewed = True
                        finally:
                            flow.close()
                    else:
                        payload = self.state(trial)
                elif method == 'POST' and path in ('/api/start', '/api/role', '/api/step'):
                    require(environ.get('HTTP_ORIGIN') == self.origin, 'ORIGIN_REJECTED', 403)
                    require(environ.get('CONTENT_TYPE', '').split(';')[0] == 'application/json', 'JSON_REQUIRED', 415)
                    length = int(environ.get('CONTENT_LENGTH') or -1)
                    require(0 < length <= 512, 'REQUEST_TOO_LARGE', 413)
                    data = json.loads(environ['wsgi.input'].read(length))
                    require(isinstance(data, dict), 'OBJECT_REQUIRED')
                    if path == '/api/start':
                        require(data == {'ack': True}, 'FIXTURE_ONLY')
                        require(len(self.trials) < self.maximum, 'TRIAL_CAPACITY', 429)
                        trial = Trial(tempfile.TemporaryDirectory(prefix='dl-trial-', dir=self.parent), time.monotonic() + self.ttl)
                        flow = Workflow(trial.root)
                        try:
                            flow.provision()
                        except Exception:
                            trial.temporary.cleanup()
                            raise
                        finally:
                            flow.close()
                        key = secrets.token_urlsafe(32)
                        self.trials[key] = trial
                        headers['Set-Cookie'] = f'{self.cookie_name}={key}; Path=/; HttpOnly; SameSite=Strict; Max-Age={self.ttl}' + ('; Secure' if self.secure else '')
                    else:
                        trial = self.session(environ, True)
                        if path == '/api/role':
                            require(set(data) == {'role'} and data['role'] in ROLES, 'INVALID_ROLE')
                            trial.role = data['role']
                        else:
                            require(set(data) == {'stage'} and type(data['stage']) is int, 'FIXTURE_ONLY')
                            # Retries after a lost success response read the already
                            # committed stage instead of performing it a second time.
                            require(data['stage'] <= trial.stage, 'STALE_STAGE', 409)
                            if data['stage'] == trial.stage:
                                self.step(trial)
                    payload = self.state(trial)
                else:
                    raise FlowError('NOT_FOUND', 404)
            except FlowError as exc:
                status, payload = exc.status, {'error': exc.code, 'completed': False}
            except (json.JSONDecodeError, UnicodeError, ValueError, TypeError):
                status, payload = 400, {'error': 'INVALID_REQUEST', 'completed': False}
            except (sqlite3.Error, OSError):
                status, payload = 503, {'error': 'TRIAL_RESTART_REQUIRED', 'completed': False}
            except Exception:
                status, payload = 500, {'error': 'TRIAL_RESTART_REQUIRED', 'completed': False}
        raw = json.dumps(payload, ensure_ascii=False).encode() if kind.startswith('application/json') else payload
        headers.update({'Content-Type': kind, 'Content-Length': str(len(raw))})
        phrase = {200: 'OK', 400: 'Bad Request', 401: 'Unauthorized', 403: 'Forbidden', 404: 'Not Found', 405: 'Method Not Allowed', 409: 'Conflict', 413: 'Payload Too Large', 415: 'Unsupported Media Type', 429: 'Too Many Requests', 500: 'Internal Server Error', 503: 'Service Unavailable'}[status]
        start_response(f'{status} {phrase}', list(headers.items()))
        return [raw]


if __name__ == '__main__':
    from waitress import serve

    origin = os.environ.get('RENDER_EXTERNAL_URL') or os.environ.get('DL_TRIAL_ORIGIN', '')
    app = App(origin)
    try:
        serve(app, host='0.0.0.0', port=int(os.environ.get('PORT', '10000')),
              threads=4, max_request_body_size=512, channel_timeout=30,
              clear_untrusted_proxy_headers=True)
    finally:
        app.close()
