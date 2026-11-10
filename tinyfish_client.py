"""Small stdlib client for documented TinyFish public REST APIs.

No connector captures, implicit HTTP fallback, credential files, raw-header logs,
or arbitrary API hosts. Receipts describe transport observations, not mocked/live
certification. Fetch/Search are read-only; Agent is explicit and never auto-used.
References: docs.tinyfish.ai/{fetch-api,search-api}/reference and Agent API docs.
"""
from __future__ import annotations

import ipaddress
import json
import math
import os
import re
import time
import uuid
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

UNKNOWN = 'Unknown'
FETCH = 'https://api.fetch.tinyfish.ai'
SEARCH = 'https://api.search.tinyfish.ai'
AGENT = 'https://agent.tinyfish.ai'
MAX_RESPONSE_BYTES = 8_000_000
TERMINAL = frozenset(('COMPLETED', 'FAILED', 'CANCELLED'))
STATUSES = TERMINAL | {'PENDING', 'RUNNING'}


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z')


class TinyFishError(RuntimeError):
    """Safe diagnostic: no response body, request headers, or credential attached."""
    def __init__(self, code, message=None, *, http_status=None):
        self.code = code
        self.http_status = http_status
        super().__init__(message or code.replace('_', ' '))


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # urllib otherwise forwards X-API-Key on a cross-host redirect.
        raise TinyFishError('redirect_refused', 'API redirect refused; credential was not forwarded')


def public_url(url):
    """Basic public URL boundary; the caller additionally checks retailer scope."""
    if not isinstance(url, str) or len(url) > 2048 or re.search(r'[\x00-\x20\\]', url):
        raise ValueError('Invalid public HTTPS URL')
    u = urlsplit(url)
    try:
        port = u.port
        host = (u.hostname or '').encode('idna').decode('ascii').lower().rstrip('.')
    except (ValueError, UnicodeError):
        raise ValueError('Invalid public HTTPS URL') from None
    if u.scheme != 'https' or not host or u.username is not None or u.password is not None or port not in (None, 443):
        raise ValueError('Public HTTPS URL without credentials required')
    if '.' not in host or host.endswith(('.localhost', '.local', '.internal', '.test', '.invalid', '.example')):
        raise ValueError('Public hostname required')
    try:
        ipaddress.ip_address(host)
    except ValueError:
        return url
    raise ValueError('IP literal URLs are prohibited')


