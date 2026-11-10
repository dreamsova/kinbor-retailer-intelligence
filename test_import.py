"""Small test suite; runs without the private supplier spreadsheets."""
import csv
from collections import Counter
from pathlib import Path
import tempfile
import unittest
import zipfile

import importlib.util

BASE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("kinbor_import", BASE / "import.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class PublicCatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with (BASE / "products.csv").open(encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            cls.columns = reader.fieldnames
            cls.records = list(reader)
        cls.by_sku = {r["sku"]: r for r in cls.records}

    def test_real_sku_count(self):
        self.assertEqual(len(self.records), 210)
        self.assertEqual(len(self.by_sku), 210)
        self.assertEqual(Counter(r["collection"] for r in self.records),
                         {"Original Design": 120, "Brunch Brother": 90})

    def test_public_allowlist_only(self):
        self.assertEqual(self.columns, mod.COLUMNS)
        private_terms = {"price", "cost", "exw", "inventory", "stock", "barcode", "rebate", "order"}
        self.assertFalse(any(word in col.lower() for col in self.columns for word in private_terms))

    def test_one_carton_per_sku(self):
        for r in self.records:
            with self.subTest(sku=r["sku"]):
                self.assertEqual(int(r["moq_cartons"]), 1)
                self.assertGreater(int(r["units_per_carton"]), 0)
                self.assertEqual(int(r["moq_units"]), int(r["units_per_carton"]))

    def test_user_confirmed_cartons(self):
        for sku in ("DTB6611-1", "DTB6616-1"):
            self.assertEqual(int(self.by_sku[sku]["units_per_carton"]), 112)
            self.assertEqual(self.by_sku[sku]["carton_qty_basis"], "user_confirmed")
            self.assertEqual(self.by_sku[sku]["packing_raw"], "1/24/48")

    def test_source_provenance(self):
        for r in self.records:
            self.assertTrue(r["source_sheet"])
            self.assertGreater(int(r["source_row"]), 0)
            self.assertTrue(r["name_zh"])
            self.assertTrue(r["sku"])

    def test_known_examples(self):
        self.assertEqual(self.by_sku["DT54731"]["name_zh"], "索引标记自粘本-1")
        self.assertEqual(int(self.by_sku["DT54731"]["units_per_carton"]), 240)
        self.assertEqual(self.by_sku["HX588237"]["collection"], "Brunch Brother")

    def test_no_formulas_in_public_csv(self):
        for row in self.records:
            for text in row.values():
                self.assertFalse(str(text).startswith(("=", "+", "-", "@", "\t", "\r")))

    def test_export_round_trip(self):
        with tempfile.TemporaryDirectory() as d:
            output = Path(d) / "safe.csv"
            mod.write_catalog([{"sku": "SAFE", "name_zh": "=FORMULA", **{
                key: "" for key in mod.COLUMNS if key not in {"sku", "name_zh"}}}], output)
            with output.open(encoding="utf-8-sig", newline="") as f:
                item = next(csv.DictReader(f))
            # CSV writer is safe even if called directly with an untrusted record.
            self.assertEqual(item["name_zh"], "'=FORMULA")
            self.assertEqual(mod._safe_text("=FORMULA"), "'=FORMULA")

    def test_quantity_validation(self):
        for invalid in ("", "0", "1.5", "-48", "unavailable"):
            with self.assertRaises(ValueError):
                mod._positive_int(invalid, "test")
        self.assertEqual(mod._positive_int("112", "test"), 112)

    def test_category_is_explicitly_heuristic(self):
        self.assertEqual(mod._category("索引标记自粘本-1"), "Sticky Notes & Page Flags")
        self.assertEqual(mod._category("A6内芯（空白）"), "Refills & Inserts")
        self.assertEqual(mod._category("未知品名"), "Other / Review")


if __name__ == "__main__":
    unittest.main(verbosity=2)
