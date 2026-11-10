# Offline tests

Run the complete suite from the repository root:

```bash
python3 -m unittest discover -v
```

Application tests import the `kinbor` package and use synthetic transport and model responses. The frozen catalog suite lives at `catalog/test_import.py`, beside `catalog/import.py`, `products.csv` and the 210 images it checks. Root discovery includes that suite through the `catalog` package. Its bytes retain the original preservation hash.

```bash
python3 -m unittest -v catalog.test_import
python3 scripts/verify_repository.py
```

All public tests and saved-output checks use the standard library. Pillow is only needed for actual image export from authorized private workbooks. Passing tests establish code behavior and evidence integrity; they do not establish live multimodal validation, human recommendation quality or commercial conversion. [Preservation and baseline guide](../docs/BASELINES.md).
