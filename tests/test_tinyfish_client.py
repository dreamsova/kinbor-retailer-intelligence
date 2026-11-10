"""Mock-only public API transport tests; NEVER evidence of live execution."""
import io
import json
import os
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError

from kinbor.tinyfish_client import TinyFishClient, TinyFishError, FETCH, SEARCH, AGENT

KEY = 'OFFLINE_SYNTHETIC_TEST_SECRET_12345'
URL = 'https://retailer-fixture.org/'
RUN = '12345678-1234-1234-1234-123456789012'


class Response:
    def __init__(self, data, *, status=200, headers=None):
        self.data = json.dumps(data).encode() if not isinstance(data, bytes) else data
        self.status = status
        self.headers = headers or {'X-Request-ID': 'provider-offline-request'}
    def read(self, limit):
        return self.data[:limit]
    def __enter__(self):
        return self
    def __exit__(self, *args):
        pass


class Transport:
    """Scripted synthetic responses; no socket/network is used."""
    def __init__(self, *responses):
        self.responses = list(responses)
        self.requests = []
    def open(self, request, timeout):
        self.requests.append((request, timeout))
        result = self.responses.pop(0)
        if isinstance(result, BaseException):
            raise result
        return Response(result) if isinstance(result, dict) else result


class Clock:
    def __init__(self):
        self.time = 0
        self.sleeps = []
    def __call__(self):
        return self.time
    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.time += seconds


def http_error(code, headers=None):
    return HTTPError(FETCH, code, 'Synthetic failure ' + KEY, headers or {}, io.BytesIO(KEY.encode()))


def client(transport, **kwargs):
    return TinyFishClient(KEY, opener=transport, sleep=lambda _: None, **kwargs)


