import io
import json
import tempfile
import unittest
from unittest.mock import patch

from internal.ops_mvp.hosted import App, STEPS


class HostedTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.app = App('https://trial.example.invalid', parent=self.temp.name)
        self.cookie, self.csrf = '', ''

    def tearDown(self):
        self.app.close()
        self.temp.cleanup()

    def request(self, path, data=None, **overrides):
        raw = json.dumps(data).encode() if data is not None else b''
        environ = {'REQUEST_METHOD': 'POST' if data is not None else 'GET', 'PATH_INFO': path,
                   'HTTP_HOST': self.app.host, 'HTTP_ORIGIN': self.app.origin,
                   'HTTP_COOKIE': self.cookie, 'HTTP_X_CSRF_TOKEN': self.csrf,
                   'CONTENT_TYPE': 'application/json', 'CONTENT_LENGTH': str(len(raw)),
                   'wsgi.input': io.BytesIO(raw)}
        environ.update(overrides)
        received = {}
        def start(status, headers):
            received.update(status=int(status.split()[0]), headers=dict(headers))
        body = b''.join(self.app(environ, start))
        received['body'] = json.loads(body) if received['headers']['Content-Type'].startswith('application/json') else body
        return received

    def begin(self):
        response = self.request('/api/start', {'ack': True})
        self.assertEqual(response['status'], 200)
        self.cookie = response['headers']['Set-Cookie'].split(';')[0]
        self.csrf = response['body']['csrf']
        return response

    def switch(self, role):
        self.assertEqual(self.request('/api/role', {'role': role})['status'], 200)

    def test_fixture_flow_through_closed_and_approved_reports(self):
        self.begin()
        for stage, (role, _, _) in enumerate(STEPS):
            self.switch(role)
            if stage == 10:
                self.assertEqual(self.request('/api/step', {'stage': stage})['status'], 409)
                preview = self.request('/api/preview')['body']
                self.assertEqual(preview['row_count'], 14)
            response = self.request('/api/step', {'stage': stage})
            self.assertEqual(response['status'], 200, response['body'])
            self.assertEqual(response['body']['stage'], stage + 1)
        result = response['body']['case']
        self.assertEqual(result['state'], 'closed')
        self.assertEqual(len(result['reports']), 3)
        self.assertTrue(all(r['state'] == 'approved' and not r['stale'] for r in result['reports']))
        self.assertEqual([str(g['total']) for g in result['reports'][0]['body']['groups']], ['21', '7'])

    def test_cookie_is_host_only_secure_and_http_only(self):
        cookie = self.begin()['headers']['Set-Cookie']
        for part in ['__Host-dl_trial=', 'Secure', 'HttpOnly', 'SameSite=Strict', 'Path=/']:
            self.assertIn(part, cookie)
        self.assertNotIn('Domain=', cookie)

    def test_no_account_key_or_file_collection_endpoints(self):
        self.begin()
        for path in ['/api/login', '/api/cases', '/api/cases/SYN-guessed/uploads', '/contacts.sqlite3', '/internal/ops_mvp/hosted.py', '/../schema.sql']:
            self.assertEqual(self.request(path, {'email': 'private@example.com'})['status'], 404)
        self.assertEqual(self.request('/api/start', {'ack': True, 'email': 'private@example.com'})['status'], 400)
        self.assertEqual(self.request('/api/step', {'stage': 0, 'answers': {'I04': 'private text'}})['status'], 400)

    def test_sessions_and_other_customer_role_have_no_shared_case(self):
        self.begin()
        self.request('/api/step', {'stage': 0})
        first_cookie, first_csrf = self.cookie, self.csrf
        self.begin()
        self.assertIsNone(self.request('/api/trial')['body']['case'])
        self.cookie, self.csrf = first_cookie, first_csrf
        self.switch('client_b')
        self.assertIsNone(self.request('/api/trial')['body']['case'])
        self.assertEqual(self.request('/api/step', {'stage': 1})['status'], 403)
        self.switch('operator')
        self.assertIsNotNone(self.request('/api/trial')['body']['case'])

    def test_replayed_stage_does_not_duplicate_receipt(self):
        self.begin()
        first = self.request('/api/step', {'stage': 0})['body']
        second = self.request('/api/step', {'stage': 0})['body']
        self.assertEqual(first['case']['id'], second['case']['id'])
        self.assertEqual(len(second['case']['events']), 1)
        self.assertEqual(self.request('/api/step', {'stage': 3})['status'], 409)

    def test_origin_host_csrf_and_anonymous_requests(self):
        self.assertEqual(self.request('/api/trial')['status'], 401)
        self.assertEqual(self.request('/api/start', {'ack': True}, HTTP_ORIGIN='https://other.invalid')['status'], 403)
        self.assertEqual(self.request('/health', HTTP_HOST='other.invalid')['status'], 403)
        self.begin()
        self.assertEqual(self.request('/api/step', {'stage': 0}, HTTP_X_CSRF_TOKEN='wrong')['status'], 403)
        self.assertEqual(self.request('/api/trial', HTTP_COOKIE='__Host-dl_trial=forged')['status'], 401)

    def test_expiry_reclaims_only_created_trial(self):
        self.begin()
        trial = next(iter(self.app.trials.values()))
        root = trial.root
        trial.expires = 0
        self.assertEqual(self.request('/api/trial')['status'], 401)
        self.assertFalse(root.exists())
        self.assertTrue(self.temp.name)

    def test_bounded_capacity_and_request_size(self):
        self.app.maximum = 1
        self.begin()
        self.assertEqual(self.request('/api/start', {'ack': True})['status'], 429)
        self.assertEqual(self.request('/api/start', {'ack': True}, CONTENT_LENGTH='513')['status'], 413)
        self.assertEqual(self.request('/api/start', {'ack': True}, CONTENT_TYPE='text/plain')['status'], 415)

    def test_partial_failure_is_not_reported_as_success(self):
        self.begin()
        with patch.object(self.app, 'step', side_effect=OSError('secret path')):
            response = self.request('/api/step', {'stage': 0})
        self.assertEqual(response['status'], 503)
        self.assertFalse(response['body']['completed'])
        self.assertNotIn('secret', json.dumps(response['body']))

    def test_static_headers_and_readiness_no_trial_created(self):
        self.assertEqual(self.request('/health')['body']['mode'], 'fixture-only')
        self.assertEqual(len(self.app.trials), 0)
        html = self.request('/')
        self.assertIn('실제 이름'.encode(), html['body'])
        self.assertIn("frame-ancestors 'none'", html['headers']['Content-Security-Policy'])
        self.assertEqual(html['headers']['Cache-Control'], 'no-store')
        self.assertEqual(self.request('/robots.txt')['body'], b'User-agent: *\nDisallow: /\n')


if __name__ == '__main__':
    unittest.main()
