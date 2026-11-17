"""Publish only reviewed HP navigation objects; never synchronize or delete."""
import hashlib
import json
import mimetypes
import os
import re
import subprocess
import tempfile
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
from xml.sax.saxutils import escape
import xml.etree.ElementTree as ET
from hp_industry_release import ROOT, URL, LEGACY_URL, check, source_path
from hp_management_industries import published_industries


class Landing(HTMLParser):
    def __init__(self):
        super().__init__()
        self.canonicals = []
        self.ids = set()

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'link' and attrs.get('rel') == 'canonical':
            self.canonicals.append(attrs.get('href'))
        if attrs.get('id'):
            self.ids.add(attrs['id'])


def preflight(opener=urlopen):
    """Read published landing pages only, with no form or registration actions."""
    checked = []
    for industry in published_industries():
        url = 'https://simy.one' + industry['url']
        with opener(Request(url, headers={'User-Agent': 'SIMY-HP-release-preflight/1.0'}), timeout=30) as response:
            final = urlsplit(response.geturl())
            if response.status != 200 or (final.scheme, final.netloc) != ('https', 'simy.one'):
                raise ValueError('Published industry HTTP preflight failed: ' + url)
            page = Landing()
            body = response.read(5 * 1024 * 1024 + 1)
            if len(body) > 5 * 1024 * 1024:
                raise ValueError('Industry landing exceeds preflight size limit')
            page.feed(body.decode('utf-8'))
            if page.canonicals != [url] or not {'diagnosis', 'pricing'} <= page.ids:
                raise ValueError('Published industry canonical/anchors preflight failed: ' + url)
        checked.append(url)
    return checked


def aws(args, output=False):
    command = ['aws', *args]
    if output:
        return json.loads(subprocess.check_output(command))
    subprocess.run(command, check=True, stdout=subprocess.DEVNULL)


def extend_sitemap(original, head):
    root = ET.fromstring(original)
    if root.tag != '{http://www.sitemaps.org/schemas/sitemap/0.9}urlset':
        raise ValueError('Unexpected live sitemap root')
    urls = [node.findtext('{*}loc') for node in root.findall('{*}url')]
    if urls.count(URL) > 1:
        raise ValueError('Duplicate live hub sitemap URL')
    if URL in urls:
        return original, False
    if not head.get('ETag'):
        raise ValueError('Live sitemap ETag is required')
    if urls.count(LEGACY_URL) > 1:
        raise ValueError('Duplicate legacy hub sitemap URL')
    if LEGACY_URL in urls:
        # Migrate only the owned hub loc text. Keep its lastmod/priority and
        # every other byte of the live document intact, including namespaces.
        loc = re.compile(rb'(<(?:[A-Za-z_][\w.-]*:)?loc\b[^>]*>\s*)'
                         + re.escape(LEGACY_URL.encode('utf-8'))
                         + rb'(\s*</(?:[A-Za-z_][\w.-]*:)?loc\s*>)')
        if len(list(loc.finditer(original))) != 1:
            raise ValueError('Cannot uniquely identify the legacy hub loc bytes')
        updated = loc.sub(lambda match: match[1] + URL.encode('utf-8') + match[2], original, count=1)
        expected = [URL if value == LEGACY_URL else value for value in urls]
        if [node.findtext('{*}loc') for node in ET.fromstring(updated).findall('{*}url')] != expected:
            raise ValueError('Sitemap canonical migration validation failed')
        return updated, True
    closing = list(re.finditer(rb'</(?:[A-Za-z_][\w.-]*:)?urlset\s*>', original))
    if len(closing) != 1:
        raise ValueError('Unexpected sitemap closing element')
    addition = ('<url xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><loc>' + escape(URL) + '</loc></url>\n').encode('utf-8')
    offset = closing[0].start()
    updated = original[:offset] + addition + original[offset:]
    if [node.findtext('{*}loc') for node in ET.fromstring(updated).findall('{*}url')] != urls + [URL]:
        raise ValueError('Sitemap append validation failed')
    return updated, True


