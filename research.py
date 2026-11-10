#!/usr/bin/env python3
"""Bounded, read-only retailer research. No contact, checkout or retailer writes.

Public mode is an ordinary HTTP fallback, not a TinyFish run. Import mode consumes
an actual saved TinyFish connector capture; validate mode is offline, not research.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import ipaddress
import json
import os
import re
import socket
import sys
import time
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import unquote, urljoin, urlsplit, urlunsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
from urllib.robotparser import RobotFileParser

ROOT = Path(__file__).resolve().parent
UNKNOWN = 'Unknown'
AGENT = 'KinborResearch/2.0'
MAX_BYTES = 1_500_000
CATEGORIES = {
    'Notebooks & Journals': r'\b(?:notebooks?|journals?)\b',
    'Planners & Calendars': r'\b(?:planners?|calendars?)\b',
    'Pouches & Cases': r'\b(?:pencil cases?|pen cases?|pen storage|pouches?|bags.cases.pouches)\b',
    'Refills & Inserts': r'\b(?:notebook refills?|planner inserts?|refills?.inserts?)\b',
    'Stickers & Decorative Tape': r'\b(?:stickers?|washi(?: tape)?)\b',
    'Sticky Notes & Page Flags': r'\b(?:sticky notes?|page flags?|memo pads?)\b',
    'Desk & Office Tools': r'\b(?:rulers?|scissors|staplers?|desk organizers?)\b',
    'Mugs & Drinkware': r'\b(?:mugs?|drinkware)\b',
    'Pens & Writing': r'\b(?:pens?|pencils?)\b',
}
BRANDS = ('Midori', 'Hobonichi', 'Rhodia', 'Leuchtturm1917', 'Kaweco',
          'Kokuyo', 'Blackwing', 'Delfonics', 'Penco', 'Hightide', 'Field Notes',
          'Lamy', 'Pilot', 'TWSBI', 'Traveler\'s Company', 'Shorthand Press')
EVIDENCE_COLUMNS = ('evidence_id', 'field', 'value', 'source_url', 'retrieved_at_utc',
                    'confidence', 'verification_status', 'quote', 'acquisition', 'run_id')
EVIDENCE_V2_COLUMNS = EVIDENCE_COLUMNS + ('epistemic_status',)
RECOMMENDATION_COLUMNS = ('sku', 'name_zh', 'collection', 'product_category_inferred',
    'image_path', 'product_source_sheet', 'product_source_row', 'units_per_carton',
    'moq_cartons', 'moq_units', 'carton_qty_basis', 'retailer_evidence_ids',
    'retailer_evidence_url', 'retailer_fact', 'match_basis', 'match_reason',
    'aesthetic_fit', 'order_feasibility', 'commercial_status', 'display_order', 'tie_group')


def now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z')


def check_timestamp(value):
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise ValueError
    except (ValueError, AttributeError):
        raise ValueError('A timezone-aware retrieval timestamp is required') from None
    return value


def normalize_url(url, *, resolve=False):
    """Only public HTTPS hostnames, no credentials, unusual ports or active URLs.

    DNS is checked before each actual fetch, including each redirect. Offline
    validation intentionally does not resolve DNS. Query/fragment are discarded
    to avoid publishing tracking/session tokens or executing query-based actions.
    """
    if not isinstance(url, str) or len(url) > 2048 or re.search(r'[\x00-\x20\\]', url):
        raise ValueError('Invalid URL')
    u = urlsplit(url)
    try:
        port = u.port
    except ValueError:
        raise ValueError('Invalid URL port') from None
    if u.scheme.lower() != 'https' or not u.hostname or u.username is not None or u.password is not None:
        raise ValueError('Use an HTTPS retailer URL without credentials')
    host = u.hostname.lower().encode('idna').decode('ascii').rstrip('.')
    if port not in (None, 443) or '.' not in host or host.endswith(('.local', '.localhost', '.internal', '.test', '.invalid', '.example')):
        raise ValueError('Public HTTPS hostname and standard port required')
    try:
        ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        raise ValueError('IP literal URLs are not retailer websites')
    if host in ('localhost', 'metadata.google.internal'):
        raise ValueError('Local/metadata URL is prohibited')
    if any(c in unquote(u.path) for c in ('\r', '\n', '\x00', '\\')):
        raise ValueError('Invalid URL path')
    if resolve:
        try:
            addresses = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
        except OSError as exc:
            raise ValueError('DNS unavailable') from exc
        if not addresses or any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses):
            raise ValueError('Non-public DNS address is prohibited')
    return urlunsplit(('https', host, u.path or '/', '', ''))


def same_site(a, b):
    return urlsplit(a).hostname.removeprefix('www.') == urlsplit(b).hostname.removeprefix('www.')


def safe_text(value):
    """Remove control characters and credentials; raw pages are not public output."""
    value = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', str(value))
    value = re.sub(r'(?i)\b(?:authorization\s*[:=]\s*(?:bearer\s+)?\S+|bearer\s+\S+|sk-[a-z0-9_-]{12,}|(?:api[_ -]?key|password)\s*[:=]\s*\S+)', '[REDACTED]', value)
    value = re.sub(r'https?://[^\s/]+:[^\s/@]+@\S+', '[REDACTED URL]', value)
    return value


def plain(value):
    return re.sub(r'\s+', ' ', safe_text(value)).strip()


def short_quote(text, match, words=12):
    # Exact substring; enough nearby context for an operator, never a rewritten fact.
    lo = max(text.rfind('\n', 0, match.start()) + 1, match.start() - 50)
    hi = text.find('\n', match.end())
    if hi < 0:
        hi = len(text)
    snippet = text[lo:hi].strip()
    tokens = list(re.finditer(r'\S+', snippet))
    if len(tokens) > words:
        # Window around the matched token, maintaining literal source substring.
        relative = match.start() - lo
        at = next((i for i, t in enumerate(tokens) if t.end() > relative), 0)
        start = max(0, at - 3)
        end = min(len(tokens), start + words)
        snippet = snippet[tokens[start].start():tokens[end - 1].end()]
    return snippet


class PageParser(HTMLParser):
    """Visible-text extraction; scripts/styles/forms are never executed or submitted."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts, self.links, self.title_parts = [], [], []
        self.ignore = 0
        self.in_title = False
        self.anchor = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in ('script', 'style', 'noscript', 'svg', 'template'):
            self.ignore += 1
        if tag == 'title':
            self.in_title = True
        if tag in ('p', 'div', 'li', 'h1', 'h2', 'h3', 'br'):
            self.parts.append('\n')
        if tag == 'a' and not self.ignore:
            self.anchor = [attrs.get('href', ''), []]

    def handle_endtag(self, tag):
        if tag in ('script', 'style', 'noscript', 'svg', 'template') and self.ignore:
            self.ignore -= 1
        if tag == 'title':
            self.in_title = False
        if tag == 'a' and self.anchor:
            self.links.append({'url': self.anchor[0], 'text': ''.join(self.anchor[1]).strip()})
            self.anchor = None
        if tag in ('p', 'div', 'li', 'h1', 'h2', 'h3'):
            self.parts.append('\n')

    def handle_data(self, data):
        if self.ignore:
            return
        if self.in_title:
            self.title_parts.append(data)
        else:
            self.parts.append(data)
        if self.anchor:
            self.anchor[1].append(data)


