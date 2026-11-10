"""Repository locations and resolution of immutable historical path references."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / 'catalog'
EXAMPLES = ROOT / 'examples'
RETAILERS = EXAMPLES / 'retailers'
BASELINES = EXAMPLES / 'baselines'
EVALUATION = EXAMPLES / 'evaluation'
NOTES = EXAMPLES / 'sku_visual_notes.json'


def phase1_path(legacy_name):
    """Resolve original manifest keys without changing any of its 214 hashes."""
    name = Path(legacy_name)
    if name.is_absolute() or '..' in name.parts:
        raise ValueError('Phase 1 manifest paths must be relative repository files')
    if legacy_name in ('products.csv', 'import.py', 'test_import.py') or name.parts[:1] == ('images',):
        return CATALOG / name
    return ROOT / name
