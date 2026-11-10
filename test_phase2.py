"""Review-queue invariants; no network or buying-probability model."""
import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import phase2


class ReviewQueueIntegrity(unittest.TestCase):
    def setUp(self):
        self.rows = phase2.migrate(
            phase2.read("retailers.csv"), phase2.read("sku_matches.csv"), phase2.read("evidence.csv")
        )

    def test_catalog_and_provenance_corruption_is_rejected(self):
        phase2.validate(*self.rows)
        for field, value in (
            ("sku", "INVENTED-SKU"), ("moq_units", "1"), ("image_path", "images/WRONG.webp"),
            ("product_source_row", "99999"), ("retailer_evidence_ids", "R20-E04"),
        ):
            with self.subTest(field=field):
                rows = copy.deepcopy(self.rows)
                rows[1][0][field] = value
                with self.assertRaises(ValueError):
                    phase2.validate(*rows)

    def test_no_active_total_score_or_confirmed_feasibility(self):
        for field, value in (("contact_priority_score", "99.99"), ("order_feasibility", "Confirmed")):
            with self.subTest(field=field):
                rows = copy.deepcopy(self.rows)
                rows[0][0][field] = value
                with self.assertRaises(ValueError):
                    phase2.validate(*rows)

    def test_ties_and_legacy_hold_are_explicit(self):
        for retailer in self.rows[0]:
            with self.subTest(retailer=retailer["retailer_id"]):
                expected = "1 (tie; human review)" if retailer["research_status"] == "current_pilot" else "Hold: source revalidation"
                self.assertEqual(retailer["review_priority"], expected)
                self.assertEqual(retailer["order_feasibility"], "Unknown")
                for dimension in ("product_fit", "evidence_strength", "buyer_access"):
                    self.assertTrue(retailer[dimension])

    def test_current_style_queue_and_frozen_comparator_can_render_together(self):
        styles=[{'retailer':'atlas','selected_skus':['DT55566'],
                 'brief':'live/atlas/style_brief.md'},
                {'retailer':'wonder-fair','selected_skus':[],
                 'brief':'live/wonder-fair/style_brief.md'}]
        with tempfile.TemporaryDirectory() as td, patch.object(phase2,'DATA',Path(td)), \
                patch.object(phase2,'write'),patch.object(phase2,'validate'), \
                patch.object(phase2,'current_style_reviews',return_value=styles):
            phase2.refresh(*self.rows)
            text=(Path(td)/'review_queue.md').read_text()
        self.assertIn('DT55566',text)
        self.assertIn('Insufficient evidence; no forced recommendation',text)
        self.assertIn('frozen comparators',text)
        self.assertIn('Hold',text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