def normalize_page(page):
    url = normalize_url(page['url'])
    final = normalize_url(page.get('final_url') or url)
    links = []
    for raw in page.get('links', []):
        link = {'url': raw, 'text': ''} if isinstance(raw, str) else raw
        target = link.get('url', '')
        if target.startswith('mailto:'):
            # Business public emails only; no query subjects/body content.
            address = target[7:].split('?')[0]
            if re.fullmatch(r'[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}', address):
                links.append({'url': 'mailto:' + address, 'text': plain(link.get('text', ''))})
            continue
        try:
            target = normalize_url(urljoin(final, target))
        except ValueError:
            continue
        if target not in {x['url'] for x in links}:
            links.append({'url': target, 'text': plain(link.get('text', ''))[:200]})
    return {'url': url, 'final_url': final, 'title': plain(page.get('title', ''))[:300],
            'text': safe_text(page.get('text', ''))[:MAX_BYTES], 'links': links,
            'retrieved_at_utc': check_timestamp(page['retrieved_at_utc']),
            'status': page.get('status', 'ok'), 'error': plain(page.get('error', ''))[:200]}


def validate_capture(bundle, website):
    """Validate a saved real capture without claiming fresh or independently verified data."""
    website = normalize_url(website)
    if bundle.get('schema_version') != 1 or bundle.get('provider') != 'tinyfish_connector':
        raise ValueError('Expected a version 1 tinyfish_connector capture, not mock/API output')
    if normalize_url(bundle.get('website', '')) != website:
        raise ValueError('Capture retailer URL mismatch')
    if bundle.get('acquisition') not in ('fetch_content', 'run_web_automation'):
        raise ValueError('Unsupported connector acquisition')
    if bundle.get('status') not in ('completed', 'partial', 'failed'):
        raise ValueError('Invalid capture status')
    check_timestamp(bundle.get('captured_at_utc'))
    related = bundle.get('related_browser_run_id')
    if related is not None and not re.fullmatch(r'[a-fA-F0-9-]{36}', related):
        raise ValueError('Invalid related browser run ID')
    run_id = bundle.get('run_id')
    if run_id is not None and not re.fullmatch(r'[a-fA-F0-9-]{36}', run_id):
        raise ValueError('Invalid actual run ID')
    if bundle['acquisition'] == 'run_web_automation' and not run_id:
        raise ValueError('Browser automation capture requires its actual run ID')
    if not isinstance(bundle.get('pages'), list) or len(bundle['pages']) > 20:
        raise ValueError('Capture must contain at most 20 pages')
    pages = [normalize_page(p) for p in bundle['pages']]
    # A second shop domain is accepted only when the supplied official homepage
    # actually links to it. This is evidence of linkage, not an ownership audit.
    linked_hosts = {urlsplit(website).hostname.removeprefix('www.')}
    for p in pages:
        if same_site(p['url'], website):
            linked_hosts.update(urlsplit(x['url']).hostname.removeprefix('www.')
                for x in p['links'] if x['url'].startswith('https://'))
    for p in pages:
        if any(urlsplit(u).hostname.removeprefix('www.') not in linked_hosts for u in (p['url'], p['final_url'])):
            raise ValueError('Capture includes an unlinked external domain')
    unique = {}
    for p in pages:
        unique.setdefault(p['final_url'], p)
    result = dict(bundle)
    result['pages'] = list(unique.values())
    result['website'] = website
    result['run_id'] = run_id
    return result


class SafeRedirect(HTTPRedirectHandler):
    def __init__(self, website):
        self.website = website
        super().__init__()

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        target = normalize_url(newurl, resolve=True)
        if not same_site(target, self.website):
            raise ValueError('Cross-site redirect not followed')
        return super().redirect_request(req, fp, code, msg, headers, target)


def fetch_page(url, *, timeout=15, website=None):
    url = normalize_url(url)
    website = website or url
    page = {'url': url, 'final_url': url, 'retrieved_at_utc': now(), 'status': 'failed',
            'title': '', 'text': '', 'links': [], 'error': ''}
    try:
        normalize_url(url, resolve=True)
        opener = build_opener(SafeRedirect(website))
        request = Request(url, headers={'User-Agent': AGENT, 'Accept': 'text/html,text/plain'})
        with opener.open(request, timeout=timeout) as response:
            page['final_url'] = normalize_url(response.url)
            content_type = response.headers.get('Content-Type', '').lower()
            if not any(kind in content_type for kind in ('text/html', 'text/plain', 'application/xhtml')):
                raise ValueError('Non-text response ignored')
            raw = response.read(MAX_BYTES + 1)
            if len(raw) > MAX_BYTES:
                raise ValueError('Response exceeds byte limit')
            body = raw.decode('utf-8', 'replace')
            if 'html' in content_type:
                parser = PageParser()
                parser.feed(body)
                page.update(text=''.join(parser.parts), title=''.join(parser.title_parts), links=parser.links)
            else:
                page['text'] = body
            if re.search(r'access denied|just a moment|verify (?:that )?you are human|captcha', page['title'], re.I):
                raise ValueError('Challenge page; no bypass attempted')
            page['status'] = 'ok'
    except HTTPError as exc:
        page['error'] = 'HTTP ' + str(exc.code) + '; no bypass attempted'
    except (URLError, TimeoutError, OSError, ValueError) as exc:
        page['error'] = type(exc).__name__ + ': ' + str(exc)
    return normalize_page(page)


