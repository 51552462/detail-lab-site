"""Synthetic-only loopback HTTP harness. Never expose with a tunnel/reverse proxy."""
from __future__ import annotations

import argparse
import base64
import binascii
import hashlib
import json
import os
import secrets
import sqlite3
import time
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from . import catalog, scenario
from .workflow import Workflow, FlowError, DataError, OPERATOR, CLIENT_A, CLIENT_B, require

ASSETS = Path(__file__).with_name('web')
MAX_REQUEST = 2_800_000
SESSION_SECONDS = 900


class TestServer(HTTPServer):
    def __init__(self, root, port=0, credentials=None):
        self.root = Path(root).resolve()
        require(not self.root.is_relative_to(Path(__file__).resolve().parents[2]), 'RUNTIME_OUTSIDE_REPOSITORY_REQUIRED')
        flow = Workflow(self.root); flow.provision(); flow.close()
        self.profiles = credentials or {secrets.token_urlsafe(32): actor for actor in (OPERATOR, CLIENT_A, CLIENT_B)}
        self.sessions, self.limits, self.safe_logs = {}, {}, []
        super().__init__(('127.0.0.1', port), Handler)
        self.timeout = 5

    def rate(self, scope, maximum):
        timestamp = time.monotonic()
        entries = [t for t in self.limits.get(scope, []) if timestamp - t < 60]
        require(len(entries) < maximum, 'RATE_LIMITED', 429)
        self.limits[scope] = entries + [timestamp]


