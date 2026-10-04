#!/usr/bin/env python3
"""Put the guide's practical answer before the SIMY use-case narrative.

Preserves the authored sections and links. Rebuilds both tables of contents from
their existing localized labels and the new section order. No keyword stuffing.
"""
import argparse
import json
import re
from html import escape, unescape
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
READ_GUIDE = {'ja': '使い方・選び方を読む', 'en': 'Read the practical guide',
              'es': 'Leer la guía práctica', 'fr': 'Lire le guide pratique',
              'hi': 'इस्तेमाल की गाइड पढ़ें', 'zh-Hans': '阅读使用指南'}


class Sections(HTMLParser):
    def __init__(self, source):
        super().__init__(convert_charrefs=False)
        self.source = source
        self.offsets = [0]
        for line in source.splitlines(keepends=True):
            self.offsets.append(self.offsets[-1] + len(line))
        self.depth = 0
        self.start = None
        self.parts = []
        self.feed(source)

    def position(self):
        line, col = self.getpos()
        return self.offsets[line - 1] + col

    def handle_starttag(self, tag, attrs):
        if tag != 'section':
            return
        a = dict(attrs)
        if self.start is not None:
            self.depth += 1
        elif 'sec' in a.get('class', '').split():
            self.start = (a['id'], self.position())
            self.depth = 1

    def handle_endtag(self, tag):
        if tag == 'section' and self.start is not None:
            self.depth -= 1
            if self.depth == 0:
                ident, start = self.start
                self.parts.append((ident, start, self.position() + len('</section>')))
                self.start = None


def organize(source, topic):
    title = unescape(re.search(r'<title>(.*?)</title>', source)[1]).removesuffix(' | SIMY')
    source = re.sub(r'(<h1[^>]*>).*?(</h1>)', lambda m: m[1] + escape(title) + m[2], source, count=1, flags=re.S)
    ld = re.search(r'<script type="application/ld\+json">([\s\S]*?)</script>', source)
    article = next(n for n in json.loads(ld[1])['@graph'] if n['@type'] == 'Article')
    revised = ld[1].replace('"headline": ' + json.dumps(article['headline'], ensure_ascii=False),
                            '"headline": ' + json.dumps(title, ensure_ascii=False))
    source = source[:ld.start(1)] + revised + source[ld.end(1):]
    sections = Sections(source).parts
    order = [i for i, _, _ in sections]
    # Comparison and self-hosting guides already have a different search intent.
    priority = ['basics', 'engines', 'hardware', 'build', 'checklist', 'mistakes'] if topic == 'qwen-local' else (['compare', 'choose', 'reference'] if topic == 'china-llm' else ['reference'])
    assert set(priority) <= set(order), (topic, order)
    wanted = priority + [i for i in order if i not in priority]
    lang = re.search(r'<html lang="([^"]+)"', source)[1]
    source_link = re.compile(r'(<a class="btn btn-ghost" href=")[^"]+("[^>]*>).*?(</a>)', re.S)
    # Compute section positions before editing this earlier hero link; apply it
    # after moving the blocks so offsets continue to refer to the original text.
    blocks = {i: source[a:b] for i, a, b in sections}
    for number, ident in enumerate(wanted, 1):
        blocks[ident] = re.sub(r'(<span class="sec-label">)\d+', lambda m: m[1] + f'{number:02}', blocks[ident], count=1)
    # Keep the practical introduction visible without interaction.
    first = wanted[0]
    blocks[first] = re.sub(r'<details class="fold"(?: open)?>', '<details class="fold" open>', blocks[first], count=1)
    for (_, a, b), ident in reversed(list(zip(sections, wanted))):
        source = source[:a] + blocks[ident] + source[b:]
    def toc(match):
        nav = match[0]
        labels = {m[1]: m[0] for m in re.finditer(r'<li><a href="#([^"]+)"[^>]*>.*?</a></li>', nav, re.S)}
        assert set(labels) == set(wanted), (topic, set(labels) ^ set(wanted))
        items = []
        for number, ident in enumerate(wanted, 1):
            items.append(re.sub(r'<span>\d+</span>', f'<span>{number:02}</span>', labels[ident]))
        return re.sub(r'(<ol>).*?(</ol>)', lambda m: m[1] + '\n        ' + '\n        '.join(items) + '\n      ' + m[2], nav, flags=re.S)
    source = re.sub(r'<nav class="toc".*?</nav>', toc, source, flags=re.S)
    source = re.sub(r'<details class="toc-mobile">.*?</details>', toc, source, flags=re.S)
    # Old numerical comments are not content and become misleading after moving.
    source = re.sub(r'\s*<!-- \d{2} -->', '', source)
    source = source_link.sub(lambda m: m[1] + '#' + wanted[0] + m[2]
                             + READ_GUIDE[lang] + ' <span class="arrow" aria-hidden="true">↓</span>' + m[3], source, count=1)
    return source


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    stale = []
    for path in sorted((ROOT / 'site/guides').rglob('*.html')):
        if path.stem == 'index':
            continue
        source = path.read_text()
        output = organize(source, path.stem)
        if source != output:
            stale.append(str(path.relative_to(ROOT)))
            if not args.check:
                path.write_text(output)
    print(f'{len(stale)} guides ' + ('need regeneration' if args.check else 'updated'))
    return bool(stale) if args.check else 0


if __name__ == '__main__':
    raise SystemExit(main())