def public_capture(website, *, max_pages=8, timeout=15, deadline=120):
    website = normalize_url(website, resolve=True)
    started = time.monotonic()
    robots_url = urljoin(website, '/robots.txt')
    rp = RobotFileParser()
    try:
        robot_page = fetch_page(robots_url, timeout=timeout, website=website)
        if robot_page['status'] != 'ok':
            # A 404 means no published rules. All other failure is fail-closed.
            if not robot_page['error'].startswith('HTTP 404'):
                raise ValueError('robots.txt unavailable; public mode stopped')
            rp.parse([])
        else:
            rp.parse(robot_page['text'].splitlines())
    except (ValueError, OSError) as exc:
        return {'provider': 'public_http', 'website': website, 'status': 'failed',
                'acquisition': 'public_http', 'run_id': None, 'pages': [], 'errors': [str(exc)]}
    queue, pages, seen, errors = [website], [], set(), []
    relevant = re.compile(r'contact|about|faq|submit|vendor|supplier|notebook|journal|planner|case|pouch|brand|stationery', re.I)
    # Prefer contact/policy discovery before product pages. No external search,
    # login, form, cart, checkout or arbitrary user-provided instructions.
    forbidden = re.compile(r'/account|/login|/cart|/checkout|/search|/customer_|/orders|/products/', re.I)
    while queue and len(pages) < max_pages:
        if time.monotonic() - started >= deadline:
            errors.append('Total research deadline reached')
            break
        url = queue.pop(0)
        if url in seen:
            continue
        seen.add(url)
        if not rp.can_fetch(AGENT, url):
            errors.append('robots_disallowed: ' + url)
            continue
        page = fetch_page(url, timeout=min(timeout, max(1, deadline - (time.monotonic() - started))), website=website)
        pages.append(page)
        if page['status'] != 'ok':
            errors.append(page['error'] + ': ' + url)
            continue
        links = [x['url'] for x in page['links'] if x['url'].startswith('https://')
                 and same_site(x['url'], website) and relevant.search(x['url']) and not forbidden.search(x['url'])]
        links.sort(key=lambda u: (0 if re.search(r'contact|submit|vendor|supplier|faq', u, re.I) else 1, u))
        queue.extend(x for x in links if x not in seen and x not in queue)
    good = sum(p['status'] == 'ok' for p in pages)
    return {'provider': 'public_http', 'website': website, 'status': 'completed' if good and not errors else 'partial' if good else 'failed',
            'acquisition': 'public_http', 'run_id': None, 'pages': pages, 'errors': errors,
            'elapsed_seconds': round(time.monotonic() - started, 3)}


def tinyfish_capture(website, *, max_pages=6, deadline=240, max_requests=4,
                     search=False, collect_usage=False):
    """Local Python -> official REST API. Never imports a connector capture.

    Fetch homepage, then one bounded batch of relevant official links. Search
    is optional discovery only: snippets are never assortment evidence. No
    catalog, images, supplier details or website text is sent as an agent goal.
    """
    from tinyfish_client import TinyFishClient, TinyFishError
    website = normalize_url(website)
    started = time.monotonic()
    pages, errors, client = [], [], None
    receipt = {'schema_version': 1, 'execution': 'local_python_direct_api',
               'started_at_utc': now(), 'website': website, 'transport': 'official_rest',
               'authenticated_response_received': False, 'requests': [], 'usage': UNKNOWN,
               'billed_cost': UNKNOWN, 'run_id': None,
               'limits': {'max_pages': max_pages, 'max_requests': max_requests,
                          'deadline_seconds': deadline}, 'fallback': 'none'}
    allowed_hosts = {urlsplit(website).hostname.removeprefix('www.')}
    seen = set()
    forbidden = re.compile(r'/account|/login|/cart|/checkout|/search|/customer_|/orders|/logout|/add(?:/|$)|/blogs/|/events(?:/|$)', re.I)
    relevant = re.compile(r'contact|about|faq|submit|vendor|supplier|notebook|journal|planner|case|pouch|brand|stationery|shop', re.I)

    def acceptable(url):
        try:
            url = normalize_url(url)
        except (ValueError, TypeError):
            return None
        if urlsplit(url).hostname.removeprefix('www.') not in allowed_hosts or forbidden.search(urlsplit(url).path):
            return None
        return url

    def acquire(urls):
        response = client.fetch(urls, per_url_timeout_ms=45000)
        stamp = now()  # response observation, not a claimed origin publication time
        for row in response.get('results', []):
            original = acceptable(row.get('url', ''))
            final = acceptable(row.get('final_url') or row.get('url', ''))
            if not original or not final or original not in urls:
                errors.append('Rejected unexpected or unlinked API result URL')
                continue
            if not isinstance(row.get('text'), str) or not row['text'].strip():
                errors.append('Empty text result: ' + original)
                continue
            labels = {url: plain(label) for label, url in re.findall(
                r'\[([^\]\n]{1,100})\]\((https://[^)\s]+)\)', row['text'])}
            links = []
            for link in row.get('links') or []:
                if isinstance(link, str):
                    links.append({'url': link, 'text': labels.get(link, '')})
                elif isinstance(link, dict):
                    links.append({'url': link.get('url') or link.get('href', ''),
                                  'text': link.get('text') or link.get('title', '')})
            page = normalize_page({'url': original, 'final_url': final, 'title': row.get('title', ''),
                'text': row['text'], 'links': links, 'retrieved_at_utc': stamp, 'status': 'ok'})
            if final not in seen:
                pages.append(page)
                seen.add(final)
        for row in response.get('errors', []):
            target = acceptable(row.get('url', ''))
            errors.append('Fetch URL failed: ' + (target or 'Unknown URL') + '; status ' + str(row.get('status', UNKNOWN)))
        returned = {normalize_url(r['url']) for r in response.get('results', []) if acceptable(r.get('url', ''))}
        failed = {r.get('url') for r in response.get('errors', [])}
        for target in urls:
            if target not in returned and target not in failed:
                errors.append('Fetch omitted requested URL: ' + target)

    try:
        client = TinyFishClient(deadline=deadline, max_requests=max_requests)
        acquire([website])
        # An explicit shop link on the supplied official homepage may authorize
        # reading its commerce domain, not unrelated third-party sites.
        for p in pages:
            for link in p['links']:
                if link['url'].startswith('https://'):
                    host = urlsplit(link['url']).hostname.removeprefix('www.')
                    stem = urlsplit(website).hostname.removeprefix('www.').split('.')[0]
                    commerce_cue = re.search(r'\bshop\b|\bstore\b', link['text'], re.I)
                    branded_shop = len(stem) >= 5 and stem in host and 'shop' in host
                    if commerce_cue or branded_shop:
                        allowed_hosts.add(host)
        targets = []
        for p in pages:
            for link in p['links']:
                target = acceptable(link['url'])
                if target and target not in seen and relevant.search(target + ' ' + link['text']):
                    targets.append(target)
        if search:
            response = client.search('stationery notebooks product submissions contact',
                                     include_domains=sorted(allowed_hosts))
            for row in response.get('results', []):
                target = acceptable(row.get('url', ''))
                if target and target not in seen and relevant.search(target):
                    targets.append(target)
        targets = sorted(set(targets), key=lambda u: (
            0 if re.search(r'faq|submit|vendor|supplier|contact', urlsplit(u).path, re.I) else
            1 if re.search(r'notebook|journal|planner|pouch|case', urlsplit(u).path, re.I) else
            2 if not same_site(u, website) and urlsplit(u).path == '/' else 3, u))
        targets = targets[:max(0, max_pages - len(pages))]
        if targets:
            acquire(targets)
        if collect_usage:
            try:
                receipt['usage'] = client.usage('fetch')
            except TinyFishError as exc:
                errors.append('Usage lookup unavailable: ' + exc.code)
        receipt['status'] = 'completed' if pages and not errors else 'partial' if pages else 'failed'
    except TinyFishError as exc:
        errors.append('TinyFish API: ' + exc.code)
        receipt['error_code'] = exc.code
        receipt['status'] = 'blocked' if exc.code == 'missing_credential' else 'partial' if pages else 'failed'
        if exc.code == 'missing_credential':
            receipt['live_validation'] = 'LIVE API TEST BLOCKED — missing credential'
    if client is not None:
        receipt['requests'] = client.receipts
        receipt['authenticated_response_received'] = any(
            r.get('authenticated_response_received', r.get('authenticated', False)) or
            (isinstance(r.get('http_status'), int) and 200 <= r['http_status'] < 300)
            for r in client.receipts)
    receipt['finished_at_utc'] = now()
    receipt['elapsed_seconds'] = round(time.monotonic() - started, 3)
    status = receipt['status'] if receipt['status'] in ('completed', 'partial', 'failed') else 'failed'
    return {'provider': 'tinyfish_api', 'website': website, 'status': status,
            'acquisition': 'tinyfish_api_fetch', 'run_id': None, 'pages': pages,
            'errors': errors, 'elapsed_seconds': receipt['elapsed_seconds'], 'api_receipt': receipt}