class Handler(BaseHTTPRequestHandler):
    server_version = 'DetailLabSyntheticTest/0.1'

    def log_message(self, *args):
        pass  # No payload, contact, token, query string, or request-body logging.

    def send(self, status, payload, kind='application/json; charset=utf-8', cookie=None):
        raw = json.dumps(payload, ensure_ascii=False, allow_nan=False).encode() if kind.startswith('application/json') else payload
        self.send_response(status)
        for key, value in {
            'Content-Type': kind, 'Content-Length': str(len(raw)), 'Cache-Control': 'no-store',
            'X-Content-Type-Options': 'nosniff', 'Referrer-Policy': 'no-referrer',
            'Content-Security-Policy': "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'",
        }.items():
            self.send_header(key, value)
        if cookie:
            self.send_header('Set-Cookie', cookie)
        self.end_headers(); self.wfile.write(raw)

    def host(self):
        host = self.headers.get('Host', '')
        allowed = {f'127.0.0.1:{self.server.server_port}', f'localhost:{self.server.server_port}'}
        require(host in allowed, 'HOST_NOT_ALLOWED', 403)
        return host

    def session(self, mutation=False):
        cookie = SimpleCookie()
        try:
            cookie.load(self.headers.get('Cookie', ''))
            sid = cookie['dl_syn_session'].value if 'dl_syn_session' in cookie else ''
        except Exception:
            raise FlowError('AUTH_REQUIRED', 401) from None
        current = self.server.sessions.get(sid)
        require(current is not None and current['expires'] > time.monotonic(), 'AUTH_REQUIRED', 401)
        require(current['actor'].id not in getattr(self.server, 'revoked', set()), 'AUTH_REVOKED', 401)
        if mutation:
            require(secrets.compare_digest(self.headers.get('X-CSRF-Token', ''), current['csrf']), 'CSRF_REJECTED', 403)
        return sid, current

    def body(self):
        require(self.headers.get('Content-Type', '').split(';')[0] == 'application/json', 'JSON_REQUIRED', 415)
        try:
            length = int(self.headers.get('Content-Length', '-1'))
        except ValueError:
            raise FlowError('CONTENT_LENGTH_REQUIRED', 411) from None
        require(0 <= length <= MAX_REQUEST, 'REQUEST_TOO_LARGE', 413)
        require(not self.headers.get('Transfer-Encoding'), 'CHUNKED_NOT_SUPPORTED', 400)
        self.connection.settimeout(5)
        raw = self.rfile.read(length)
        require(len(raw) == length, 'INTERRUPTED_REQUEST')
        try:
            result = json.loads(raw)
        except (ValueError, UnicodeError):
            raise FlowError('INVALID_JSON') from None
        require(isinstance(result, dict), 'OBJECT_REQUIRED')
        return result

    def do_GET(self):
        self.dispatch(False)

    def do_POST(self):
        self.dispatch(True)

    def do_OPTIONS(self):
        self.send(405, {'error': 'METHOD_NOT_ALLOWED'})

    def dispatch(self, mutation):
        flow = None
        try:
            host = self.host()
            path = urlsplit(self.path).path
            if mutation:
                require(self.headers.get('Origin') == 'http://' + host, 'ORIGIN_REJECTED', 403)
            if not mutation and path in ('/', '/app.js', '/app.css'):
                name, kind = {'/': ('index.html', 'text/html; charset=utf-8'), '/app.js': ('app.js', 'text/javascript; charset=utf-8'), '/app.css': ('app.css', 'text/css; charset=utf-8')}[path]
                self.send(200, (ASSETS / name).read_bytes(), kind); return
            require(path.startswith('/api/'), 'NOT_FOUND', 404)
            if mutation and path == '/api/login':
                self.server.rate('login', 10)
                data = self.body(); token = data.get('token', '')
                actor = next((a for secret, a in self.server.profiles.items() if isinstance(token, str) and secrets.compare_digest(secret, token)), None)
                require(actor is not None, 'AUTH_REQUIRED', 401)
                sid = secrets.token_urlsafe(32); csrf = secrets.token_urlsafe(32)
                self.server.sessions = {k: v for k, v in self.server.sessions.items() if v['expires'] > time.monotonic()}
                require(len(self.server.sessions) < 100, 'SESSION_LIMIT', 429)
                self.server.sessions[sid] = {'actor': actor, 'csrf': csrf, 'expires': time.monotonic() + SESSION_SECONDS}
                self.send(200, {'role': actor.role, 'client_id': actor.client_id, 'csrf': csrf}, cookie=f'dl_syn_session={sid}; HttpOnly; SameSite=Strict; Path=/; Max-Age={SESSION_SECONDS}'); return
            sid, session = self.session(mutation)
            actor = session['actor']
            if mutation and path == '/api/logout':
                del self.server.sessions[sid]
                self.send(200, {'ok': True}, cookie='dl_syn_session=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0'); return
            if not mutation and path == '/api/session':
                self.send(200, {'role': actor.role, 'client_id': actor.client_id, 'csrf': session['csrf']}); return
            flow = Workflow(self.server.root)
            if not mutation and path == '/api/catalog':
                sites = [dict(r) for r in flow.db.execute('SELECT * FROM sites' + ('' if actor.role == 'operator' else ' WHERE client_id=?'), () if actor.role == 'operator' else (actor.client_id,))]
                self.send(200, {'intake': catalog.INTAKE, 'interview': catalog.INTERVIEW, 'modules': catalog.MODULES,
                               'states': catalog.STATES, 'transitions': catalog.TRANSITIONS, 'goal_fields': catalog.GOAL_FIELDS,
                               'sources': catalog.SOURCE_NOTION, 'sites': sites,
                               'fixtures': {'intake': scenario.intake(actor.client_id or 'SYN-A'), 'interview': scenario.interview(),
                                            'diagnosis': scenario.diagnosis(), 'goal': scenario.goal(), 'observation': scenario.observation(),
                                            'decision': scenario.decision(), 'csv': scenario.csv_data(actor.client_id or 'SYN-A').decode()}}); return
            if path == '/api/cases':
                if mutation:
                    self.server.rate(actor.id + ':submit', 5)
                    data = self.body()
                    result = flow.submit(actor, data, self.headers.get('Idempotency-Key', ''))
                    self.send(200 if result['duplicate'] else 201, result)
                else:
                    self.send(200, {'cases': flow.list_cases(actor)})
                return
            parts = path.strip('/').split('/')
            require(len(parts) >= 3 and parts[:2] == ['api', 'cases'], 'NOT_FOUND', 404)
            case_id = parts[2]
            flow.case(actor, case_id)
            action = '/'.join(parts[3:])
            if not mutation:
                if action == '':
                    result = flow.detail(actor, case_id); result['sources'] = flow.sources(case_id)
                    self.send(200, result)
                elif action == 'contact':
                    self.send(200, flow.contact(actor, case_id))
                elif len(parts) == 7 and parts[3] == 'uploads' and parts[6] == 'preview':
                    self.send(200, flow.preview_upload(actor, case_id, parts[4], int(parts[5])))
                else:
                    raise FlowError('NOT_FOUND', 404)
                return
            data = self.body()
            if action == 'state':
                flow.transition(actor, case_id, data.get('target'), data.get('revision'), data.get('owner'), data.get('next_action'), data.get('due'), data.get('notice'))
            elif action == 'interview':
                flow.interview(actor, case_id, data.get('answers', {}), data.get('revision'))
            elif action == 'interview/confirm':
                flow.confirm_interview(actor, case_id)
            elif action == 'diagnosis':
                flow.diagnose(actor, case_id, data.get('selections'), data.get('revision'))
            elif action == 'evidence':
                self.send(201, {'id': flow.add_evidence(actor, case_id, data)}); return
            elif action == 'claims':
                self.send(201, {'id': flow.add_claim(actor, case_id, data.get('kind'), data)}); return
            elif action == 'goals':
                self.send(201, {'version': flow.save_goal(actor, case_id, data.get('goal', {}), data.get('revision'))}); return
            elif action == 'goals/approve':
                flow.approve_goal(actor, case_id, data.get('version'), data.get('digest'))
            elif action == 'experiments':
                self.send(201, {'id': flow.create_experiment(actor, case_id, data)}); return
            elif action == 'experiments/approve':
                flow.approve_experiment(actor, case_id, data.get('experiment_id'))
            elif action == 'observations':
                flow.observe(actor, case_id, data.get('experiment_id'), data)
            elif action == 'decisions':
                flow.decide(actor, case_id, data.get('experiment_id'), data)
            elif action == 'uploads':
                try:
                    raw = base64.b64decode(data.get('content_base64', ''), validate=True)
                except (ValueError, binascii.Error, TypeError):
                    raise FlowError('INVALID_FILE_ENCODING') from None
                result = flow.upload(actor, case_id, data.get('source_id', ''), data.get('filename', ''), raw, data.get('origin', ''), data.get('start'), data.get('end'), data.get('unit'))
                self.send(200 if result['duplicate'] else 201, result); return
            elif action == 'uploads/review':
                require(type(data.get('approve')) is bool, 'APPROVAL_REQUIRED')
                flow.review_upload(actor, case_id, data.get('source_id'), data.get('version'), data['approve'])
            elif action == 'reports':
                self.send(201, {'id': flow.draft_report(actor, case_id, data.get('kind'), data.get('start'), data.get('end'))}); return
            elif action == 'reports/approve':
                flow.approve_report(actor, case_id, data.get('report_id'))
            elif action == 'work':
                flow.add_work(actor, case_id, data.get('activity'), data.get('minutes'), data.get('cost'))
            else:
                raise FlowError('NOT_FOUND', 404)
            self.send(200, {'ok': True})
        except FlowError as exc:
            self.server.safe_logs.append({'status': exc.status, 'code': exc.code})
            self.send(exc.status, {'error': exc.code, 'completed': False})
        except DataError as exc:
            self.server.safe_logs.append({'status': 400, 'code': 'DATA_VALIDATION_FAILED'})
            self.send(400, {'error': str(exc), 'completed': False})
        except (sqlite3.Error, OSError, TimeoutError):
            self.server.safe_logs.append({'status': 503, 'code': 'STORAGE_UNAVAILABLE'})
            self.send(503, {'error': 'STORAGE_UNAVAILABLE', 'completed': False, 'receipt_status': 'not_confirmed'})
        except (TypeError, KeyError, ValueError):
            self.server.safe_logs.append({'status': 400, 'code': 'INVALID_REQUEST'})
            self.send(400, {'error': 'INVALID_REQUEST', 'completed': False})
        finally:
            if flow:
                flow.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='SYNTHETIC ONLY. 127.0.0.1 only; no external binding option.')
    parser.add_argument('--root', required=True)
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--seed-complete-case', action='store_true')
    args = parser.parse_args()
    server = TestServer(args.root, args.port)
    if args.seed_complete_case:
        check = Workflow(args.root)
        empty = not check.list_cases(OPERATOR)
        check.close()
        if empty:
            scenario.run(args.root)
    credentials_path = Path(args.root) / 'test-credentials.json'
    credentials_path.write_text(json.dumps({actor.id: token for token, actor in server.profiles.items()}, indent=2))
    os.chmod(credentials_path, 0o600)
    print(json.dumps({'synthetic_only': True, 'url': f'http://127.0.0.1:{server.server_port}', 'test_credentials': str(credentials_path)}, ensure_ascii=False), flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
