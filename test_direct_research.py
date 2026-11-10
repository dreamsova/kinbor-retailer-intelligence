"""Mock-only CLI integration: no network, live API receipt, or buyer validation.

The real catalog and pipeline are exercised against a scripted synthetic transport.
Every result remains an offline test fixture, never evidence of real API execution.
"""
from contextlib import ExitStack, redirect_stdout, redirect_stderr
import csv
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

import research
import tinyfish_client


URL = 'https://retailer-fixture.org/'
KEY = 'OFFLINE_SYNTHETIC_CLI_SECRET_12345'


class SyntheticResponse:
    def __init__(self, body):
        self.status = 200
        self.headers = {'X-Request-ID': 'offline-synthetic-request'}
        self.body = json.dumps(body).encode('utf-8')

    def read(self, limit):
        return self.body[:limit]

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


class SyntheticTransport:
    """Scripted HTTP substitute; using a real socket is a test failure."""
    def __init__(self, *responses):
        self.responses = list(responses)
        self.requests = []

    def open(self, request, timeout):
        self.requests.append(request)
        if not self.responses:
            raise AssertionError('Unexpected extra API request')
        response = self.responses.pop(0)
        if isinstance(response, BaseException):
            raise response
        return SyntheticResponse(response)


def page(path='/', *, text='Independent stationery store', links=(), title='Fixture store', final=None):
    url = URL.rstrip('/') + path
    return {'url': url, 'final_url': final or url, 'title': title,
            'text': text, 'links': list(links), 'format': 'markdown', 'latency_ms': 1}


def home():
    return page(links=[{'url': URL + 'contact', 'text': 'Contact'},
                       {'url': URL + 'collections/notebooks', 'text': 'Notebooks'}])


def fetch_result(*pages, errors=()):
    return {'results': list(pages), 'errors': list(errors)}


def rows(folder, name):
    with (Path(folder) / name).open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def json_file(folder, name):
    return json.loads((Path(folder) / name).read_text(encoding='utf-8'))


