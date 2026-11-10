"""Offline evaluation integrity tests; fixtures are not human quality labels."""
import csv
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from kinbor import research

from kinbor import evaluation


class ReviewEvaluationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.products = research.load_catalog()

    def fixture(self, retailer='atlas'):
        probes = {sku for sku, _ in evaluation.PROBES}
        ordinary = [p['sku'] for p in self.products if p['sku'] not in probes]
        return {'retailer_id': retailer, 'baseline_skus': ordinary[:4],
            'selected_skus': ordinary[4:8],
            'baseline_reasons': {sku: 'Captured old category reason for ' + sku for sku in ordinary[:4]},
            'candidates': [{'sku': p['sku'], 'image_path': p['image_path'],
                'moq_units': p['moq_units'], 'status': 'needs_human_review',
                'reason': 'Synthetic evidence comparison for ' + p['sku'],
                'counterevidence': ['Synthetic uncertainty'],
                'retailer_evidence_ids': ['fixture-P01'],
                'retailer_evidence_urls': ['https://retailer-fixture.org/products/example']}
                for p in self.products]}

    def test_36_unique_comparisons_cover_both_shortlists_and_hypothesis_probes(self):
        results = [self.fixture(r) for r in evaluation.RETAILERS]
        rows, keys = evaluation.build_review_rows(results, self.products)
        self.assertEqual(len(rows), 36)
        self.assertEqual(len({r['review_id'] for r in rows}), 36)
        key_map = {r['review_id']: r for r in keys}
        for result in results:
            selected = {r['sku'] for r in rows if r['retailer_id'] == result['retailer_id']}
            self.assertEqual(len(selected), 12)
            self.assertTrue(set(result['baseline_skus'] + result['selected_skus']) <= selected)
            self.assertTrue({sku for sku, _ in evaluation.PROBES} <= selected)
        for row in rows:
            key = key_map[row['review_id']]
            self.assertNotIn('sample_reason', row)
            self.assertEqual(row['choice'], '')
            self.assertEqual(row['sku_fit'], '')
            self.assertIn('Synthetic evidence', row['comparison_' + ('a' if key['a_system'] == 'new' else 'b')])
        self.assertEqual((rows, keys), evaluation.build_review_rows(results, list(reversed(self.products))))

    def test_catalog_and_moq_tampering_is_rejected(self):
        fixture = self.fixture()
        fixture['candidates'][0]['moq_units'] = '1'
        with self.assertRaisesRegex(ValueError, 'fact drift'):
            evaluation.build_review_rows([fixture], self.products)
        fixture = self.fixture()
        fixture['candidates'].pop()
        with self.assertRaisesRegex(ValueError, 'complete catalog'):
            evaluation.build_review_rows([fixture], self.products)

    def test_missing_baseline_reason_never_invents_aesthetic_rationale(self):
        fixture = self.fixture()
        fixture.pop('baseline_reasons')
        rows, keys = evaluation.build_review_rows([fixture], self.products)
        key_map = {r['review_id']: r for r in keys}
        for row in rows:
            key = key_map[row['review_id']]
            old = row['comparison_' + ('a' if key['a_system'] == 'old' else 'b')]
            if row['sku'] in fixture['baseline_skus']:
                self.assertIn('not recorded', old)
            else:
                self.assertEqual(old, 'Not selected by category baseline.')

    def test_summary_counts_preferences_without_accuracy_or_fabricated_timing(self):
        rows, keys = evaluation.build_review_rows([self.fixture()], self.products)
        key_map = {r['review_id']: r for r in keys}
        rows[0]['choice'] = 'A' if key_map[rows[0]['review_id']]['a_system'] == 'new' else 'B'
        rows[0]['sku_fit'] = 'yes'
        rows[0]['seconds'] = '42.5'
        rows[1]['choice'], rows[1]['sku_fit'] = 'uncertain', 'uncertain'
        rows[2]['choice'], rows[2]['sku_fit'] = 'tie', 'no'
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'reviews.csv'
            research.write_csv(path, rows, evaluation.REVIEW_COLUMNS)
            research.write_csv(path.with_suffix('.key.csv'), keys, evaluation.KEY_COLUMNS)
            report = evaluation.summarize(path)
            self.assertEqual(report['preference_counts']['new'], 1)
            self.assertEqual(report['preference_counts']['uncertain'], 1)
            self.assertEqual(report['definite_fit_labels'], 2)
            self.assertEqual(report['uncertain_fit_excluded'], 1)
            self.assertEqual(report['recorded_review_seconds'], 42.5)
            self.assertIn('Not computed', report['accuracy'])
            rows[0]['seconds'] = 'nan'
            research.write_csv(path, rows, evaluation.REVIEW_COLUMNS)
            with self.assertRaisesRegex(ValueError, 'finite'):
                evaluation.summarize(path)

    def test_generation_preserves_existing_responses_and_mapping(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for retailer in evaluation.RETAILERS:
                pilot = root / retailer
                pilot.mkdir()
                (pilot / 'matching.json').write_text(json.dumps(self.fixture(retailer)), encoding='utf-8')
            output = root / 'reviews.csv'
            # Synthetic fixture decisions are not real evidence bundles. Test
            # orchestration here; matching's own tests cover saved validation.
            with patch('kinbor.matching.validate_saved', create=True) as validate:
                report = evaluation.generate(root, output)
                self.assertEqual(validate.call_count, 3)
            self.assertEqual(report['gold_labels'], 0)
            rows = evaluation.read_csv(output)
            rows[0]['reason'] = 'Existing reviewer response must survive.'
            research.write_csv(output, rows, evaluation.REVIEW_COLUMNS)
            snapshot = output.read_bytes()
            with self.assertRaisesRegex(ValueError, 'exists'):
                evaluation.generate(root, output)
            self.assertEqual(output.read_bytes(), snapshot)
            summary = evaluation.summarize(output)
            self.assertEqual(summary['preference_counts'], {'pending': 36})
            self.assertEqual(summary['recorded_review_seconds'], 'Unknown')

    def test_invalid_saved_matching_never_creates_review_or_key(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            output = root / 'reviews.csv'
            with patch('kinbor.matching.validate_saved', create=True, side_effect=ValueError('Unsupported saved evidence')):
                with self.assertRaisesRegex(ValueError, 'Unsupported'):
                    evaluation.generate(root, output)
            self.assertFalse(output.exists())
            self.assertFalse(output.with_suffix('.key.csv').exists())


if __name__ == '__main__':
    unittest.main()
