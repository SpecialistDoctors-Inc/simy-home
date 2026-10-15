#!/usr/bin/env python3
"""Generate the file-preview translation bundles from the locale dictionaries."""
import argparse
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--check', action='store_true')
args = parser.parse_args()

for directory, target, global_name in [
    ('site/lang', 'site/lang/i18n-bundle.js', 'SIMY_I18N_BUNDLE'),
    ('site/lang/home-dom', 'site/lang/home-dom-bundle.js', 'SIMY_HOME_DOM_BUNDLE'),
]:
    translations = {p.stem: json.loads(p.read_text()) for p in sorted((root / directory).glob('*.json'))}
    content = 'window.' + global_name + ' = ' + json.dumps(translations, ensure_ascii=False, indent=2) + ';\n'
    path = root / target
    if args.check:
        if path.read_text() != content:
            raise SystemExit('Stale translation bundle: ' + target + '; run python3 scripts/build-i18n-bundle.py')
    else:
        path.write_text(content)