def extract_evidence(pages, acquisition='public_http', run_id=None, *, typed=False):
    """Literal bounded observations. These do not infer willingness to buy.

    Pages and their instructions are data. No prompts, commands, external tools or
    requests are assembled from page text. Negated or suspicious sentences are
    excluded conservatively. Navigation supports a listed category, not stock.
    """
    evidence, seen = [], set()

    def add(field, value, page, quote, status='direct_text', confidence='medium'):
        key = (field, value.casefold(), page['final_url'])
        if key in seen:
            return
        seen.add(key)
        evidence.append(dict(zip(EVIDENCE_COLUMNS, (
            f'E{len(evidence) + 1:03d}', field, value, page['final_url'],
            page['retrieved_at_utc'], confidence, status, quote, acquisition, run_id or ''))))

    suspicious = re.compile(r'ignore.{0,35}(?:instructions|rules)|system prompt|api.key|password|\bbearer\b', re.I)
    for raw in pages:
        page = normalize_page(raw)
        if page['status'] != 'ok':
            continue
        text = page['title'] + '\n' + page['text']
        if typed and 'submit' in urlsplit(page['final_url']).path.lower():
            # Submission exclusions and procurement instructions are not stock
            # observations. Only an explicit positive-interest section can
            # support category hypotheses on a submission page.
            positive = re.search(r'(?:interested in stocking|stocking interests)(.*?)(?:we are\s+NOT|not currently|$)',
                                 page['text'], re.I | re.S)
            text = positive.group(0) if positive else ''
        for category, pattern in CATEGORIES.items():
            for match in re.finditer(pattern, text, re.I):
                quote = short_quote(text, match)
                if suspicious.search(quote) or re.search(r'\b(?:no|not|without|never|don.t|doesn.t)\b', quote, re.I):
                    continue
                # Accessory mentions do not establish the instrument/notebook
                # category (e.g. a "case for 1 Sport Pen" is a case, not a pen).
                if category == 'Pens & Writing' and re.search(r'case|pouch|storage|refill|ink|accessor|holder|clip', quote, re.I):
                    continue
                if category == 'Notebooks & Journals' and re.search(r'cover|refill|insert|accessor', quote, re.I):
                    continue
                if category == 'Planners & Calendars' and re.search(r'refill|insert|accessor', quote, re.I):
                    continue
                add('category', category, page, quote)
                break
        for brand in BRANDS:
            match = re.search(r'\b' + re.escape(brand) + r'\b', text, re.I)
            if match:
                quote = short_quote(text, match)
                if not suspicious.search(quote) and not re.search(r'\b(?:no|not|without|never|don.t|doesn.t|no longer)\b', quote, re.I):
                    add('brand', brand, page, quote)
        # Only retain a public business contact page, not named employee details.
        if re.search(r'/contact(?:[-/]|$)', urlsplit(page['final_url']).path, re.I) and page['text'].strip():
            add('contact', page['final_url'], page, page['title'] or page['text'].strip().splitlines()[0][:200])
        for link in page['links']:
            target = link['url']
            if not target.startswith('https://'):
                continue
            label = link['text']
            path = unquote(urlsplit(target).path).replace('-', ' ').replace('_', ' ')
            if same_site(target, page['final_url']) and '/collections/' in target:
                for category, pattern in CATEGORIES.items():
                    nav = label or path
                    if re.search(pattern, nav, re.I):
                        if category == 'Pens & Writing' and re.search(r'case|pouch|storage|refill|ink|accessor|holder|clip', nav, re.I):
                            continue
                        if category == 'Notebooks & Journals' and re.search(r'cover|refill|insert|accessor', nav, re.I):
                            continue
                        if category == 'Planners & Calendars' and re.search(r'refill|insert|accessor', nav, re.I):
                            continue
                        # A literal URL in links is evidence, not a fabricated quote.
                        add('category', category, page, target, 'navigation_link', 'medium')
            if same_site(target, page['final_url']) and re.search(r'/contact(?:[-/]|$)', urlsplit(target).path, re.I):
                add('contact', target, page, target, 'navigation_link', 'medium')
        # Extract only context near explicit incoming-product language. Unknown
        # if merely an outbound wholesale program or general contact invitation.
        for line in page['text'].splitlines():
            path = urlsplit(page['final_url']).path.lower()
            explicit = re.search(r'vendor|supplier|product submission|submit.{0,30}(?:product|work)|sell.{0,30}(?:your|our) (?:products?|work)', line, re.I)
            faq_product_route = ('faq' in path and re.search(r'email', line, re.I) and re.search(r'(?:your|new) products?', line, re.I))
            submission_route = ('submit' in path and re.search(r'submissions?@|submit.{0,40}(?:email|products?|work)', line, re.I))
            policy_context = ('faq' in path and re.search(r'small store|specific aesthetic|discourage.{0,30}bringing products', line, re.I))
            policy_constraint = ('submit' in path and re.search(r'refrain.{0,60}follow.?up|no follow.?up|do not.{0,30}follow.?up', line, re.I))
            if ((explicit or faq_product_route or submission_route or policy_context or policy_constraint)
                    and not suspicious.search(line) and not re.search(r'wholesale (?:customer|account)|stock (?:our|shorthand)', line, re.I)):
                line = line.strip()
                if line:
                    add('vendor_policy', line[:500], page, line[:500], 'policy_excerpt', 'medium')
        if typed and 'submit' in urlsplit(page['final_url']).path.lower():
            # Keep restrictions even when they occur after the first 500 chars
            # of a long paragraph. A short exact window is independently auditable.
            for match in re.finditer(r'refrain.{0,80}follow.?up|(?:cannot|unable to).{0,50}return.{0,30}samples|AI.assisted artworks|Fan art',
                                     page['text'], re.I):
                quote = short_quote(page['text'], match, words=20)
                add('vendor_policy', 'Restriction requiring human review: ' + match.group(0),
                    page, quote, 'policy_constraint', 'medium')
    if typed:
        for row in evidence:
            row['epistemic_status'] = 'fact_observation'
    return evidence


