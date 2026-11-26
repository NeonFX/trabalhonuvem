"""Testes de sondagem real HTTP e contratos da API sem dependência do PostgreSQL."""
import sys
from pathlib import Path
import socket
from threading import Thread
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
from fastapi.testclient import TestClient
import api
import probe
import worker


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response({'/ok': 200, '/bad': 503, '/redirect': 302}.get(self.path, 404))
        self.end_headers()
    def log_message(self, *args): pass


class ProbeTests(unittest.TestCase):
    def test_normalization(self):
        self.assertEqual(probe.validate_target('Exemplo.com#fragmento'), 'https://exemplo.com/')
        self.assertEqual(probe.validate_target('https://example.com/olá'), 'https://example.com/ol%C3%A1')
    def test_private_and_invalid_urls(self):
        for url in ['http://127.0.0.1', 'http://192.168.0.1', 'http://[::1]', 'file:///etc/passwd', 'http://web/secret', 'http://x.com:3000', 'http://user:pass@x.com']:
            with self.subTest(url=url), self.assertRaises(ValueError):
                probe.validate_target(url)
    def test_demo_urls(self):
        self.assertEqual(probe.validate_target('http://web/demo/online'), 'http://web/demo/online')
    def test_private_dns(self):
        with patch('probe.socket.getaddrinfo', return_value=[(socket.AF_INET,socket.SOCK_STREAM,6,'',('10.0.0.2',80))]):
            result = probe.check_url('http://example.com/')
        self.assertFalse(result.online)
        self.assertIsNone(result.status_code)
    def test_http_responses(self):
        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = Thread(target=server.serve_forever, daemon=True); thread.start()
        connect = socket.create_connection
        try:
            # O servidor local é acessado exclusivamente no teste, após simular a resolução pública.
            with patch('probe.public_address', return_value='93.184.216.34'), patch('probe.socket.create_connection', side_effect=lambda addr,timeout,source_address=None: connect(server.server_address,timeout,source_address)):
                for path, expected, status in [('ok',True,200),('bad',False,503),('redirect',True,302),('missing',False,404)]:
                    with self.subTest(path=path):
                        result=probe.check_url(f'http://example.com/{path}')
                        self.assertEqual((result.online,result.status_code),(expected,status))
                        self.assertGreaterEqual(result.latency_ms,0)
        finally:
            server.shutdown(); server.server_close(); thread.join()


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.client=TestClient(api.app)
    def test_health(self):
        with patch('api.db.health'):
            self.assertEqual(self.client.get('/api/health').json(),{'status':'ok'})
    def test_create(self):
        with patch('api.db.create_site',return_value={'id':1,'name':'Exemplo','url':'https://example.com/'}) as create:
            response=self.client.post('/api/sites',json={'name':' Exemplo ','url':'example.com'})
            self.assertEqual(response.status_code,201); create.assert_called_once_with('Exemplo','https://example.com/')
    def test_invalid(self):
        for data in [{'name':'x','url':'http://127.0.0.1'},{'name':' ','url':'example.com'},{'name':'x','url':''}]:
            self.assertEqual(self.client.post('/api/sites',json=data).status_code,422)
    def test_duplicate(self):
        with patch('api.db.create_site',return_value=None):
            self.assertEqual(self.client.post('/api/sites',json={'name':'x','url':'example.com'}).status_code,409)
    def test_history(self):
        with patch('api.db.history',return_value=[]):
            self.assertEqual(self.client.get('/api/sites/1/history').json(),[])
        with patch('api.db.history',return_value=None):
            self.assertEqual(self.client.get('/api/sites/1/history').status_code,404)
    def test_delete(self):
        with patch('api.db.delete_site',return_value=True):
            self.assertEqual(self.client.delete('/api/sites/1').status_code,204)
        with patch('api.db.delete_site',return_value=False):
            self.assertEqual(self.client.delete('/api/sites/1').status_code,404)
    def test_demo(self):
        with patch('api.db.create_site',return_value={'id':1}) as create:
            self.assertEqual(len(self.client.post('/api/demo').json()['created']),2)
            self.assertEqual(create.call_count,2)
    def test_worker_records_result(self):
        result=probe.Result(True,200,30)
        with patch('worker.db.targets',return_value=[{'id':1,'url':'https://example.com/'}]), patch('worker.check_url',return_value=result), patch('worker.db.save_check') as save:
            worker.run_cycle(); save.assert_called_once_with(1,result)

if __name__=='__main__': unittest.main()
