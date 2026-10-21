const test = require('node:test');
const assert = require('node:assert/strict');
const {execFileSync} = require('node:child_process');
const path = require('node:path');
const root = path.resolve(__dirname, '..');

test('manga release rejects missing scenes and reused artwork', () => {
  const output = execFileSync('python3', ['-c', `
import sys, tempfile
from pathlib import Path
sys.path.insert(0, 'scripts')
from pharmaceutical_manga_art import validate_art, render_artwork
with tempfile.TemporaryDirectory() as temporary:
    directory = Path(temporary)
    assert render_artwork('unchanged release', directory) == 'unchanged release'
    try:
        validate_art(directory, required=True)
        raise AssertionError('Missing artwork was accepted')
    except ValueError as error:
        assert 'Missing manga artwork' in str(error)
    reference = Path('site/assets/engineer-manga/release-crew-ja.webp').read_bytes()
    for index in range(1, 9):
        (directory / f'scene-{index:02}.webp').write_bytes(reference)
    try:
        validate_art(directory, required=True)
        raise AssertionError('Repeated artwork was accepted')
    except ValueError as error:
        assert 'duplicate artwork' in str(error)
    (directory / 'scene-08.webp').unlink()
    try:
        validate_art(directory, required=True)
        raise AssertionError('Partial delivery was accepted')
    except ValueError as error:
        assert 'scene-08.webp' in str(error)
print('Asset completeness and duplication guards verified')
`], {cwd:root, encoding:'utf8'});
  assert.match(output, /guards verified/);
});

test('full-scene layout retains all six localized dialogues and removes portrait reuse', () => {
  const output = execFileSync('python3', ['-c', `
import sys, tempfile, shutil, re, runpy
from unittest.mock import patch
from pathlib import Path
sys.path.insert(0, 'scripts')
from pharmaceutical_manga_art import render_artwork
# Existing real WebP files exercise layout integration only; they are never
# delivered as the new pharma artwork or copied into deployed scene paths.
references = sorted(Path('site/assets/engineer-manga').glob('*.webp'))
references += [Path('site/assets/pharmaceutical-companies/lead.webp'), Path('site/assets/pharmaceutical-companies/simy.webp')]
assert len(references) >= 8
with tempfile.TemporaryDirectory() as temporary:
    directory = Path(temporary)
    for index, reference in enumerate(references[:8], 1):
        shutil.copyfile(reference, directory / f'scene-{index:02}.webp')
    # Render the maintained localized template before art injection; released
    # pages already contain artwork and must not be injected a second time.
    with patch('pharmaceutical_manga_art.render_artwork', side_effect=lambda source, **kwargs: source):
        builder = runpy.run_path('scripts/build-pharmaceutical-pages.py')
    for language in ['ja', 'en', 'es', 'fr', 'hi', 'zh-Hans']:
        source = builder['render'](language)
        result = render_artwork(source, directory, required=True)
        assert result.count('class="manga-art"') == 8
        assert result.count('class="dialogue"') == 8
        assert re.findall(r'<p class="bubble">.*?</p>', result) == re.findall(r'<p class="bubble">.*?</p>', source)
        assert re.findall(r'<h3 class="number">.*?</h3>', result) == re.findall(r'<h3 class="number">.*?</h3>', source)
        for old in ['lead.webp', 'simy.webp', 'colleague.webp']:
            assert '/assets/pharmaceutical-companies/' + old not in result
        for index in range(1, 9):
            assert f'/manga-v2/scene-{index:02}.webp' in result
print('Six-language artwork layout verified with reference-only fixtures')
`], {cwd:root, encoding:'utf8'});
  assert.match(output, /Six-language artwork layout verified/);
});