def load_catalog(path=ROOT / 'products.csv'):
    with Path(path).open(encoding='utf-8-sig', newline='') as handle:
        products = list(csv.DictReader(handle))
    if len(products) != 210 or len({p['sku'] for p in products}) != 210:
        raise ValueError('Expected the complete 210 unique Phase 1 SKU pool')
    required = {'sku', 'name_zh', 'category', 'image_path', 'source_sheet', 'source_row',
                'collection', 'units_per_carton', 'moq_cartons', 'moq_units', 'carton_qty_basis'}
    for p in products:
        if not required.issubset(p) or p['moq_cartons'] != '1' or p['moq_units'] != p['units_per_carton']:
            raise ValueError('Catalog fields / per-SKU one-carton rule invalid')
        image = (Path(path).parent / p['image_path']).resolve()
        if not image.is_relative_to(Path(path).parent.resolve() / 'images') or image.name != p['sku'] + '.webp' or not image.is_file():
            raise ValueError('Product image mismatch: ' + p['sku'])
    by_sku = {p['sku']: p for p in products}
    for sku in ('DTB6611-1', 'DTB6616-1'):
        if by_sku[sku]['units_per_carton'] != '112':
            raise ValueError('Owner-confirmed 112-unit carton rule changed')
    return products


def recommend(products, evidence, limit=4, *, strategy='evidence_review_v2'):
    if not 3 <= limit <= 5:
        raise ValueError('Recommendation limit must be 3 to 5')
    if strategy not in ('evidence_review_v2', 'legacy_source_order_v1'):
        raise ValueError('Unknown matching strategy')
    audit, candidates = [], []
    category_evidence = {}
    for e in evidence:
        if e['field'] == 'category' and e['verification_status'] in ('direct_text', 'navigation_link'):
            category_evidence.setdefault(e['value'], []).append(e)

    def evidence_priority(e):
        # This orders observations for review, not product appeal or buying intent.
        # A category-specific page is more precise than a homepage menu label.
        path = unquote(urlsplit(e['source_url']).path).replace('-', ' ').replace('_', ' ')
        dedicated = bool(re.search(CATEGORIES.get(e['value'], r'(?!)'), path, re.I))
        return 3 if dedicated and e['verification_status'] == 'direct_text' else 2 if e['verification_status'] == 'direct_text' else 1

    def shared_attributes(p, support):
        # Only literal, named attributes in the category observation and source
        # catalog name may refine the hypothesis. No style/brand affinity is inferred.
        corpus = '\n'.join(e['quote'] for e in support if e['verification_status'] == 'direct_text')
        attrs = []
        for size in ('A5', 'A6', 'B5', 'B6', 'M5'):
            pattern = r'(?<![A-Za-z0-9])' + size + r'(?![A-Za-z0-9])'
            if re.search(pattern, corpus, re.I) and re.search(pattern, p['name_zh'], re.I):
                attrs.append(size)
        for label, source_pattern, product_pattern in (
            ('blank', r'\bblank\b', r'空白'),
            ('lined', r'\b(?:lined|ruled)\b', r'横线'),
            ('grid', r'\b(?:squared|(?<!dot )(?<!dot-)grid)\b', r'方格'),
            ('dotted', r'\b(?:dotted|dot grid)\b', r'点阵|点格'),
            ('weekly', r'\bweekly\b', r'周计划'),
        ):
            if re.search(source_pattern, corpus, re.I) and re.search(product_pattern, p['name_zh']):
                attrs.append(label)
        return attrs

    details = {}
    for index, p in enumerate(products):
        category = p['category']
        support = category_evidence.get(category, [])
        if strategy == 'evidence_review_v2':
            support = sorted(support, key=lambda e: (-evidence_priority(e), e['source_url'], e['evidence_id']))
        # Keep Phase 1 immutable, but avoid treating answer/fortune books as
        # ordinary writing notebooks, and keychains as stationery stickers.
        ambiguous = bool(re.search(r'答案之书|钥匙扣|卡套|耳机|化妆|编织袋', p['name_zh']))
        eligible = bool(support) and not ambiguous
        reason = ('Phase 1 heuristic category needs manual review for this product subtype' if ambiguous
                  else 'Official category overlap; product category is a Phase 1 name inference' if support
                  else 'No observed official category evidence for this catalog category')
        attrs = shared_attributes(p, support) if eligible and strategy == 'evidence_review_v2' else []
        if eligible and strategy == 'evidence_review_v2':
            strength = evidence_priority(support[0])
            scope = {1: 'navigation only', 2: 'page text', 3: 'category-specific page text'}[strength]
            reason += '; support: ' + scope + '; literal shared attributes: ' + (', '.join(attrs) or 'none established')
            reason += '; tied review candidate, not a product-quality or purchase score'
            details[p['sku']] = (strength, attrs, scope)
        audit.append({'sku': p['sku'], 'product_category_inferred': category,
                      'eligible': str(eligible).lower(), 'reason': reason,
                      'retailer_evidence_ids': '|'.join(e['evidence_id'] for e in support),
                      'selected': 'false', 'tie_group': (category + '|' + (','.join(attrs) or 'category_only') + '|needs_human_review') if eligible and strategy == 'evidence_review_v2' else category if eligible else '',
                      'catalog_display_order': str(index + 1), 'aesthetic_fit': 'Needs human image review',
                      'order_feasibility': UNKNOWN})
        if eligible:
            candidates.append((index, p, support))
    if strategy == 'legacy_source_order_v1':
        # Preserve historical snapshots without silently rewriting past receipts.
        selected = candidates[:limit]
    else:
        # Show one representative per observed category before repeats. Within
        # each category, prefer explicit attribute overlap, then rotate collections
        # among equally supported products. SKU spelling only stabilizes the
        # display order; neither supplier row order nor aesthetics ranks products.
        pools = {}
        for candidate in candidates:
            pools.setdefault(candidate[1]['category'], []).append(candidate)
        for category, pool in list(pools.items()):
            ordered = []
            for count in sorted({len(details[c[1]['sku']][1]) for c in pool}, reverse=True):
                collections = {}
                for c in sorted(pool, key=lambda c: c[1]['sku']):
                    if len(details[c[1]['sku']][1]) == count:
                        collections.setdefault(c[1]['collection'], []).append(c)
                while any(collections.values()):
                    for collection in sorted(collections):
                        if collections[collection]:
                            ordered.append(collections[collection].pop(0))
            pools[category] = ordered
        categories = sorted(pools, key=lambda category: (-details[pools[category][0][1]['sku']][0], category))
        selected = []
        while len(selected) < limit and any(pools.values()):
            for category in categories:
                if pools[category] and len(selected) < limit:
                    selected.append(pools[category].pop(0))
    recommendations = []
    for display, (index, p, support) in enumerate(selected, 1):
        e = support[0]
        row = {k: p[k] for k in ('sku', 'name_zh', 'collection', 'image_path',
                    'units_per_carton', 'moq_cartons', 'moq_units', 'carton_qty_basis')}
        row.update(product_category_inferred=p['category'], product_source_sheet=p['source_sheet'],
                   product_source_row=p['source_row'], retailer_evidence_ids='|'.join(x['evidence_id'] for x in support),
                   retailer_evidence_url=e['source_url'], retailer_fact=e['quote'],
                   match_basis='category_overlap_inference',
                   match_reason='Observed ' + p['category'] + ' category. Catalog name/category implies product-family overlap only; source-order preview among tied eligible candidates.',
                   aesthetic_fit='Needs human image review', order_feasibility=UNKNOWN,
                   commercial_status='research_candidate_only', display_order=str(display), tie_group='all_eligible_need_review')
        if strategy == 'evidence_review_v2':
            strength, attrs, scope = details[p['sku']]
            tie = p['category'] + '|' + (','.join(attrs) or 'category_only') + '|needs_human_review'
            row.update(match_basis='category_and_literal_attributes_inference' if attrs else 'category_overlap_inference',
                       match_reason='Observed ' + p['category'] + ' through ' + scope + '. '
                       + ('Literal shared attributes: ' + ', '.join(attrs) + '. ' if attrs else 'No product-specific preference established. ')
                       + 'Review preview rotates observed categories and equally supported collections. SKU alphabetical order breaks display ties only; all candidates require human image and commercial review.',
                       tie_group=tie)
        recommendations.append(row)
        audit[index]['selected'] = 'true'
        audit[index]['tie_group'] = row['tie_group']
    return audit, recommendations