class TinyFishClient:
    def __init__(self, api_key=None, *, request_timeout=150, deadline=240,
                 max_requests=8, max_retries=2, opener=None,
                 clock=time.monotonic, sleep=time.sleep):
        key = os.environ.get('TINYFISH_API_KEY', '') if api_key is None else api_key
        if not isinstance(key, str) or not key.strip():
            raise TinyFishError('missing_credential', 'LIVE API TEST BLOCKED — missing credential (TINYFISH_API_KEY)')
        key = key.strip()
        if '\r' in key or '\n' in key:
            raise TinyFishError('invalid_credential', 'Credential contains invalid characters')
        if (not math.isfinite(request_timeout) or not math.isfinite(deadline)
                or request_timeout <= 0 or deadline <= 0 or max_requests < 1 or not 0 <= max_retries <= 5):
            raise ValueError('Invalid API request/deadline/retry budget')
        self._key = key
        self._clock, self._sleep = clock, sleep
        self._expires = clock() + deadline
        self.request_timeout = request_timeout
        self.max_requests, self.max_retries = int(max_requests), int(max_retries)
        self._opener = opener or build_opener(NoRedirect())
        self.receipts = []
        self.request_count = 0

    def _redact(self, value):
        if isinstance(value, str):
            return value.replace(self._key, '[REDACTED]')
        if isinstance(value, list):
            return [self._redact(v) for v in value]
        if isinstance(value, dict):
            return {self._redact(k): self._redact(v) for k, v in value.items()}
        return value

    def _id(self, value):
        if isinstance(value, str) and self._key not in value and re.fullmatch(r'[A-Za-z0-9_.:/-]{1,160}', value):
            return value
        return UNKNOWN

    @staticmethod
    def _usage(body):
        # Billing is not inferred from URL count, durations, or step count.
        usage = body.get('usage')
        allowed = ('credits', 'credits_used', 'cost', 'cost_usd', 'total_tokens',
                   'input_tokens', 'output_tokens', 'request_count', 'units', 'browser_seconds')
        result = {k: usage[k] for k in allowed if isinstance(usage, dict)
                  and isinstance(usage.get(k), (int, float)) and not isinstance(usage[k], bool)}
        return result or UNKNOWN

    @staticmethod
    def _rate_headers(headers):
        result = {}
        for name in ('X-RateLimit-Limit', 'X-RateLimit-Remaining', 'X-RateLimit-Reset'):
            value = headers.get(name)
            if isinstance(value, str) and re.fullmatch(r'[0-9]{1,16}(?:\.[0-9]{1,6})?', value):
                result[name] = float(value) if '.' in value else int(value)
        return result

    def _pause(self, seconds):
        if seconds < 0 or self._clock() + seconds >= self._expires:
            raise TinyFishError('deadline_exceeded', 'API research scheduling deadline reached')
        self._sleep(seconds)

    @staticmethod
    def _retry_after(headers, attempt):
        value = headers.get('Retry-After')
        if value:
            try:
                return max(0, float(value))
            except (ValueError, TypeError):
                try:
                    return max(0, parsedate_to_datetime(value).timestamp() - time.time())
                except (ValueError, TypeError, OverflowError):
                    pass
        return min(30, 2 ** attempt)

    def _request(self, api, method, endpoint, *, body=None, query=None, retry_safe=False):
        origin = {'fetch': FETCH, 'search': SEARCH, 'agent': AGENT}[api]
        if not endpoint.startswith(origin) or urlsplit(endpoint).netloc != urlsplit(origin).netloc:
            raise ValueError('Only fixed official TinyFish API origins are allowed')
        url = endpoint + ('?' + urlencode(query, doseq=True) if query else '')
        payload = json.dumps(body).encode('utf-8') if body is not None else None
        for attempt in range(self.max_retries + 1):
            remaining = self._expires - self._clock()
            if remaining <= 0:
                raise TinyFishError('deadline_exceeded', 'API research scheduling deadline reached')
            if self.request_count >= self.max_requests:
                raise TinyFishError('request_budget_exceeded', 'API request budget exhausted')
            local_id = str(uuid.uuid4())
            request = Request(url, data=payload, method=method,
                              headers={'X-API-Key': self._key, 'Accept': 'application/json',
                                       'Content-Type': 'application/json',
                                       'User-Agent': 'KinborResearch/3.0', 'X-Request-ID': local_id})
            receipt = {'api': api, 'method': method, 'endpoint': endpoint,
                       'client_request_id': local_id, 'provider_request_id': UNKNOWN,
                       'started_at_utc': utc_now(), 'http_status': None,
                       'authenticated_response': False, 'outcome': 'unknown',
                       'usage': UNKNOWN, 'billing_cost': UNKNOWN, 'run_id': None,
                       'attempt': attempt + 1}
            self.request_count += 1
            self.receipts.append(receipt)
            start = self._clock()
            headers = {}
            try:
                with self._opener.open(request, timeout=min(self.request_timeout, remaining)) as response:
                    status = response.status
                    headers = response.headers
                    receipt['http_status'] = status
                    receipt['provider_request_id'] = self._id(headers.get('X-Request-ID'))
                    rate = self._rate_headers(headers)
                    if rate:
                        receipt['rate_limit_headers'] = rate
                    receipt['authenticated_response'] = 200 <= status < 300
                    raw = response.read(MAX_RESPONSE_BYTES + 1)
                    if len(raw) > MAX_RESPONSE_BYTES:
                        raise TinyFishError('response_too_large', 'API response exceeded the byte budget')
                if not 200 <= status < 300:
                    raise TinyFishError('unexpected_http_status', http_status=status)
                try:
                    result = json.loads(raw.decode('utf-8'))
                except (UnicodeError, ValueError):
                    raise TinyFishError('malformed_response', 'API did not return a JSON object') from None
                if not isinstance(result, dict):
                    raise TinyFishError('malformed_response', 'API did not return a JSON object')
                result = self._redact(result)
                if receipt['provider_request_id'] == UNKNOWN:
                    receipt['provider_request_id'] = self._id(result.get('request_id'))
                receipt['usage'] = self._usage(result)
                receipt['run_id'] = result.get('run_id') if self._id(result.get('run_id')) != UNKNOWN else None
                if isinstance(result.get('num_of_steps'), int):
                    receipt['num_of_steps'] = result['num_of_steps']
                receipt['outcome'] = 'received'
                return result
            except HTTPError as exc:
                headers = exc.headers or {}
                receipt['http_status'] = exc.code
                receipt['provider_request_id'] = self._id(headers.get('X-Request-ID'))
                rate = self._rate_headers(headers)
                if rate:
                    receipt['rate_limit_headers'] = rate
                receipt['outcome'] = 'http_error'
                # An explicit 429 means rejected, so even Agent submit is safe
                # to retry. Ambiguous submit 5xx/timeouts are never retried.
                retry = exc.code == 429 or (retry_safe and exc.code in (500, 502, 503, 504))
                if retry and attempt < self.max_retries:
                    self._pause(self._retry_after(headers, attempt))
                    continue
                code = 'authentication_failed' if exc.code in (401, 403) else 'rate_limited' if exc.code == 429 else 'http_error'
                if api == 'agent' and method == 'POST' and endpoint.endswith('/run-async') and exc.code >= 500:
                    code = 'submission_outcome_unknown'
                    receipt['outcome'] = code
                raise TinyFishError(code, 'TinyFish API HTTP ' + str(exc.code), http_status=exc.code) from None
            except (TimeoutError, URLError, OSError) as exc:
                timeout = isinstance(exc, TimeoutError) or (isinstance(exc, URLError) and isinstance(exc.reason, TimeoutError))
                receipt['outcome'] = 'timeout' if timeout else 'transport_error'
                if retry_safe and method == 'GET' and attempt < self.max_retries:
                    self._pause(2 ** attempt)
                    continue
                code = 'timeout' if timeout else 'transport_error'
                if method == 'POST' and api == 'agent':
                    code = 'submission_outcome_unknown'
                raise TinyFishError(code, 'TinyFish API ' + code.replace('_', ' ')) from None
            except TinyFishError as exc:
                receipt['outcome'] = exc.code
                raise
            finally:
                receipt['finished_at_utc'] = utc_now()
                receipt['elapsed_seconds'] = round(max(0, self._clock() - start), 3)
        raise AssertionError('Unreachable retry state')

    def fetch(self, urls, *, per_url_timeout_ms=45000):
        if not isinstance(urls, (list, tuple)) or not 1 <= len(urls) <= 10:
            raise ValueError('Fetch accepts 1–10 public URLs')
        for url in urls:
            public_url(url)
        if not isinstance(per_url_timeout_ms, int) or not 1 <= per_url_timeout_ms <= 110000:
            raise ValueError('per_url_timeout_ms must be 1–110000')
        data = self._request('fetch', 'POST', FETCH, body={'urls': list(urls), 'format': 'markdown',
            'links': True, 'ttl': 0, 'per_url_timeout_ms': per_url_timeout_ms}, retry_safe=True)
        results, errors = data.get('results'), data.get('errors')
        valid = isinstance(results, list) and isinstance(errors, list)
        if valid:
            for row in results:
                if isinstance(row, dict) and row.get('title') is None:
                    row['title'] = ''
                if (not isinstance(row, dict) or not isinstance(row.get('url'), str)
                        or not isinstance(row.get('text'), str)
                        or any(k in row and not isinstance(row[k], str) for k in ('final_url', 'title'))
                        or ('links' in row and not isinstance(row['links'], list))):
                    valid = False
                    break
                if any(not isinstance(link, (str, dict)) or
                       (isinstance(link, dict) and not isinstance(link.get('url'), str))
                       for link in row.get('links', [])):
                    valid = False
                    break
            if any(not isinstance(row, dict) or not isinstance(row.get('url'), str)
                   or not isinstance(row.get('error'), str) for row in errors):
                valid = False
        if not valid:
            self.receipts[-1]['outcome'] = 'malformed_fetch_response'
            raise TinyFishError('malformed_fetch_response', 'Fetch response contains invalid results/errors rows')
        self.receipts[-1]['outcome'] = 'partial' if data['results'] and data['errors'] else 'failed' if data['errors'] else 'completed'
        self.receipts[-1]['returned_url_count'] = len(data['results'])
        self.receipts[-1]['error_url_count'] = len(data['errors'])
        return data

    def search(self, query, *, include_domains=None):
        if not isinstance(query, str) or not query.strip() or len(query) > 2000:
            raise ValueError('Nonempty bounded search query required')
        params = {'query': query}
        if include_domains:
            domains = []
            for domain in include_domains:
                public_url('https://' + domain + '/')
                if '/' in domain or '?' in domain or '#' in domain:
                    raise ValueError('Search scope must contain hostnames only')
                domains.append(domain)
            params['include_domains'] = ','.join(domains)
        data = self._request('search', 'GET', SEARCH, query=params, retry_safe=True)
        if (not isinstance(data.get('results'), list)
                or any(not isinstance(row, dict)
                       or any(not isinstance(row.get(key), str) for key in ('title', 'url', 'snippet'))
                       for row in data['results'])):
            self.receipts[-1]['outcome'] = 'malformed_search_response'
            raise TinyFishError('malformed_search_response', 'Search response contains invalid result rows')
        self.receipts[-1]['outcome'] = 'completed'
        self.receipts[-1]['returned_result_count'] = len(data['results'])
        return data

    def usage(self, service='fetch'):
        """Read one bounded usage page, retaining only this client's request IDs.

        An unreturned/unknown request ID remains unmatched; no guessed billing.
        Other simultaneous account activity is neither returned nor published.
        """
        if service not in ('fetch', 'search'):
            raise ValueError('Usage service must be fetch or search')
        relevant = [r for r in self.receipts if r['api'] == service]
        if not relevant:
            return {'items': [], 'matched_request_count': 0, 'billing_cost': UNKNOWN,
                    'coverage': 'No requests to reconcile'}
        request_ids = {r['provider_request_id'] for r in relevant if r['provider_request_id'] != UNKNOWN}
        origin = {'fetch': FETCH, 'search': SEARCH}[service]
        data = self._request(service, 'GET', origin + '/usage', query={
            'start_after': relevant[0]['started_at_utc'], 'end_before': utc_now(),
            'limit': 100, 'page': 1}, retry_safe=True)
        if not isinstance(data.get('items'), list):
            raise TinyFishError('malformed_usage_response', 'Usage response requires an items array')
        items = []
        for item in data['items']:
            if not isinstance(item, dict) or item.get('request_id') not in request_ids:
                continue
            row = {'request_id': self._id(item['request_id'])}
            for key in ('id', 'status', 'created_at'):
                if isinstance(item.get(key), str) and len(item[key]) <= 160:
                    row[key] = item[key]
            for key in ('text_length', 'links_count', 'latency_ms'):
                if isinstance(item.get(key), (int, float)) and not isinstance(item[key], bool):
                    row[key] = item[key]
            items.append(row)
        return {'items': items, 'matched_request_count': len({i['request_id'] for i in items}),
                'billing_cost': UNKNOWN, 'has_more': data.get('has_more', UNKNOWN),
                'coverage': 'Only matching provider request IDs; first 100 records; usage may lag'}

    def submit_agent(self, url, goal, *, max_duration_seconds=120):
        public_url(url)
        if not isinstance(goal, str) or not goal.strip() or len(goal) > 12000:
            raise ValueError('Bounded explicit read-only agent goal required')
        if not isinstance(max_duration_seconds, int) or not 1 <= max_duration_seconds <= 300:
            raise ValueError('Agent duration budget must be 1–300 seconds')
        data = self._request('agent', 'POST', AGENT + '/v1/automation/run-async',
            body={'url': url, 'goal': goal, 'agent_config': {'max_duration_seconds': max_duration_seconds}})
        run_id = data.get('run_id')
        if data.get('error') or not self._valid_run_id(run_id):
            self.receipts[-1]['outcome'] = 'agent_submission_failed'
            raise TinyFishError('agent_submission_failed', 'Agent submission returned no valid run ID')
        return data

    @staticmethod
    def _valid_run_id(run_id):
        return isinstance(run_id, str) and bool(re.fullmatch(r'[A-Za-z0-9_-]{1,128}', run_id))

    def _run_endpoint(self, run_id):
        if not self._valid_run_id(run_id):
            raise ValueError('Invalid run ID')
        return AGENT + '/v1/runs/' + run_id

    def get_run(self, run_id):
        data = self._request('agent', 'GET', self._run_endpoint(run_id),
                             query={'screenshots': 'none', 'html': 'none'}, retry_safe=True)
        if data.get('run_id') != run_id or data.get('status') not in STATUSES:
            self.receipts[-1]['outcome'] = 'malformed_run_response'
            raise TinyFishError('malformed_run_response', 'Agent response run ID/status mismatch')
        return data

    def cancel_run(self, run_id):
        data = self._request('agent', 'POST', self._run_endpoint(run_id) + '/cancel')
        if data.get('run_id') != run_id or data.get('status') not in TERMINAL:
            self.receipts[-1]['outcome'] = 'malformed_cancel_response'
            raise TinyFishError('malformed_cancel_response', 'Cancellation did not return a verified terminal state')
        return data

    def wait_run(self, run_id, *, poll_interval=2, timeout=120, cancel_on_timeout=True):
        if poll_interval <= 0 or timeout <= 0:
            raise ValueError('Positive polling limits required')
        expires = min(self._expires, self._clock() + timeout)
        while self._clock() < expires:
            data = self.get_run(run_id)
            if data['status'] in TERMINAL:
                return data
            remaining = expires - self._clock()
            if remaining <= 0:
                break
            self._pause(min(poll_interval, remaining))
        if cancel_on_timeout:
            # Cancellation itself is observed, never assumed successful. It can
            # fail if the overall request/deadline budget has already expired.
            data = self.cancel_run(run_id)
            data['client_wait_timed_out'] = True
            return data
        raise TinyFishError('poll_timeout', 'Agent wait timeout; run may still be active')
