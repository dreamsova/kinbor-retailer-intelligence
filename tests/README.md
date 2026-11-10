# Offline tests

Run the complete suite from the repository root:

```bash
python3 -m unittest discover -v
```

The root `test_import.py` is intentionally kept in its original location and
unchanged. It is one of the 214 Phase 1 files protected by
[`docs/phase1_manifest.json`](../docs/phase1_manifest.json), alongside the catalog,
210 product images, importer and data dictionary. Root discovery runs that frozen
catalog suite together with the tests in this package.

Tests use synthetic transport and model responses. Passing tests establish code
behavior and evidence integrity; they do not establish live multimodal validation,
human recommendation quality or commercial conversion.