def write_csv(path, rows, columns):
    with Path(path).open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, lineterminator='\n')
        writer.writeheader()
        for row in rows:
            clean = {}
            for key in columns:
                value = safe_text(row.get(key, ''))
                # Formula escape public CSV cells without changing SKU facts.
                clean[key] = "'" + value if value.lstrip().startswith(('=', '+', '-', '@')) else value
            writer.writerow(clean)


def evidence_supported(e, pages):
    for page in pages:
        if e['source_url'] != page['final_url'] or e['retrieved_at_utc'] != page['retrieved_at_utc'] or page['status'] != 'ok':
            continue
        corpus = page['title'] + '\n' + page['text']
        if e['quote'] in corpus or e['quote'] in [x['url'] for x in page['links']]:
            return True
    return False


def derived_fields(evidence, pages, audit, recs, catalog_count):
    fields = {}
    for field in ('category', 'brand', 'contact', 'vendor_policy'):
        rows = [e for e in evidence if e['field'] == field]
        fields[{'category': 'categories', 'brand': 'brands'}.get(field, field)] = {
            'value': sorted({e['value'] for e in rows}) or UNKNOWN,
            'evidence_ids': [e['evidence_id'] for e in rows],
            'confidence': 'medium' if rows else UNKNOWN}
    good = sum(p['status'] == 'ok' for p in pages)
    summary = {'catalog_count': catalog_count, 'eligible_count': sum(a['eligible'] == 'true' for a in audit),
               'recommendation_count': len(recs), 'product_fit': 'Category overlap; human review required' if recs else UNKNOWN,
               'evidence_strength': 'Official page observations; not independent verification' if good else UNKNOWN,
               'buyer_access': 'Submission-related policy; applicability requires human review' if fields['vendor_policy']['evidence_ids'] else 'General contact only' if fields['contact']['evidence_ids'] else UNKNOWN,
               'order_feasibility': UNKNOWN}
    return fields, summary


