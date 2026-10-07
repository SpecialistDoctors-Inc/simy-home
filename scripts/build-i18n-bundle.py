#!/usr/bin/env python3
"""Build the shared translation bundle from site/lang/*.json; --check is read-only."""
import argparse
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--check', action='store_true')
args = parser.parse_args()
translations = {p.stem: json.loads(p.read_text()) for p in sorted((root / 'site/lang').glob('*.json'))}
content = 'window.SIMY_I18N_BUNDLE = ' + json.dumps(translations, ensure_ascii=False, indent=2) + ';\n'
target = root / 'site/lang/i18n-bundle.js'
if args.check:
    if target.read_text() != content:
        raise SystemExit('Translation bundle is stale; run python3 scripts/build-i18n-bundle.py')
else:
    target.write_text(content)
