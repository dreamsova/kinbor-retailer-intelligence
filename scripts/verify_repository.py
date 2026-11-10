#!/usr/bin/env python3
"""Read-only offline checks for the preserved catalog and both pilot generations.

Print a fresh JSON receipt to stdout. No network calls, output regeneration or
review writes occur; redirect stdout to an ignored work/ file if desired.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from kinbor import evaluation, matching, pipeline, research
from kinbor.paths import CATALOG, EXAMPLES, RETAILERS, EVALUATION, NOTES, phase1_path


def check_document_links():
    """Check local inline Markdown targets, including the saved brief images."""
    documents = [ROOT / 'README.md', *sorted((ROOT / 'docs').rglob('*.md')),
                 *sorted(EXAMPLES.rglob('*.md')),
                 *sorted((ROOT / 'tests').rglob('*.md')),
                 *sorted(CATALOG.rglob('*.md')), *sorted((ROOT / 'kinbor').rglob('*.md'))]
    checked = 0
    for document in documents:
        # Code examples can contain illustrative Markdown rather than links.
        prose = re.sub(r'^```.*?^```', '', document.read_text(encoding='utf-8'),
                       flags=re.MULTILINE | re.DOTALL)
        for target in re.findall(r'\[[^\]\n]*\]\(([^)\n]+)\)', prose):
            target = target.strip().removeprefix('<').removesuffix('>')
            parts = urlsplit(target)
            if parts.scheme or parts.netloc or not parts.path:
                continue
            path = (document.parent / unquote(parts.path)).resolve()
            if not path.is_relative_to(ROOT) or not path.exists():
                raise ValueError(f'Broken local link: {document.relative_to(ROOT)} -> {target}')
            checked += 1
    return {'documents': len(documents), 'local_targets_checked': checked,
            'scope': 'inline Markdown file/image targets; remote URLs and anchors not fetched'}


def verify():
    manifest = json.loads((ROOT / 'docs/phase1_manifest.json').read_text(encoding='utf-8'))
    expected = manifest['phase1_files']
    pipeline.require(len(expected) == 214, 'Phase 1 manifest must retain 214 entries')
    for name, digest in expected.items():
        actual = hashlib.sha256(phase1_path(name).read_bytes()).hexdigest()
        pipeline.require(actual == digest, 'Phase 1 preservation mismatch: ' + name)

    products = research.load_catalog()
    images = {p.name for p in (CATALOG / 'images').glob('*.webp')}
    pipeline.require(len(products) == 210 and images == {p['sku'] + '.webp' for p in products},
                   'Catalog must retain exactly 210 joined SKU images')
    tables = tuple(pipeline.read(name) for name in ('retailers.csv', 'sku_matches.csv', 'evidence.csv'))
    combined = pipeline.validate(*tables)
    pilots = {}
    for slug in pipeline.PILOTS:
        directory = RETAILERS / slug
        frozen = research.validate_output(directory)
        style = matching.validate_saved(directory)
        result = json.loads((directory / 'matching.json').read_text(encoding='utf-8'))
        pilots[slug] = {'frozen_research': frozen, 'current_style': style,
                        'product_observations': len(result['observations']),
                        'shown_review_candidates': result['selected_skus'],
                        'supported_hypotheses_needing_review': sum(
                            c['status'] == 'needs_human_review' for c in result['candidates']),
                        'multimodal_status': result['multimodal']['status']}
    notes = matching.load_notes(NOTES, products)
    return {'status': 'passed', 'mode': 'offline; read-only saved evidence checks',
            'checked_at_utc': datetime.now(timezone.utc).isoformat(timespec='seconds'),
            'phase1_preserved_files': len(expected), 'catalog_skus': len(products),
            'catalog_images': len(images), 'annotated_sku_images': len(notes),
            'combined_frozen_tables': combined,
            'negative_controls_passed': pipeline.fault_checks(*tables),
            'pilots': pilots,
            'review_summary': evaluation.summarize(EVALUATION / 'reviews.csv'),
            'documentation_links': check_document_links(),
            'limits': 'Integrity checks do not establish fresh site truth, live multimodal quality, '
                      'human preference or commercial conversion.'}


def main():
    try:
        print(json.dumps(verify(), indent=2, ensure_ascii=False))
    except (OSError, ValueError, KeyError) as exc:
        print(json.dumps({'status': 'failed', 'error': research.safe_text(str(exc))}))
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