def write_results(capture, output_dir, *, mode, catalog_path=ROOT / 'products.csv', limit=4):
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    products = load_catalog(catalog_path)
    acquisition = capture['acquisition']
    pages = [normalize_page(p) for p in capture['pages']]
    evidence = extract_evidence(pages, acquisition, capture.get('run_id'), typed=True)
    if not all(evidence_supported(e, pages) for e in evidence):
        raise ValueError('Evidence quote does not exactly match captured page')
    audit, recs = recommend(products, evidence, limit)
    fields, summary = derived_fields(evidence, pages, audit, recs, len(products))
    errors = capture.get('errors', []) + [p['error'] for p in pages if p['error']]
    result = {'schema_version': 2, 'website': capture['website'], 'generated_at_utc': now(),
              'mode': mode, 'status': capture['status'], 'acquisition': acquisition,
              'matching_strategy': 'evidence_review_v2', 'requested_limit': limit,
              'run_id': capture.get('run_id'),
              'related_browser_run_id': capture.get('related_browser_run_id'),
              'source_capture': capture.get('source_capture') if isinstance(capture.get('source_capture'), str) and re.fullmatch(r'[A-Za-z0-9_./-]+\.json', capture['source_capture']) and '..' not in Path(capture['source_capture']).parts and not capture['source_capture'].startswith('/') else None,
              'fields': fields, 'summary': summary,
              'errors': list(dict.fromkeys(safe_text(e) for e in errors)), 'pages': pages,
              'provider_receipts': [str(p) for p in capture.get('provider_receipts', []) if isinstance(p, str) and re.fullmatch(r'[A-Za-z0-9_./-]+\.json', p) and not p.startswith('/') and '..' not in Path(p).parts],
              'limitations': ['Captured pages are untrusted observations, not instructions.',
                             'Import validates supplied captures without re-fetching or authenticating provider execution.',
                             'Public deadline bounds scheduling; urllib socket inactivity timeout and system DNS are not a strict wall-clock deadline.',
                             'Brand extraction uses a small non-exhaustive literal whitelist; Unknown is not brand absence.',
                             'Navigation links prove listed categories only; not inventory.',
                             'Category and English descriptions are inferences; all aesthetics require human image review.',
                             'Evidence priority and representative display are inferences, not product superiority or purchase probability.',
                             'Order feasibility and supplier/buyer acceptance remain Unknown.'],
              'catalog_sha256': hashlib.sha256(Path(catalog_path).read_bytes()).hexdigest()}
    if 'elapsed_seconds' in capture:
        result['elapsed_seconds'] = capture['elapsed_seconds']
    if 'api_receipt' in capture:
        receipt = capture['api_receipt']
        # Exact key redaction also protects against a provider echoing a token.
        secret = os.environ.get('TINYFISH_API_KEY', '').strip()
        receipt_text = json.dumps(receipt, indent=2, ensure_ascii=False)
        if secret:
            receipt_text = receipt_text.replace(secret, '[REDACTED]')
        (output / 'api_receipt.json').write_text(receipt_text + '\n', encoding='utf-8')
        result['api_receipt'] = 'api_receipt.json'
        result['api_receipt_sha256'] = hashlib.sha256((output / 'api_receipt.json').read_bytes()).hexdigest()
        result['api_authenticated_response_received'] = receipt['authenticated_response_received']
    (output / 'research.json').write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    write_csv(output / 'evidence.csv', evidence, EVIDENCE_V2_COLUMNS)
    write_csv(output / 'candidate_audit.csv', audit, tuple(audit[0]))
    write_csv(output / 'recommendations.csv', recs, RECOMMENDATION_COLUMNS)
    md = ['# Retailer research brief', '', f"Website: {capture['website']}",
          f"Acquisition: `{acquisition}`. Status: **{capture['status']}**. Actual run ID: {capture.get('run_id') or 'None (page fetch has no browser-run ID)' }.",
          '', 'This is a research preview. No outreach, forms or purchases occurred.',
          f"All **{len(products)}** catalog SKUs were evaluated; **{summary['eligible_count']}** have observed category overlap. The following evidence-based representative preview needs human image review. Display order is not a buyer-intent or aesthetic ranking.", '',
          '| Dimension | Observation |', '|---|---|']
    md += [f'| {k.replace("_", " ").title()} | {summary[k]} |' for k in ('product_fit', 'evidence_strength', 'buyer_access', 'order_feasibility')]
    if 'api_receipt' in capture:
        md += ['', 'Direct API receipt: [api_receipt.json](api_receipt.json). '
               f"Authenticated response received: **{capture['api_receipt']['authenticated_response_received']}**. "
               'Fetch is synchronous; there is no browser run ID. Provider request IDs, bounded request counts and available usage are in the receipt; unreported billed cost is Unknown.']
        if capture['api_receipt'].get('live_validation'):
            md += ['', '**' + capture['api_receipt']['live_validation'] + '**']
    if capture.get('related_browser_run_id'):
        md += ['', 'Related real TinyFish browser run: `' + capture['related_browser_run_id'] + '`. This separate receipt supports the review; imported field quotes below were fetched with `fetch_content`, which has no browser-run ID.']
    md += ['', '| SKU | Inferred category | Minimum per SKU | Evidence |', '|---|---|---|---|']
    for r in recs:
        md.append(f"| {r['sku']} | {r['product_category_inferred']} | 1 carton / {r['moq_units']} units | [{r['retailer_evidence_ids']}]({r['retailer_evidence_url']}) |")
    if len(recs) < 3:
        md += ['', '**Insufficient evidence for 3–5 candidates. Do not fill the gap with invented matches.**']
    for r in recs:
        relative = Path(__import__('os').path.relpath(Path(catalog_path).parent / r['image_path'], output))
        md += ['', f"### {r['sku']} — {r['name_zh']}", f"![{r['sku']}]({relative.as_posix()})", r['match_reason'],
               f"Source: `{r['product_source_sheet']}`, row {r['product_source_row']}. Aesthetic fit: **Needs human image review**. MOQ: one full carton, {r['moq_units']} units. Order feasibility: **Unknown**."]
    policy_rows = [e for e in evidence if e['field'] == 'vendor_policy']
    if policy_rows:
        md += ['', '## Submission policy excerpts', '', 'Read the full source before any action; these captured excerpts do not establish acceptance of Kinbor or any product.']
        for e in policy_rows:
            md += ['', '> ' + e['quote'], f"Source: [{e['evidence_id']}]({e['source_url']}). Retrieved {e['retrieved_at_utc']}. Confidence: {e['confidence']}."]
    md += ['', '## Evidence and unknowns', '', 'See `evidence.csv` for exact quotes, field-level source URLs, retrieval timestamps and confidence. `research.json` retains the captured page excerpts used to check those quotes. Unknown means not established within this bounded capture, not absent from the website.', '',
           'Human review must check the actual image, paper, language/layout, styling, dimensions, resale authority, supplier availability, costs and buyer acceptance of one carton per individual SKU. A general contact page is not permission for a vendor pitch. Read every submission condition on the source page before any action. No automatic aesthetic or buying-intent conclusion is made.']
    (output / 'buyer_brief.md').write_text('\n'.join(md) + '\n', encoding='utf-8')
    return result


