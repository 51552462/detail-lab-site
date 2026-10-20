import base64
import http.client
import json
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from internal.ops_mvp.server import TestServer
from internal.ops_mvp.workflow import OPERATOR, CLIENT_A, CLIENT_B
from internal.ops_mvp import scenario


class HTTPTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.server = TestServer(self.temp.name, credentials={'operator-test': OPERATOR, 'client-a-test': CLIENT_A, 'client-b-test': CLIENT_B})
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True); self.thread.start()
        self.port = self.server.server_port; self.origin = f'http://127.0.0.1:{self.port}'
        self.cookie = ''; self.csrf = ''

    def tearDown(self):
        self.server.shutdown(); self.server.server_close(); self.thread.join(); self.temp.cleanup()

    def request(self, method, path, data=None, headers=None):
        conn = http.client.HTTPConnection('127.0.0.1', self.port, timeout=5)
        payload = None if data is None else json.dumps(data)
        extra = {'Origin': self.origin, 'Cookie': self.cookie, 'X-CSRF-Token': self.csrf}
        if data is not None: extra['Content-Type'] = 'application/json'
        extra.update(headers or {})
        conn.request(method, path, payload, extra); response = conn.getresponse(); raw = response.read()
        result = (response.status, json.loads(raw) if response.getheader('Content-Type','').startswith('application/json') else raw, dict(response.getheaders()))
        conn.close(); return result

    def login(self, token='client-a-test'):
        status, data, headers = self.request('POST', '/api/login', {'token': token})
        self.assertEqual(status, 200); self.cookie = headers['Set-Cookie'].split(';')[0]; self.csrf = data['csrf']
        return headers

    def submit(self):
        self.login(); status, data, _ = self.request('POST','/api/cases',scenario.intake(),{'Idempotency-Key':'synthetic-http-key-001'})
        self.assertEqual(status, 201); return data['id']

    def test_unauthenticated_reads_and_mutations_denied(self):
        self.assertEqual(self.request('GET','/api/cases')[0],401)
        self.assertEqual(self.request('POST','/api/cases',scenario.intake())[0],401)

    def test_session_cookie_and_revocation(self):
        headers=self.login(); self.assertIn('HttpOnly',headers['Set-Cookie']);self.assertIn('SameSite=Strict',headers['Set-Cookie'])
        self.server.revoked = {CLIENT_A.id}
        self.assertEqual(self.request('GET','/api/cases')[0],401)

    def test_csrf_origin_and_dns_rebinding_blocked(self):
        self.login()
        self.assertEqual(self.request('POST','/api/cases',scenario.intake(),{'X-CSRF-Token':'wrong'})[0],403)
        self.assertEqual(self.request('POST','/api/cases',scenario.intake(),{'Origin':'https://other.invalid'})[0],403)
        self.assertEqual(self.request('GET','/api/session',headers={'Host':'other.invalid'})[0],403)

    def test_client_cannot_read_other_case_contact_or_role_override(self):
        case=self.submit()
        self.assertEqual(self.request('GET',f'/api/cases/{case}/contact')[0],403)
        self.assertEqual(self.request('POST',f'/api/cases/{case}/state',{'target':'reviewing','role':'operator'})[0],403)
        self.login('client-b-test')
        self.assertEqual(self.request('GET',f'/api/cases/{case}')[0],404)
        self.assertEqual(self.request('GET','/api/cases')[1]['cases'],[])

    def test_duplicate_post_and_missing_key(self):
        case=self.submit()
        self.assertEqual(self.request('POST','/api/cases',scenario.intake(),{'Idempotency-Key':'synthetic-http-key-001'})[1],{'id':case,'duplicate':True})
        self.assertEqual(self.request('POST','/api/cases',scenario.intake())[0],400)

    def test_no_raw_file_download_or_internal_path(self):
        self.login()
        for path in ['/contacts.sqlite3','/../contacts.sqlite3','/internal/ops_mvp/workflow.py','/api/files/SYN-guessed']:
            self.assertEqual(self.request('GET',path)[0],404)

    def test_html_assets_security_headers(self):
        status, body, headers=self.request('GET','/')
        self.assertEqual(status,200);self.assertIn('실고객 입력 금지'.encode(),body)
        self.assertIn("frame-ancestors 'none'",headers['Content-Security-Policy'])
        self.assertEqual(headers['Cache-Control'],'no-store')
        self.assertEqual(self.server.server_address[0],'127.0.0.1')

    def test_rate_limit(self):
        for _ in range(10):self.request('POST','/api/login',{'token':'incorrect'})
        self.assertEqual(self.request('POST','/api/login',{'token':'incorrect'})[0],429)

    def test_expired_session(self):
        self.login()
        for s in self.server.sessions.values():s['expires']=time.monotonic()-1
        self.assertEqual(self.request('GET','/api/session')[0],401)

    def test_logout_invalidates_cookie(self):
        self.login(); self.assertEqual(self.request('POST','/api/logout',{})[0],200)
        self.assertEqual(self.request('GET','/api/cases')[0],401)

    def test_storage_failure_does_not_claim_success_or_echo_input(self):
        self.login()
        with patch('internal.ops_mvp.server.Workflow',side_effect=OSError('SENSITIVE VALUE')):
            status,data,_=self.request('POST','/api/cases',scenario.intake())
        self.assertEqual(status,503);self.assertFalse(data['completed']);self.assertNotIn('SENSITIVE',json.dumps(data))
        self.assertNotIn('owner@example.invalid',json.dumps(self.server.safe_logs))
        self.assertNotIn('client-a-test',json.dumps(self.server.safe_logs))

    def test_oversized_content_length_rejected_before_read(self):
        self.login()
        conn = http.client.HTTPConnection('127.0.0.1', self.port, timeout=5)
        conn.putrequest('POST', '/api/cases')
        for k,v in {'Origin':self.origin,'Cookie':self.cookie,'X-CSRF-Token':self.csrf,'Content-Type':'application/json','Content-Length':'2800001'}.items(): conn.putheader(k,v)
        conn.endheaders()
        try:
            response=conn.getresponse();self.assertEqual(response.status,413);response.read()
        finally:conn.close()

    def test_interrupted_request_is_not_receipt(self):
        import socket
        self.login()
        conn=http.client.HTTPConnection('127.0.0.1',self.port,timeout=5)
        conn.putrequest('POST','/api/cases')
        for k,v in {'Origin':self.origin,'Cookie':self.cookie,'X-CSRF-Token':self.csrf,'Content-Type':'application/json','Content-Length':'100'}.items():conn.putheader(k,v)
        conn.endheaders();conn.send(b'{');conn.sock.shutdown(socket.SHUT_WR)
        try:
            response=conn.getresponse();self.assertEqual(response.status,400)
            self.assertEqual(json.loads(response.read())['error'],'INTERRUPTED_REQUEST')
        finally:conn.close()
        self.assertEqual(self.request('GET','/api/cases')[1]['cases'],[])


if __name__=='__main__':unittest.main()