def publish(root=ROOT, opener=urlopen, runner=aws):
    manifest, digest = check(root, os.environ.get('EXPECTED_RELEASE_SHA256'))
    verified = preflight(opener)
    bucket = os.environ['SITE_S3_BUCKET']
    distribution = os.environ['SITE_CF_DISTRIBUTION_ID']
    if not re.fullmatch('[a-z0-9][a-z0-9.-]+', bucket) or not re.fullmatch('[A-Z0-9]+', distribution):
        raise ValueError('Invalid AWS publication target')
    written = []
    with tempfile.TemporaryDirectory(prefix='hp-industry-sitemap-') as temporary:
        sitemap = Path(temporary) / 'sitemap.xml'
        head = runner(['s3api', 'get-object', '--bucket', bucket, '--key', 'sitemap.xml', str(sitemap), '--output', 'json'], output=True)
        updated, sitemap_updated = extend_sitemap(sitemap.read_bytes(), head)
        if sitemap_updated:
            skeleton = runner(['s3api', 'put-object', '--generate-cli-skeleton', 'input'], output=True)
            if 'IfMatch' not in skeleton:
                raise ValueError('AWS CLI conditional sitemap writes are required')
            sitemap.write_bytes(updated)
        for item in manifest['objects']:
            key = item['key']
            source = source_path(root / 'site', item['source'])
            # Verify each source again immediately before its upload.
            blob = source.read_bytes()
            if len(blob) != item['bytes'] or hashlib.sha256(blob).hexdigest() != item['sha256']:
                raise ValueError('Source changed during publication: ' + item['source'])
            content_type = mimetypes.guess_type(item['source'])[0] or 'application/octet-stream'
            if item['source'].endswith(('.html', '.css', '.json')):
                content_type += '; charset=utf-8'
            runner(['s3api', 'put-object', '--bucket', bucket, '--key', key, '--body', str(source),
                    '--content-type', content_type, '--cache-control', 'public, max-age=300'])
            written.append(key)
        if sitemap_updated:
            command = ['s3api', 'put-object', '--bucket', bucket, '--key', 'sitemap.xml', '--body', str(sitemap), '--if-match', head['ETag']]
            for field, flag in [('ContentType', '--content-type'), ('CacheControl', '--cache-control'),
                                ('ContentDisposition', '--content-disposition'), ('ContentEncoding', '--content-encoding'),
                                ('ContentLanguage', '--content-language'), ('Expires', '--expires'),
                                ('WebsiteRedirectLocation', '--website-redirect-location')]:
                if field in head:
                    command += [flag, head[field]]
            if 'Metadata' in head:
                command += ['--metadata', json.dumps(head['Metadata'])]
            try:
                runner(command)
            except subprocess.CalledProcessError as error:
                raise RuntimeError('Conditional sitemap publication failed; concurrent sitemap was not overwritten. Industry objects were uploaded; invalidation was not requested.') from error
            written.append('sitemap.xml')
    # Exact keys include the canonical directory alias; no wildcard invalidations.
    paths = sorted(set(manifest['invalidation_paths']) | ({'/sitemap.xml'} if sitemap_updated else set()))
    result = runner(['cloudfront', 'create-invalidation', '--distribution-id', distribution, '--paths', *paths, '--output', 'json'], output=True)
    invalidation = result['Invalidation']['Id']
    runner(['cloudfront', 'wait', 'invalidation-completed', '--distribution-id', distribution, '--id', invalidation])
    receipt = {'url': URL, 'commit': os.environ.get('GITHUB_SHA'), 'manifest_sha256': digest,
               'objects': len(written), 'object_keys': written, 'sitemap_updated': sitemap_updated,
               'preflight_urls': verified, 'invalidation_paths': paths, 'invalidation_id': invalidation,
               'status': 'uploaded_and_invalidated'}
    (root / 'hp-industry-navigation-deployment.json').write_text(json.dumps(receipt, indent=2) + '\n')
    return receipt


if __name__ == '__main__':
    print(json.dumps(publish()))