def validate_output(output_dir, catalog_path=ROOT / 'products.csv'):
    output = Path(output_dir)
    result = json.loads((output / 'research.json').read_text(encoding='utf-8'))
    products = load_catalog(catalog_path)
    if result['catalog_sha256'] != hashlib.sha256(Path(catalog_path).read_bytes()).hexdigest():
        raise ValueError('Catalog snapshot hash differs')
    def read(name):
        with (output / name).open(encoding='utf-8-sig', newline='') as handle:
            return list(csv.DictReader(handle))
    evidence, audit, recs = read('evidence.csv'), read('candidate_audit.csv'), read('recommendations.csv')
    if len(audit) != 210 or {a['sku'] for a in audit} != {p['sku'] for p in products}:
        raise ValueError('Full catalog audit missing or duplicated')
    pages = [normalize_page(p) for p in result['pages']]
    if len({e['evidence_id'] for e in evidence}) != len(evidence):
        raise ValueError('Duplicate evidence IDs')
    for e in evidence:
        check_timestamp(e['retrieved_at_utc'])
        if not evidence_supported(e, pages):
            raise ValueError('Unsupported / inaccurate evidence quote')
    # Recompute deterministic inferences, do not trust a CSV claiming support.
    version = result.get('schema_version', 1)
    expected_evidence = extract_evidence(pages, result['acquisition'], result.get('run_id'), typed=version >= 2)
    if evidence != expected_evidence:
        raise ValueError('Evidence differs from deterministic page extraction')
    limit = result.get('requested_limit', len(recs) if len(recs) >= 3 else 4)
    strategy = result.get('matching_strategy', 'legacy_source_order_v1')
    expected_audit, expected_recs = recommend(products, evidence, limit, strategy=strategy)
    if audit != expected_audit or recs != expected_recs:
        raise ValueError('Recommendation / audit data drift, invented SKU or MOQ')
    fields, summary = derived_fields(evidence, pages, audit, recs, len(products))
    if result['fields'] != fields or result['summary'] != summary:
        raise ValueError('Derived field / dimension drift from observed evidence')
    if result['status'] not in ('completed', 'partial', 'failed') or result['mode'] not in ('public', 'public_http', 'import', 'tinyfish'):
        raise ValueError('Invalid research mode/status')
    if result['acquisition'] not in ('public_http', 'fetch_content', 'run_web_automation', 'tinyfish_api_fetch'):
        raise ValueError('Invalid acquisition provenance')
    if result['acquisition'] == 'public_http' and result['run_id'] is not None:
        raise ValueError('Ordinary HTTP is not a TinyFish run')
    if result['acquisition'] == 'run_web_automation' and not result['run_id']:
        raise ValueError('Browser run receipt requires its real run ID')
    if result['mode'] == 'tinyfish' or result['acquisition'] == 'tinyfish_api_fetch':
        if result['mode'] != 'tinyfish' or result['acquisition'] != 'tinyfish_api_fetch':
            raise ValueError('Direct API provenance mismatch')
        path = output / 'api_receipt.json'
        if hashlib.sha256(path.read_bytes()).hexdigest() != result.get('api_receipt_sha256'):
            raise ValueError('Direct API receipt drift')
        receipt = json.loads(path.read_text(encoding='utf-8'))
        if receipt.get('execution') != 'local_python_direct_api' or receipt.get('fallback') != 'none':
            raise ValueError('Invalid direct API receipt')
        if pages and not receipt.get('authenticated_response_received'):
            raise ValueError('API evidence requires an authenticated response')
        if result['api_authenticated_response_received'] != receipt.get('authenticated_response_received'):
            raise ValueError('API authentication receipt drift')
        expected_status = 'failed' if receipt.get('status') == 'blocked' else receipt.get('status')
        if result['status'] != expected_status:
            raise ValueError('API status receipt drift')
        if result['status'] == 'completed' and (not pages or result['errors'] or not any(
                r.get('api') == 'fetch' and r.get('method') == 'POST' and r.get('http_status') == 200
                for r in receipt.get('requests', []))):
            raise ValueError('Completed API research requires successful Fetch evidence without errors')
    return {'status': 'passed', 'catalog_count': len(products), 'evidence_count': len(evidence),
            'recommendation_count': len(recs), 'validation_mode': 'offline; no research or API call'}


def validate_outputs(output_dir, repo_root=ROOT):
    """Compatibility helper for the Phase 2 data integrator."""
    return validate_output(output_dir, Path(repo_root) / 'products.csv')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=('tinyfish', 'public_http', 'public', 'import', 'validate'), default='tinyfish',
                        help='tinyfish: direct official API (default); public_http/public: explicit HTTP fallback; import: saved connector capture; validate: offline only')
    parser.add_argument('--url', help='Official retailer HTTPS URL; required for public/import')
    parser.add_argument('--input', type=Path, help='Version 1 normalized real TinyFish connector capture JSON (import only)')
    parser.add_argument('--output-dir', type=Path, default=ROOT / 'work' / 'research', help='Output folder or existing folder to validate')
    parser.add_argument('--catalog', type=Path, default=ROOT / 'products.csv')
    parser.add_argument('--limit', type=int, choices=(3, 4, 5), default=4, help='Maximum human-review candidate preview size')
    parser.add_argument('--max-pages', type=int, default=6, help='Page cap: API 1–10; public HTTP 1–12')
    parser.add_argument('--timeout', type=float, default=15, help='Per-request seconds, 1–30')
    parser.add_argument('--deadline', type=float, default=None, help='Scheduling budget seconds: API default 240, public default 120; DNS/socket timeout may overrun')
    parser.add_argument('--max-api-requests', type=int, default=4, help='Total API attempt cap including retries/optional search/usage, 1–8')
    parser.add_argument('--tinyfish-search', action='store_true', help='Add a domain-restricted Search API discovery call; snippets never become facts')
    parser.add_argument('--collect-usage', action='store_true', help='Query official Fetch usage endpoint; no automatic wallet changes')
    args = parser.parse_args(argv)
    try:
        if args.mode == 'validate':
            if args.input or args.url:
                parser.error('validate reads existing outputs only; do not pass --input/--url')
            print(json.dumps(validate_output(args.output_dir, args.catalog), indent=2))
            return 0
        if not args.url:
            parser.error('--url is required for research')
        website = normalize_url(args.url)
        if args.mode == 'import':
            if not args.input:
                parser.error('--input is required for connector import')
            capture = validate_capture(json.loads(args.input.read_text(encoding='utf-8')), website)
        elif args.mode == 'tinyfish':
            if args.input:
                parser.error('Direct API mode does not accept captures')
            deadline = 240 if args.deadline is None else args.deadline
            if not 1 <= args.max_pages <= 10 or not 10 <= deadline <= 600 or not 1 <= args.max_api_requests <= 8:
                parser.error('API limits out of bounds')
            capture = tinyfish_capture(website, max_pages=args.max_pages, deadline=deadline,
                                      max_requests=args.max_api_requests, search=args.tinyfish_search,
                                      collect_usage=args.collect_usage)
        else:
            if args.input:
                parser.error('--input is only supported in import mode')
            deadline = 120 if args.deadline is None else args.deadline
            if not 1 <= args.max_pages <= 12 or not 1 <= args.timeout <= 30 or not 10 <= deadline <= 180:
                parser.error('Public limits out of bounds')
            capture = public_capture(website, max_pages=args.max_pages, timeout=args.timeout, deadline=deadline)
        result = write_results(capture, args.output_dir, mode=args.mode, catalog_path=args.catalog, limit=args.limit)
        print(json.dumps({k: result[k] for k in ('status', 'acquisition', 'run_id', 'summary', 'errors')}, indent=2))
        return 0 if result['status'] == 'completed' else 2
    except (ValueError, OSError, KeyError, json.JSONDecodeError) as exc:
        print(json.dumps({'status': 'failed', 'error': plain(str(exc)), 'run_id': None}), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
