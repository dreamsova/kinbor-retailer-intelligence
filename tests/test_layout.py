"""Migration checks for byte-preserved data and historical path references."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from kinbor import pipeline
from kinbor.paths import CATALOG, ROOT, RETAILERS, phase1_path


class PreservedLayout(unittest.TestCase):
    def test_original_manifest_still_validates_all_214_relocated_files(self):
        manifest = json.loads((ROOT / 'docs/phase1_manifest.json').read_text())['phase1_files']
        self.assertEqual(len(manifest), 214)
        for original, digest in manifest.items():
            with self.subTest(original=original):
                self.assertEqual(hashlib.sha256(phase1_path(original).read_bytes()).hexdigest(), digest)
        self.assertEqual(phase1_path('products.csv'), CATALOG / 'products.csv')
        self.assertFalse((ROOT / 'phase2').exists())

    def test_frozen_capture_fields_resolve_to_relocated_pilot_without_rewriting_rows(self):
        evidence = pipeline.read('evidence.csv')
        current = [row for row in evidence if row['evidence_scope'] == 'current_pilot']
        self.assertTrue(current)
        for row in current:
            legacy = row['source_capture']
            self.assertTrue(legacy.startswith('live/'))
            resolved = pipeline.saved_artifact(legacy)
            self.assertTrue(resolved.is_file())
            self.assertTrue(resolved.is_relative_to(RETAILERS))
            self.assertEqual(pipeline.saved_artifact(pipeline.artifact_link(legacy)), resolved)

    def test_historical_path_resolution_rejects_traversal_and_symlink_escape(self):
        for unsafe in ('../outside.json', '/tmp/outside.json', 'live/../../outside.json'):
            with self.subTest(path=unsafe), self.assertRaises(ValueError):
                pipeline.saved_artifact(unsafe)
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as outside:
            base = Path(directory)
            (base / 'escape').symlink_to(outside, target_is_directory=True)
            with patch.object(pipeline, 'DATA', base), self.assertRaises(ValueError):
                pipeline.saved_artifact('escape/capture.json')

    def test_manifest_path_resolution_rejects_escaping_legacy_names(self):
        for unsafe in ('../products.csv', '/tmp/products.csv', 'images/../../key'):
            with self.subTest(path=unsafe), self.assertRaises(ValueError):
                phase1_path(unsafe)