class DirectResearchOfflineIntegration(unittest.TestCase):
    def run_cli(self, folder, transport, *extra, credential=KEY):
        # Patch both the API transport and unrelated fallback/DNS entry points.
        # An implicit public HTTP request must fail this offline integration test.
        with ExitStack() as stack:
            stack.enter_context(patch.dict(os.environ, {'TINYFISH_API_KEY': credential}, clear=True))
            opener = stack.enter_context(patch.object(tinyfish_client, 'build_opener', return_value=transport))
            stack.enter_context(patch.object(research, 'public_capture', side_effect=AssertionError('Implicit HTTP fallback')))
            stack.enter_context(patch.object(research, 'fetch_page', side_effect=AssertionError('Unexpected public HTTP')))
            stack.enter_context(patch.object(research.socket, 'getaddrinfo', side_effect=AssertionError('Unexpected DNS')))
            output, error = io.StringIO(), io.StringIO()
            stack.enter_context(redirect_stdout(output))
            stack.enter_context(redirect_stderr(error))
            code = research.main(['--mode', 'tinyfish', '--url', URL,
                                  '--output-dir', str(folder), *extra])
        return code, output.getvalue(), error.getvalue(), opener.call_count

    def test_mocked_cli_to_api_to_catalog_outputs_is_auditable(self):
        transport = SyntheticTransport(fetch_result(home()), fetch_result(
            page('/contact', text='Contact our store', title='Contact'),
            page('/collections/notebooks', text='A5 notebooks\nMidori notebooks', title='Notebooks')))
        with tempfile.TemporaryDirectory() as folder:
            code, stdout, stderr, _ = self.run_cli(folder, transport)
            self.assertEqual(code, 0, stderr)
            result = json_file(folder, 'research.json')
            receipt = json_file(folder, 'api_receipt.json')
            self.assertEqual(result['acquisition'], 'tinyfish_api_fetch')
            self.assertEqual(result['mode'], 'tinyfish')
            self.assertEqual(result['status'], 'completed')
            self.assertEqual(result['summary']['catalog_count'], 210)
            self.assertEqual(len(rows(folder, 'candidate_audit.csv')), 210)
            evidence = rows(folder, 'evidence.csv')
            self.assertTrue(evidence)
            self.assertTrue(all(e['epistemic_status'] == 'fact_observation' for e in evidence))
            self.assertTrue(all(e['acquisition'] == 'tinyfish_api_fetch' for e in evidence))
            self.assertTrue(all(e['source_url'].startswith(URL) and e['retrieved_at_utc'] for e in evidence))
            self.assertEqual(receipt['execution'], 'local_python_direct_api')
            self.assertTrue(receipt['authenticated_response_received'])
            self.assertIsNone(receipt['run_id'])
            self.assertEqual(receipt['fallback'], 'none')
            self.assertEqual(receipt['usage'], 'Unknown')
            self.assertEqual(len(receipt['requests']), 2)
            self.assertEqual([r['http_status'] for r in receipt['requests']], [200, 200])
            brief = (Path(folder) / 'buyer_brief.md').read_text(encoding='utf-8')
            self.assertIn('api_receipt.json', brief)
            self.assertIn('human image review', brief)
            self.assertIn('Unknown', brief)
            public = '\n'.join(p.read_text(encoding='utf-8') for p in Path(folder).iterdir())
            self.assertNotIn(KEY, public + stdout + stderr)
            with patch.object(tinyfish_client, 'build_opener', side_effect=AssertionError('Offline validation network')):
                self.assertEqual(research.validate_output(folder)['status'], 'passed')
            for request in transport.requests:
                self.assertEqual(request.full_url, tinyfish_client.FETCH)
                payload = json.loads(request.data)
                self.assertEqual(set(payload), {'urls', 'format', 'links', 'ttl', 'per_url_timeout_ms'})
                self.assertEqual(payload['ttl'], 0)

    def test_partial_fetch_keeps_supported_evidence_and_nonzero_exit(self):
        transport = SyntheticTransport(fetch_result(home()), fetch_result(
            page('/collections/notebooks', text='Notebooks', title='Notebooks'),
            errors=[{'url': URL + 'contact', 'error': 'Synthetic access denied', 'status': 403}]))
        with tempfile.TemporaryDirectory() as folder:
            code, _, stderr, _ = self.run_cli(folder, transport)
            self.assertEqual(code, 2, stderr)
            result = json_file(folder, 'research.json')
            self.assertEqual(result['status'], 'partial')
            self.assertTrue(result['errors'])
            self.assertTrue(rows(folder, 'evidence.csv'))
            self.assertEqual(len(rows(folder, 'candidate_audit.csv')), 210)
            self.assertEqual(research.validate_output(folder)['status'], 'passed')

    def test_missing_key_blocks_before_transport_and_never_falls_back(self):
        transport = SyntheticTransport()
        with tempfile.TemporaryDirectory() as folder:
            code, _, stderr, opener_calls = self.run_cli(folder, transport, credential='')
            self.assertEqual(code, 2, stderr)
            self.assertEqual(opener_calls, 0)
            self.assertEqual(transport.requests, [])
            result = json_file(folder, 'research.json')
            receipt = json_file(folder, 'api_receipt.json')
            self.assertEqual(result['status'], 'failed')
            self.assertEqual(receipt['status'], 'blocked')
            self.assertEqual(receipt['live_validation'], 'LIVE API TEST BLOCKED — missing credential')
            self.assertFalse(receipt['authenticated_response_received'])
            self.assertEqual(receipt['requests'], [])
            self.assertEqual(receipt['fallback'], 'none')
            self.assertEqual(len(rows(folder, 'candidate_audit.csv')), 210)
            self.assertEqual(rows(folder, 'evidence.csv'), [])
            self.assertEqual(rows(folder, 'recommendations.csv'), [])
            self.assertEqual(research.validate_output(folder)['status'], 'passed')

    def test_api_authentication_failure_is_not_public_http_success(self):
        failure = HTTPError(tinyfish_client.FETCH, 401, 'Synthetic auth failure', {}, io.BytesIO(b'private'))
        transport = SyntheticTransport(failure)
        with tempfile.TemporaryDirectory() as folder:
            code, _, stderr, _ = self.run_cli(folder, transport)
            self.assertEqual(code, 2, stderr)
            result = json_file(folder, 'research.json')
            receipt = json_file(folder, 'api_receipt.json')
            self.assertEqual(result['status'], 'failed')
            self.assertEqual(result['acquisition'], 'tinyfish_api_fetch')
            self.assertFalse(receipt['authenticated_response_received'])
            self.assertEqual(receipt['requests'][0]['http_status'], 401)
            self.assertEqual(receipt['error_code'], 'authentication_failed')
            self.assertEqual(receipt['fallback'], 'none')
            self.assertEqual(len(transport.requests), 1)
            self.assertEqual(rows(folder, 'evidence.csv'), [])

    def test_search_snippets_discover_urls_but_do_not_become_facts(self):
        transport = SyntheticTransport(fetch_result(page()),
            {'results': [{'url': URL + 'contact', 'title': 'Notebooks Midori',
                          'snippet': 'Notebooks, planners, Midori; synthetic untrusted snippet'}]},
            fetch_result(page('/contact', text='Contact our shop', title='Contact')))
        with tempfile.TemporaryDirectory() as folder:
            code, _, stderr, _ = self.run_cli(folder, transport, '--tinyfish-search')
            self.assertEqual(code, 0, stderr)
            evidence = rows(folder, 'evidence.csv')
            self.assertFalse(any(e['field'] in ('category', 'brand') for e in evidence))
            self.assertEqual(rows(folder, 'recommendations.csv'), [])
            self.assertTrue(transport.requests[1].full_url.startswith(tinyfish_client.SEARCH + '?'))
            self.assertEqual(len(transport.requests), 3)
            self.assertEqual(research.validate_output(folder)['status'], 'passed')

    def test_unlinked_external_fetch_result_is_rejected(self):
        transport = SyntheticTransport(fetch_result(page(text='Notebooks', final='https://unlinked-fixture.org/')))
        with tempfile.TemporaryDirectory() as folder:
            code, _, stderr, _ = self.run_cli(folder, transport)
            self.assertEqual(code, 2, stderr)
            result = json_file(folder, 'research.json')
            self.assertEqual(result['pages'], [])
            self.assertIn('Rejected unexpected or unlinked API result URL', result['errors'])
            self.assertEqual(rows(folder, 'evidence.csv'), [])
            self.assertEqual(rows(folder, 'recommendations.csv'), [])

    def test_changed_receipt_is_rejected_by_offline_validation(self):
        transport = SyntheticTransport(fetch_result(page(text='Notebooks', title='Notebooks')))
        with tempfile.TemporaryDirectory() as folder:
            code, _, stderr, _ = self.run_cli(folder, transport)
            self.assertEqual(code, 0, stderr)
            receipt_path = Path(folder) / 'api_receipt.json'
            receipt = json_file(folder, 'api_receipt.json')
            receipt['fallback'] = 'public_http'
            receipt_path.write_text(json.dumps(receipt), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'receipt drift'):
                research.validate_output(folder)

    def test_schema2_submission_exclusions_and_long_constraints_are_preserved(self):
        restriction = 'Please refrain from contacting the shop with follow up inquiries.'
        long_paragraph = ('Product submissions: ' + 'Review our complete submission requirements. ' * 20
                          + restriction)
        self.assertGreater(long_paragraph.index(restriction), 500)
        submission = page('/submit', title='Product submissions', text=(
            'We are interested in stocking:\nNotebooks and journals.\n'
            'We are NOT currently considering:\n'
            'Planners, pencil cases, mugs, stickers, sticky notes and pens.\n'
            'Please attach your product submission materials with staplers.\n'
            + long_paragraph))
        submission.update(retrieved_at_utc='2026-11-10T02:00:00Z', status='ok', error='')
        evidence = research.extract_evidence([submission], 'tinyfish_api_fetch', typed=True)
        # A submission exclusion list and packaging directions must never become
        # observed retail assortment. Schema 1 history is intentionally separate.
        categories = {e['value'] for e in evidence if e['field'] == 'category'}
        self.assertEqual(categories, {'Notebooks & Journals'})
        constraints = [e for e in evidence if e['verification_status'] == 'policy_constraint']
        self.assertTrue(constraints)
        self.assertTrue(any('follow up' in e['quote'] for e in constraints))
        self.assertTrue(all(e['field'] == 'vendor_policy' for e in constraints))
        self.assertTrue(all(e['quote'] in submission['text'] for e in constraints))
        self.assertTrue(all(e['epistemic_status'] == 'fact_observation' for e in evidence))

    def test_partial_or_failed_receipt_cannot_be_promoted_to_completed(self):
        cases = (
            ('partial', SyntheticTransport(fetch_result(home()), fetch_result(
                page('/collections/notebooks', text='Notebooks', title='Notebooks'),
                errors=[{'url': URL + 'contact', 'error': 'Synthetic denied', 'status': 403}]))),
            ('failed', SyntheticTransport(HTTPError(tinyfish_client.FETCH, 401,
                'Synthetic authentication failure', {}, io.BytesIO(b'')))),
        )
        for status, transport in cases:
            with self.subTest(status=status), tempfile.TemporaryDirectory() as folder:
                code, _, stderr, _ = self.run_cli(folder, transport)
                self.assertEqual(code, 2, stderr)
                result = json_file(folder, 'research.json')
                self.assertEqual(result['status'], status)
                self.assertEqual(json_file(folder, 'api_receipt.json')['status'], status)
                self.assertEqual(research.validate_output(folder)['status'], 'passed')
                result['status'] = 'completed'
                (Path(folder) / 'research.json').write_text(json.dumps(result), encoding='utf-8')
                with self.assertRaises(ValueError):
                    research.validate_output(folder)

    def test_explicit_public_mode_keeps_http_provenance(self):
        captured_page = page(text='Notebooks', title='Notebooks')
        captured_page.update(retrieved_at_utc='2026-11-10T02:00:00Z', status='ok', error='')
        capture = {'provider': 'public_http', 'website': URL, 'status': 'completed',
                   'acquisition': 'public_http', 'run_id': None, 'pages': [captured_page], 'errors': []}
        with tempfile.TemporaryDirectory() as folder, \
                patch.object(research, 'public_capture', return_value=capture) as public, \
                patch.object(research, 'tinyfish_capture', side_effect=AssertionError('Unexpected API')):
            with redirect_stdout(io.StringIO()):
                code = research.main(['--mode', 'public_http', '--url', URL, '--output-dir', folder])
            self.assertEqual(code, 0)
            public.assert_called_once()
            result = json_file(folder, 'research.json')
            self.assertEqual(result['mode'], 'public_http')
            self.assertEqual(result['acquisition'], 'public_http')
            self.assertIsNone(result['run_id'])
            self.assertNotIn('api_receipt', result)
            self.assertFalse((Path(folder) / 'api_receipt.json').exists())
            self.assertTrue(all(e['acquisition'] == 'public_http' for e in rows(folder, 'evidence.csv')))
            self.assertEqual(research.validate_output(folder)['status'], 'passed')


if __name__ == '__main__':
    unittest.main(verbosity=2)
