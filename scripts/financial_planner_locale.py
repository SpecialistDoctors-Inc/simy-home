"""Locale copy and public URL conventions for the FP experience."""
import json
from pathlib import Path

LOCALES = ('ja', 'en', 'es', 'fr', 'hi', 'zh-Hans')
COPY = json.loads(Path(__file__).with_name('financial-planner-locales.json').read_text())


def route(lang):
    if lang not in LOCALES:
        raise ValueError(f'Unsupported FP locale: {lang}')
    prefix = '' if lang == 'ja' else lang.lower() + '/'
    return f'/for/{prefix}financial-planners/'


def translator(lang):
    if lang not in LOCALES:
        raise ValueError(f'Unsupported FP locale: {lang}')

    def translate(ja, en):
        if lang == 'ja':
            return ja
        if lang == 'en':
            return en
        # Missing copy fails generation rather than silently publishing English.
        return COPY[lang][en]

    return translate
