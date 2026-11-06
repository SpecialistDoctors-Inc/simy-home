"""Content-specific sharing metadata, also applied by every page generator."""
import html
import json
import re
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

@lru_cache(maxsize=1)
def cards():
    return {c['page']: c for c in json.loads((ROOT / 'scripts/social-preview-pages.json').read_text())}

def apply(source, path):
    page = Path(path).resolve().relative_to(ROOT / 'site').as_posix()
    card = cards().get(page)
    if not card:
        return source
    source = re.sub(r'\n?<!-- Shared social preview -->\n.*?<!-- /Shared social preview -->', '', source, flags=re.S)
    values = {
        'og:image': 'https://simy.one' + card['image'],
        'og:image:width': '1200', 'og:image:height': '630',
        'og:image:type': 'image/png', 'og:image:alt': card['alt'],
        'twitter:card': 'summary_large_image',
        'twitter:image': 'https://simy.one' + card['image'],
        'twitter:image:alt': card['alt'],
    }
    # Reinsert one canonical set, avoiding stale duplicate dimensions or alts.
    def keep(match):
        key = re.search(r'(?:property|name)=["\']([^"\']+)', match[0], re.I)
        return '' if key and key[1] in values else match[0]
    source = re.sub(r'<meta\b[^>]*>', keep, source, flags=re.I)
    # Articles that used the previous sharing asset should expose the same cover
    # to structured-data consumers. Do not change unrelated article photographs.
    def schema_cover(match):
        return re.sub(r'https://simy.one/(?:ogp[^"\s]+|assets/(?:fp|engineer)-experience/social-[^"\s]+)',
                      'https://simy.one' + card['image'], match[0])
    source = re.sub(r'<script[^>]+type="application/ld\+json"[^>]*>.*?</script>', schema_cover, source, flags=re.S)
    source = re.sub(r'[ \t]+(?=\n)', '', source)
    tags = '\n'.join(f'<meta {"property" if k.startswith("og:") else "name"}="{k}" content="{html.escape(v, quote=True)}">' for k, v in values.items())
    # Marker makes repeated application byte-stable without altering other head spacing.
    block = '<!-- Shared social preview -->\n' + tags + '\n<!-- /Shared social preview -->'
    # Keep metadata near the start of large inline-CSS documents, after charset.
    charset = re.search(r'<meta\b[^>]*charset=[^>]*>', source, re.I)
    if charset:
        return source[:charset.end()] + '\n' + block + source[charset.end():]
    return source.replace('<head>', '<head>\n' + block, 1)
