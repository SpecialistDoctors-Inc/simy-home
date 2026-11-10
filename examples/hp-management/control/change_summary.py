"""Bounded descriptions from exact static files; source text is never executed."""
from difflib import SequenceMatcher
from html.parser import HTMLParser
from pathlib import PurePosixPath
import re


class VisibleText(HTMLParser):
    blocks = {'p', 'li', 'div', 'section', 'article', 'header', 'footer', 'td', 'th', 'tr',
              'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'br'}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rows, self.parts, self.ignored = [], [], []
        self.heading, self.in_heading = '', False

    def flush(self):
        text = re.sub(r'\s+', ' ', ''.join(self.parts)).strip()
        self.parts = []
        if text:
            if self.in_heading:
                self.heading = text
            self.rows.append((self.heading, text))

    def handle_starttag(self, tag, attrs):
        if tag in ('head', 'script', 'style', 'template'):
            self.ignored.append(tag)
        if self.ignored:
            return
        if tag in self.blocks:
            self.flush()
        if tag in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
            self.in_heading = True

    def handle_endtag(self, tag):
        if self.ignored:
            if tag == self.ignored[-1]:
                self.ignored.pop()
            return
        if tag in self.blocks:
            self.flush()
        if tag in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
            self.in_heading = False

    def handle_data(self, data):
        if not self.ignored:
            self.parts.append(data)


def excerpt(text):
    return text if len(text) <= 120 else text[:119] + '…'


def changed_excerpt(left, right):
    prefix = 0
    while prefix < min(len(left), len(right)) and left[prefix] == right[prefix]:
        prefix += 1
    suffix = 0
    while suffix < min(len(left), len(right)) - prefix and left[-suffix-1] == right[-suffix-1]:
        suffix += 1
    start = max(0, prefix - 24)
    end = min(len(left), len(left) - suffix + 24)
    return ('…' if start else '') + left[start:end] + ('…' if end < len(left) else '')


def text_rows(data, html):
    text = data.decode('utf-8', errors='replace')
    if not html:
        return [('', line.strip()) for line in text.splitlines() if line.strip()]
    parser = VisibleText()
    parser.feed(text)
    parser.flush()
    return parser.rows


def summarize_changes(before, after):
    items = []
    for path in sorted(set(before) | set(after)):
        if path == 'version.json' or before.get(path) == after.get(path):
            continue
        suffix = PurePosixPath(path).suffix.lower()
        title = 'ページ' if path == 'index.html' else PurePosixPath(path).name
        rows = []
        if suffix in ('.html', '.htm', '.txt') and max(len(before.get(path, b'')), len(after.get(path, b''))) <= 131072:
            old = text_rows(before.get(path, b''), suffix != '.txt')
            new = text_rows(after.get(path, b''), suffix != '.txt')
            opcodes = []
            if max(len(old), len(new)) <= 500:
                diff = SequenceMatcher(None, [row[1] for row in old], [row[1] for row in new], autojunk=False)
                opcodes = diff.get_opcodes()
            for kind, i, j, a, b in opcodes:
                if kind == 'equal':
                    continue
                left, right = ' '.join(row[1] for row in old[i:j]), ' '.join(row[1] for row in new[a:b])
                heading = (new[a][0] if a < b else old[i][0]) or title
                # An appended sentence should show the addition, not repeat its paragraph.
                if left and right.startswith(left):
                    right, left = right[len(left):].strip(), ''
                elif right and left.startswith(right):
                    left, right = left[len(right):].strip(), ''
                if not left and not right:
                    continue
                if left and right:
                    left, right = changed_excerpt(left, right), changed_excerpt(right, left)
                rows.append({'title': excerpt(heading), 'kind': 'added' if not left else 'removed' if not right else 'changed',
                             'before': excerpt(left), 'after': excerpt(right)})
        if not rows:
            action = '追加' if path not in before else '削除' if path not in after else '変更'
            category = ('デザイン' if suffix == '.css' else '画像' if suffix in ('.png', '.jpg', '.jpeg', '.webp', '.gif', '.svg')
                        else '動作' if suffix == '.js' else 'ページの構成・表示')
            rows = [{'title': title, 'kind': 'description', 'before': '', 'after': category + 'を' + action}]
        items.extend(rows)
    return {'items': items[:5], 'additional_count': max(0, len(items) - 5)}
