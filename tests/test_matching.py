"""Offline matching tests using the real immutable catalog and synthetic evidence.

These are review-selection tests, never live TinyFish receipts or buyer validation.
"""
import csv
import hashlib
import json
from pathlib import Path
import unittest

from kinbor import research


def baseline(*args, **kwargs):
    """Explicit historical comparator, never the new research default."""
    kwargs.setdefault('strategy', 'evidence_review_v2')
    return research.recommend(*args, **kwargs)


def observation(category, *, quote=None, path='/collections/notebooks',
                status='direct_text', eid='E001'):
    return {'evidence_id': eid, 'field': 'category', 'value': category,
            'source_url': 'https://retailer-fixture.org' + path,
            'retrieved_at_utc': '2026-11-10T02:00:00Z', 'confidence': 'medium',
            'verification_status': status, 'quote': quote or category,
            'acquisition': 'offline_synthetic', 'run_id': ''}


class EvidenceReviewMatching(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.products = research.load_catalog()

    def test_new_preview_does_not_depend_on_supplier_row_order(self):
        evidence = [observation('Notebooks & Journals')]
        audit, selected = baseline(self.products, evidence)
        _, reordered = baseline(list(reversed(self.products)), evidence)
        self.assertEqual([r['sku'] for r in selected], [r['sku'] for r in reordered])
        self.assertEqual(len(audit), 210)
        legacy = baseline(self.products, evidence,
                                    strategy='legacy_source_order_v1')[1]
        self.assertNotEqual([r['sku'] for r in selected], [r['sku'] for r in legacy])
        self.assertTrue(all('needs_human_review' in r['tie_group'] for r in selected))
        self.assertTrue(all('top' not in r['match_reason'].lower() for r in selected))

    def test_retailer_categories_change_selection_without_forcing_diversity(self):
        notebook_evidence = [observation('Notebooks & Journals')]
        pen_evidence = [observation('Pens & Writing', path='/collections/pens')]
        notebooks = baseline(self.products, notebook_evidence)[1]
        pens = baseline(self.products, pen_evidence)[1]
        self.assertTrue(all(r['product_category_inferred'] == 'Notebooks & Journals' for r in notebooks))
        self.assertTrue(all(r['product_category_inferred'] == 'Pens & Writing' for r in pens))
        # Identical observations remain identical; no retailer-name or random quota.
        self.assertEqual(notebooks, baseline(self.products, notebook_evidence)[1])
        self.assertFalse({r['sku'] for r in notebooks} & {r['sku'] for r in pens})

    def test_preview_covers_each_supported_category_before_repeating(self):
        evidence = [observation('Notebooks & Journals'),
                    observation('Planners & Calendars', path='/collections/planners', eid='E002'),
                    observation('Pouches & Cases', path='/collections/pouches', eid='E003')]
        _, selected = baseline(self.products, evidence)
        self.assertEqual(len({r['product_category_inferred'] for r in selected[:3]}), 3)

    def test_literal_attributes_refine_hypothesis_and_keep_real_carton_quantity(self):
        evidence = [observation('Refills & Inserts', quote='A6 blank notebook refills',
                                path='/collections/refills')]
        audit, selected = baseline(self.products, evidence)
        self.assertEqual(selected[0]['sku'], 'DTB6611-1')
        self.assertEqual(selected[0]['units_per_carton'], '112')
        self.assertEqual(selected[0]['moq_units'], '112')
        self.assertEqual(selected[0]['moq_cartons'], '1')
        self.assertIn('A6, blank', selected[0]['match_reason'])
        self.assertEqual(selected[0]['match_basis'], 'category_and_literal_attributes_inference')
        self.assertEqual(selected[0]['order_feasibility'], 'Unknown')
        self.assertEqual(selected[0]['aesthetic_fit'], 'Needs human image review')
        self.assertEqual(next(a for a in audit if a['sku'] == 'DTB6611-1')['tie_group'],
                         selected[0]['tie_group'])

    def test_precise_page_is_primary_source_and_navigation_remains_weak(self):
        evidence = [observation('Notebooks & Journals', quote='https://retailer-fixture.org/collections/notebooks',
                                path='/', status='navigation_link', eid='E001'),
                    observation('Notebooks & Journals', quote='Notebooks',
                                path='/collections/notebooks', eid='E002')]
        audit, selected = baseline(self.products, evidence)
        self.assertTrue(all(r['retailer_evidence_url'].endswith('/collections/notebooks') for r in selected))
        self.assertTrue(all('category-specific page text' in r['match_reason'] for r in selected))
        self.assertTrue(all('literal shared attributes: none established' in a['reason']
                            for a in audit if a['eligible'] == 'true'))

    def test_no_unsupported_product_or_aesthetic_matches(self):
        audit, selected = baseline(self.products, [])
        self.assertEqual(selected, [])
        self.assertEqual(sum(a['eligible'] == 'true' for a in audit), 0)
        evidence = [observation('Notebooks & Journals', quote='Midori notebooks')]
        selected = baseline(self.products, evidence)[1]
        self.assertTrue(all(r['match_basis'] == 'category_overlap_inference' for r in selected))
        self.assertTrue(all('No product-specific preference established' in r['match_reason'] for r in selected))

    def test_legacy_strategy_preserves_baseline_full_catalog_results(self):
        # Frozen before cleanup at 54c8776, using the retained real evidence.
        # Hashes cover every audit/recommendation cell; this is offline replay.
        expected = {
            'atlas': '25bd821a53d32d5858d15fc479a29d727ef4fe26d7ff95415b600fa19939a7eb',
            'shorthand': '20f5bbcbe32073602784d91b936e8cf9b2678ab9b70f4908fd62d1774f2effaf',
            'wonder-fair': '13613d3c37a8379e0c166e1e2c9b2d31cbd6d7ac573faec72c6cc606cabb65cb',
        }
        for slug, digest in expected.items():
            with self.subTest(slug=slug):
                folder = Path(research.ROOT) / 'examples' / 'retailers' / slug
                def read(name):
                    with (folder / name).open(encoding='utf-8-sig', newline='') as f:
                        return list(csv.DictReader(f))
                audit, selected = baseline(self.products, read('evidence.csv'),
                                                     strategy='legacy_source_order_v1')
                actual = hashlib.sha256(json.dumps([audit, selected], sort_keys=True).encode()).hexdigest()
                self.assertEqual(actual, digest)

    def test_saved_direct_api_bundles_recompute_without_network(self):
        for slug in ('atlas', 'shorthand', 'wonder-fair'):
            with self.subTest(slug=slug):
                folder = Path(research.ROOT) / 'examples' / 'retailers' / slug
                self.assertEqual(research.validate_output(folder)['status'], 'passed')


if __name__ == '__main__':
    unittest.main(verbosity=2)
