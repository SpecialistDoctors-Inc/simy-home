"""Rewrite captured HTML/CSS references to their validated static import paths."""
import hashlib
import re
import mimetypes
from html import escape
from html.parser import HTMLParser
from pathlib import PurePosixPath
from urllib.parse import quote, urldefrag, urljoin, urlsplit

from bundles import validate_path, SUFFIXES


class SourceConnectionRequired(ValueError):
    pass


def normalize(records, raw_files, host):
    paths, source_paths, candidates, first_html = {}, {}, {}, True
    for record in records:
        url = urlsplit(record['url'])
        if url.scheme != 'https' or url.hostname not in (host, 'www.' + host, host.removeprefix('www.')):
            raise SourceConnectionRequired('import_source_mismatch')
        original = url.path.lstrip('/') or 'index.html'
        if original.endswith('/'):
            original += 'index.html'
        mime = record.get('content_type', '').split(';', 1)[0].strip().lower()
        required = {'text/html': '.html', 'text/css': '.css', 'text/javascript': '.js',
                    'application/javascript': '.js'}.get(mime)
        suffix = PurePosixPath(original).suffix
        if required is None and suffix.lower() not in SUFFIXES:
            guessed = mimetypes.guess_extension(mime)
            required = guessed if guessed in SUFFIXES else None
        if required and suffix.lower() != required:
            original = original[:-len(suffix)] + required if suffix else original + required
            suffix = required
        if mime == 'text/html' and first_html:
            original, suffix, first_html = 'index.html', '.html', False
        elif url.query:
            token = '__' + hashlib.sha256(url.query.encode()).hexdigest()[:12]
            original = original[:-len(suffix)] + token + suffix if suffix else original + token
        validate_path(original)
        if original in candidates:
            raise SourceConnectionRequired('import_path_collision')
        paths[record['url']] = original
        source_paths[record['path']] = original
        candidates[original] = raw_files[record['path'][5:]]
    if first_html:
        raise SourceConnectionRequired('homepage_html_required')

    def reference(value, base):
        if not value or value.startswith(('#', 'data:', 'tel:', 'mailto:', 'javascript:')):
            return value
        absolute, fragment = urldefrag(urljoin(base, value))
        return '/' + quote(paths[absolute], safe='/') + ('#' + fragment if fragment else '') if absolute in paths else value

    def css(text, base):
        pattern = r'url\(\s*([\"\']?)([^)\"\']+)\1\s*\)'
        def replace(match):
            value = reference(match[2].strip(), base)
            return 'url("' + value.replace('"', '%22') + '")' if value != match[2].strip() else match[0]
        text = re.sub(pattern, replace, text)
        return re.sub(r'(@import\s+)([\"\'])([^\"\']+)\2',
            lambda m: m[1] + m[2] + reference(m[3], base) + m[2], text, flags=re.I)

    class HTML(HTMLParser):
        def __init__(self, base):
            super().__init__(convert_charrefs=False)
            self.base, self.output, self.in_style = base, [], False
        def tag(self, tag, attrs, closed=False):
            values = dict(attrs)
            if tag == 'script' and values.get('type', '').lower() == 'module':
                raise SourceConnectionRequired('website_application_connection_required')
            if tag == 'style': self.in_style = True
            if tag == 'form':
                target = urlsplit(urljoin(self.base, values.get('action') or self.base))
                if target.hostname in (host, 'www.' + host, host.removeprefix('www.')):
                    raise SourceConnectionRequired('website_form_connection_required')
            if tag == 'base' and values.get('href'):
                self.base = urljoin(self.base, values['href'])
            rendered = []
            for name, value in attrs:
                if value is not None:
                    if tag == 'meta' and name == 'charset': value = 'utf-8'
                    elif tag == 'meta' and name == 'content' and values.get('http-equiv', '').lower() == 'content-type':
                        value = 'text/html; charset=utf-8'
                    elif tag == 'base' and name == 'href' and urlsplit(self.base).hostname in (host, 'www.' + host, host.removeprefix('www.')):
                        value = '/'
                    elif name in ('src', 'href', 'poster'): value = reference(value, self.base)
                    elif name == 'style': value = css(value, self.base)
                    elif name == 'srcset' and 'data:' not in value:
                        value = ', '.join(' '.join([reference(v.split()[0], self.base), *v.split()[1:]]) for v in value.split(',') if v.split())
                rendered.append(name if value is None else name + '="' + escape(value, quote=True) + '"')
            self.output.append('<' + tag + (' ' + ' '.join(rendered) if rendered else '') + (' />' if closed else '>'))
        def handle_starttag(self, tag, attrs): self.tag(tag, attrs)
        def handle_startendtag(self, tag, attrs): self.tag(tag, attrs, True)
        def handle_endtag(self, tag):
            if tag == 'style': self.in_style = False
            self.output.append('</' + tag + '>')
        def handle_data(self, data): self.output.append(css(data, self.base) if self.in_style else data)
        def handle_entityref(self, name): self.output.append('&' + name + ';')
        def handle_charref(self, name): self.output.append('&#' + name + ';')
        def handle_comment(self, data): self.output.append('<!--' + data + '-->')
        def handle_decl(self, decl): self.output.append('<!' + decl + '>')
        def handle_pi(self, data): self.output.append('<?' + data + '>')

    for record in records:
        path = source_paths[record['path']]
        mime = record.get('content_type', '').lower()
        if 'text/html' not in mime and 'text/css' not in mime:
            continue
        data = candidates[path]
        declared = re.search(r'charset\s*=\s*[\"\']?([a-zA-Z0-9_-]+)', mime)
        meta = re.search(rb'charset\s*=\s*[\"\']?([a-zA-Z0-9_-]+)', data[:2048])
        encoding = declared[1] if declared else meta[1].decode() if meta else 'utf-8'
        text = data.decode(encoding)
        if 'text/html' in mime:
            parser = HTML(record['url']); parser.feed(text); parser.close(); text = ''.join(parser.output)
        else:
            text = css(text, record['url'])
            text = re.sub(r'(?i)^@charset\s+[\"\'][^\"\']+[\"\'];', '@charset "utf-8";', text)
        candidates[path] = text.encode('utf-8')
    return candidates
