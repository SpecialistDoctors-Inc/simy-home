#!/usr/bin/env python3
"""Capture SIMY's native fixture UI; never attaches to a user's running host.

Requires a SIMY_DEV native app built from the release tag, and that release's
installed Node runtime and CLI entry. See docs/cli-home-refresh/verification.md.
"""
import argparse
import hashlib
import json
import shutil
import struct
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCENES = {
    'overview': [],
    'goal': [{'ui': 'goal', 'value': 'g2'}, {'ui': 'charter'}],
    'sqm': [{'ui': 'mode', 'value': 'sqm'}, {'ui': 'sqmRun', 'value': 's2'}],
    'connection': [{'ui': 'settings', 'value': 'connection'}],
    'usage': [{'ui': 'settings', 'value': 'usage'}],
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--app', type=Path, required=True, help='SIMY_DEV executable')
    parser.add_argument('--node', type=Path, required=True)
    parser.add_argument('--entry', type=Path, required=True, help='release src/index.js')
    parser.add_argument('--locale', choices=['ja', 'en'], required=True)
    parser.add_argument('--source-commit', required=True, help='verified release tag commit')
    args = parser.parse_args()
    args.entry = args.entry.resolve()
    args.node = args.node.resolve()
    installed = json.loads((args.entry.parent.parent / 'package.json').read_text())
    target = ROOT / 'site/assets/cli-ui' / args.locale
    target.mkdir(parents=True, exist_ok=True)
    manifest = []
    with tempfile.TemporaryDirectory(prefix='simy-cli-ui-') as directory:
        scratch = Path(directory)
        for name, steps in SCENES.items():
            script = scratch / f'{name}.json'
            script.write_text(json.dumps({'app': [
                {'ui': 'settings', 'value': 'general'},
                {'ui': 'pref', 'value': f'lang={args.locale}'},
                {'until': 'settings.lang', 'equals': args.locale},
                {'ui': 'mode', 'value': 'loop'},
            ] + steps}))
            subprocess.run([
                str(args.app), '--snapshot', str(scratch), '--fixture', 'ok',
                '--appearance', 'light', '--screen', 'window', '--size', '1180x800',
                '--script', str(script), '--', str(args.node),
                str(ROOT / 'scripts/cli-ui-fixture.mjs'), str(args.entry), args.locale,
            ], check=True, timeout=60, stdout=subprocess.DEVNULL)
            matches = list(scratch.glob(f'window-*-ok-{name}-light.png'))
            if len(matches) != 1:
                raise RuntimeError(f'{name}: expected one native snapshot, found {len(matches)}')
            image = matches[0]
            data = image.read_bytes()
            if data[:8] != b'\x89PNG\r\n\x1a\n':
                raise RuntimeError(f'{name}: native output is not PNG')
            width, height = struct.unpack('>II', data[16:24])
            shutil.copyfile(image, target / f'{name}.png')
            manifest.append({'file': f'{name}.png', 'width': width, 'height': height,
                             'sha256': hashlib.sha256(data).hexdigest(), 'sampleData': True})
            print(f'{name}: {width}x{height}, {len(data)} bytes')
    (target / 'manifest.json').write_text(json.dumps({
        'version': installed['version'], 'sourceCommit': args.source_commit, 'locale': args.locale,
        'capturedAt': '2026-11-17', 'renderer': f'native SwiftUI, SIMY_DEV snapshot, light, {args.locale}',
        'data': f'official fixture ok with {args.locale} sample content and actual release version; no customer data or production outcomes', 'images': manifest,
    }, ensure_ascii=False, indent=2) + '\n')


if __name__ == '__main__':
    main()
