"""Embed the small entry policy before the body, without a blocking request."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def strip(source):
    return re.sub(r'\n?<!-- SIMY locale navigation -->[\s\S]*?<!-- /SIMY locale navigation -->\n?', '', source)

def apply(source):
    source = strip(source)
    script = (ROOT / 'site/locale-navigation.js').read_text().rstrip()
    if '</script' in script.lower():
        raise ValueError('Locale source cannot contain a closing script tag')
    block = '<!-- SIMY locale navigation -->\n<script data-simy-locale-navigation>\n' + script + '\n</script>\n<!-- /SIMY locale navigation -->\n'
    return re.sub(r'\s*</head>', lambda _: '\n' + block + '</head>', source, count=1)