class OfflineTransportTests(unittest.TestCase):
    def test_product_image_option_is_explicit_and_default_protocol_is_unchanged(self):
        transport = Transport({'results': [], 'errors': []})
        client(transport).fetch([URL], include_images=True)
        body = json.loads(transport.requests[0][0].data)
        self.assertIs(body['image_links'], True)
        self.assertNotIn('page_metadata', body)
        with self.assertRaises(ValueError):
            client(Transport()).fetch([URL], include_images='yes')

    def test_missing_credentials_before_network(self):
        transport = Transport()
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(TinyFishError) as error:
                TinyFishClient(opener=transport)
        self.assertEqual(error.exception.code, 'missing_credential')
        self.assertFalse(transport.requests)

    def test_env_credential_and_live_fetch_options(self):
        transport = Transport({'results': [{'url': URL, 'text': 'Notebooks', 'title': None}], 'errors': []})
        with patch.dict(os.environ, {'TINYFISH_API_KEY': KEY}):
            api = TinyFishClient(opener=transport)
        data = api.fetch([URL])
        request, timeout = transport.requests[0]
        self.assertEqual(request.full_url, FETCH)
        self.assertEqual(request.get_header('X-api-key'), KEY)
        body = json.loads(request.data)
        self.assertEqual(body, {'urls': [URL], 'format': 'markdown', 'links': True,
                                'ttl': 0, 'per_url_timeout_ms': 45000})
        self.assertEqual(timeout, 150)
        self.assertEqual(data['results'][0]['text'], 'Notebooks')
        self.assertEqual(data['results'][0]['title'], '')
        receipt = api.receipts[0]
        self.assertTrue(receipt['authenticated_response'])
        self.assertEqual(receipt['provider_request_id'], 'provider-offline-request')
        self.assertEqual(receipt['usage'], 'Unknown')
        self.assertEqual(receipt['billing_cost'], 'Unknown')
        self.assertNotIn(KEY, json.dumps(receipt))
        self.assertIsNone(receipt['run_id'])

    def test_partial_and_all_failed_fetch_are_observed(self):
        for results, expected in (([{'url': URL, 'text': 'Notebooks'}], 'partial'), ([], 'failed')):
            api = client(Transport({'results': results, 'errors': [{'url': URL, 'error': 'timeout'}]}))
            api.fetch([URL])
            self.assertEqual(api.receipts[-1]['outcome'], expected)

    def test_auth_failure_never_retries_or_echoes_body(self):
        api = client(Transport(http_error(401)))
        with self.assertRaises(TinyFishError) as error:
            api.fetch([URL])
        self.assertEqual(error.exception.code, 'authentication_failed')
        self.assertEqual(api.request_count, 1)
        self.assertFalse(api.receipts[0]['authenticated_response'])
        self.assertNotIn(KEY, str(error.exception) + json.dumps(api.receipts))

    def test_429_retries_after_header(self):
        clock = Clock()
        transport = Transport(http_error(429, {'Retry-After': '3', 'X-RateLimit-Remaining': '0'}), {'results': [], 'errors': []})
        api = TinyFishClient(KEY, opener=transport, clock=clock, sleep=clock.sleep)
        api.fetch([URL])
        self.assertEqual(clock.sleeps, [3])
        self.assertEqual(api.request_count, 2)
        self.assertEqual(api.receipts[0]['rate_limit_headers'], {'X-RateLimit-Remaining': 0})
        self.assertEqual([r['http_status'] for r in api.receipts], [429, 200])

    def test_get_503_uses_backoff(self):
        clock = Clock()
        transport = Transport(http_error(503), http_error(503), {'results': []})
        api = TinyFishClient(KEY, opener=transport, clock=clock, sleep=clock.sleep)
        api.search('stationery', include_domains=['retailer-fixture.org'])
        self.assertEqual(clock.sleeps, [1, 2])
        request = transport.requests[-1][0]
        self.assertEqual(request.full_url, SEARCH + '?query=stationery&include_domains=retailer-fixture.org')

    def test_search_response_rows_are_validated(self):
        api = client(Transport({'results': [{'title': 'Stationery', 'url': URL, 'snippet': 'Notebooks'}]}))
        self.assertEqual(api.search('stationery')['results'][0]['url'], URL)
        for body in ({'results': [None]}, {'results': [{'url': URL}]}, {'results': 'bad'}):
            api = client(Transport(body))
            with self.assertRaises(TinyFishError) as error:
                api.search('stationery')
            self.assertEqual(error.exception.code, 'malformed_search_response')
            self.assertEqual(api.receipts[-1]['outcome'], 'malformed_search_response')

    def test_exhausted_429_and_request_budget(self):
        api = client(Transport(http_error(429), http_error(429)), max_retries=1)
        with self.assertRaises(TinyFishError) as error:
            api.search('stationery')
        self.assertEqual(error.exception.code, 'rate_limited')
        api = client(Transport({'results': [], 'errors': []}), max_requests=1)
        api.fetch([URL])
        with self.assertRaises(TinyFishError) as error:
            api.fetch([URL])
        self.assertEqual(error.exception.code, 'request_budget_exceeded')
        self.assertEqual(api.request_count, 1)

    def test_retry_after_cannot_exceed_deadline(self):
        clock = Clock()
        api = TinyFishClient(KEY, opener=Transport(http_error(429, {'Retry-After': '999'})),
                             clock=clock, sleep=clock.sleep, deadline=10)
        with self.assertRaises(TinyFishError) as error:
            api.fetch([URL])
        self.assertEqual(error.exception.code, 'deadline_exceeded')
        self.assertEqual(clock.sleeps, [])

    def test_timeout_preserves_unknown_and_agent_submission_not_retried(self):
        for failure in (TimeoutError(KEY), URLError(TimeoutError(KEY))):
            api = client(Transport(failure))
            with self.assertRaises(TinyFishError) as error:
                api.fetch([URL])
            self.assertEqual(error.exception.code, 'timeout')
            self.assertEqual(api.request_count, 1)
            self.assertNotIn(KEY, str(error.exception) + json.dumps(api.receipts))
        api = client(Transport(TimeoutError(KEY)))
        with self.assertRaises(TinyFishError) as error:
            api.submit_agent(URL, 'Read public pages only')
        self.assertEqual(error.exception.code, 'submission_outcome_unknown')
        self.assertEqual(api.request_count, 1)
        api = client(Transport(http_error(503)))
        with self.assertRaises(TinyFishError):
            api.submit_agent(URL, 'Read public pages only')
        self.assertEqual(api.request_count, 1)

    def test_malformed_and_oversized_responses(self):
        for response, expected in ((Response(b'not json ' + KEY.encode()), 'malformed_response'),
                                   ({'results': 'bad', 'errors': []}, 'malformed_fetch_response'),
                                   ({'results': [None], 'errors': []}, 'malformed_fetch_response'),
                                   ({'results': [], 'errors': ['bad']}, 'malformed_fetch_response'),
                                   ({'results': [{'url': URL, 'text': []}], 'errors': []}, 'malformed_fetch_response')):
            api = client(Transport(response))
            with self.assertRaises(TinyFishError) as error:
                api.fetch([URL])
            self.assertEqual(error.exception.code, expected)
        api = client(Transport(Response(b'x' * 100)))
        with patch('kinbor.tinyfish_client.MAX_RESPONSE_BYTES', 10):
            with self.assertRaises(TinyFishError) as error:
                api.fetch([URL])
        self.assertEqual(error.exception.code, 'response_too_large')

    def test_credential_echo_is_redacted_recursively(self):
        api = client(Transport({'results': [{'url': URL, 'text': 'prefix ' + KEY}], 'errors': [],
                                'usage': {'cost_usd': 0.01, 'api_key': KEY}, 'request_id': KEY}))
        data = api.fetch([URL])
        self.assertNotIn(KEY, json.dumps(data) + json.dumps(api.receipts))
        self.assertEqual(api.receipts[-1]['usage'], {'cost_usd': 0.01})

    def test_url_boundaries(self):
        api = client(Transport())
        for url in ('http://retailer-fixture.org', 'https://user:password@retailer-fixture.org',
                    'https://127.0.0.1/', 'https://localhost/', 'https://metadata.google.internal/'):
            with self.subTest(url=url), self.assertRaises(ValueError):
                api.fetch([url])
        self.assertFalse(api.receipts)
        with self.assertRaises(ValueError):
            api.fetch([URL] * 11)
        with self.assertRaises(ValueError):
            api.search('test', include_domains=['retailer-fixture.org/path'])

    def test_redirect_does_not_forward_credentials(self):
        from kinbor.tinyfish_client import NoRedirect
        from urllib.request import Request
        with self.assertRaises(TinyFishError) as error:
            NoRedirect().redirect_request(Request(FETCH), None, 302, 'redirect', {}, 'https://untrusted.org')
        self.assertEqual(error.exception.code, 'redirect_refused')

    def test_usage_filters_unrelated_account_activity(self):
        api = client(Transport({'results': [], 'errors': []}, {'items': [
            {'request_id': 'provider-offline-request', 'id': 'u1', 'status': 'ok', 'latency_ms': 20, 'text_length': 4},
            {'request_id': 'unrelated-id', 'url': 'https://private-other-client.org/', 'error': KEY}], 'has_more': False}))
        api.fetch([URL])
        usage = api.usage()
        self.assertEqual(usage['matched_request_count'], 1)
        self.assertEqual(usage['billing_cost'], 'Unknown')
        self.assertNotIn('private-other-client', json.dumps(usage))
        self.assertIn(FETCH + '/usage?', api._opener.requests[-1][0].full_url)


