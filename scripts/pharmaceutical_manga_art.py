"""Use eight distinct full-scene manga illustrations once the complete set exists.

Generation credentials never belong in this module. The imagegen CLI creates the
artwork; this module validates the delivery and adds localized text from the page.
"""
import hashlib
import html
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART_DIRECTORY = ROOT / 'site/assets/pharmaceutical-companies/manga-v2'
PUBLIC_DIRECTORY = '/assets/pharmaceutical-companies/manga-v2'


def validate_art(directory=ART_DIRECTORY, required=False):
    paths = [Path(directory) / f'scene-{index:02}.webp' for index in range(1, 9)]
    present = [path for path in paths if path.exists()]
    if not present and not required:
        return None
    missing = [path.name for path in paths if not path.exists()]
    if missing:
        raise ValueError('Missing manga artwork: ' + ', '.join(missing))
    seen = {}
    for path in paths:
        data = path.read_bytes()
        if data[:4] != b'RIFF' or data[8:12] != b'WEBP':
            raise ValueError(f'{path.name}: expected a WebP illustration')
        digest = hashlib.sha256(data).hexdigest()
        if digest in seen:
            raise ValueError(f'{path.name}: duplicate artwork of {seen[digest]}')
        seen[digest] = path.name
    return paths


def render_artwork(source, directory=ART_DIRECTORY, required=False):
    paths = validate_art(directory, required)
    if paths is None:
        # Keep the existing release intact while artwork is being produced.
        # Release verification must use --require-manga-art for the new comic.
        return source
    pattern = r'(<article class="panel">)(.*?)(</article>)'
    panels = list(re.finditer(pattern, source, re.S))
    if len(panels) != 8:
        raise ValueError(f'Expected 8 localized manga panels, got {len(panels)}')
    index = 0
    def panel(match):
        nonlocal index
        index += 1
        content = match[2]
        heading = re.search(r'<h3 class="number">(.*?)</h3>', content, re.S)
        if not heading:
            raise ValueError(f'Scene {index}: missing localized heading')
        label = html.unescape(re.sub(r'<[^>]*>', '', heading[1]))
        art = (f'<figure class="manga-art"><img '
               f'src="{PUBLIC_DIRECTORY}/scene-{index:02}.webp" '
               f'width="1536" height="1024" loading="lazy" decoding="async" '
               f'alt="{html.escape(label, quote=True)}"></figure>')
        # Replace the repeated portrait, while retaining every localized line.
        content, removed = re.subn(r'(<div class="dialogue">)\s*<img\b[^>]*>', r'\1', content, count=1)
        if removed != 1:
            raise ValueError(f'Scene {index}: portrait structure changed')
        content = content.replace(heading[0], heading[0] + art, 1)
        return match[1] + content + match[3]
    return re.sub(pattern, panel, source, flags=re.S)