class OfflineAsyncTests(unittest.TestCase):
    def test_submit_pending_running_completed(self):
        transport = Transport({'run_id': RUN, 'error': None},
                              {'run_id': RUN, 'status': 'PENDING'},
                              {'run_id': RUN, 'status': 'RUNNING'},
                              {'run_id': RUN, 'status': 'COMPLETED', 'result': {'text': 'notebooks'}, 'num_of_steps': 3})
        clock = Clock()
        api = TinyFishClient(KEY, opener=transport, clock=clock, sleep=clock.sleep)
        self.assertEqual(api.submit_agent(URL, 'Read public information')['run_id'], RUN)
        result = api.wait_run(RUN)
        self.assertEqual(result['status'], 'COMPLETED')
        self.assertEqual(transport.requests[0][0].full_url, AGENT + '/v1/automation/run-async')
        self.assertEqual(json.loads(transport.requests[0][0].data)['agent_config'], {'max_duration_seconds': 120})
        self.assertIn('?screenshots=none&html=none', transport.requests[-1][0].full_url)
        self.assertEqual(api.receipts[-1]['num_of_steps'], 3)

    def test_failed_and_cancelled_are_terminal(self):
        for state in ('FAILED', 'CANCELLED'):
            api = client(Transport({'run_id': RUN, 'status': state, 'error': 'Synthetic error'}))
            self.assertEqual(api.wait_run(RUN)['status'], state)
            self.assertEqual(api.request_count, 1)

    def test_wait_timeout_cancel_reports_actual_terminal_state(self):
        clock = Clock()
        transport = Transport({'run_id': RUN, 'status': 'RUNNING'},
                              {'run_id': RUN, 'status': 'CANCELLED'})
        api = TinyFishClient(KEY, opener=transport, clock=clock, sleep=clock.sleep)
        result = api.wait_run(RUN, timeout=1)
        self.assertTrue(result['client_wait_timed_out'])
        self.assertEqual(result['status'], 'CANCELLED')
        self.assertEqual(transport.requests[-1][0].get_method(), 'POST')
        self.assertTrue(transport.requests[-1][0].full_url.endswith('/cancel'))
        # Run can complete before cancellation arrives; do not claim cancelled.
        api = client(Transport({'run_id': RUN, 'status': 'COMPLETED'}))
        self.assertEqual(api.cancel_run(RUN)['status'], 'COMPLETED')

    def test_malformed_async_states_and_path_injection_rejected(self):
        for response, action in (({'run_id': None, 'error': 'fail'}, lambda c: c.submit_agent(URL, 'Read')),
                                  ({'run_id': RUN, 'status': 'INVENTED'}, lambda c: c.get_run(RUN)),
                                  ({'run_id': RUN, 'status': 'RUNNING'}, lambda c: c.cancel_run(RUN))):
            with self.assertRaises(TinyFishError):
                action(client(Transport(response)))
        api = client(Transport())
        with self.assertRaises(ValueError):
            api.get_run('../../secrets')


if __name__ == '__main__':
    unittest.main(verbosity=2)
