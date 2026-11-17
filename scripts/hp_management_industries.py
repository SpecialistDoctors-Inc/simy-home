"""Validated, shared catalog for HP management navigation and generation."""
import json
import re
from functools import lru_cache
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / 'scripts/hp-management-industries.json'
SITE = ROOT / 'site'
HUB_URL = '/hp-management.html'
HUB_SOURCE = 'hp-management/index.html'


def validate_catalog(data, site=SITE):
    if not isinstance(data, dict):
        raise ValueError('Catalog must be an object')
    if data.get('version') != 1 or not isinstance(data.get('industries'), list):
        raise ValueError('Expected catalog version 1 and industries array')
    seen = {key: set() for key in ('id', 'url', 'source')}
    records = []
    for item in data['industries']:
        required = ('id', 'label', 'nav_label', 'url', 'source', 'description', 'checkout_config', 'status', 'featured')
        if not isinstance(item, dict):
            raise ValueError('Industry must be an object')
        if any(key not in item for key in required):
            raise ValueError('Industry is missing required fields')
        if not isinstance(item['id'], str) or not re.fullmatch(r'[a-z][a-z0-9]*(?:-[a-z0-9]+)*', item['id']):
            raise ValueError('Industry id must be a stable lowercase slug')
        if item['status'] not in ('published', 'draft') or type(item['featured']) is not bool:
            raise ValueError('Invalid industry status or featured flag')
        for key in ('label', 'nav_label', 'description'):
            if not isinstance(item[key], str) or not item[key].strip():
                raise ValueError(f'Invalid industry {key}')
        for key in ('url', 'source', 'checkout_config'):
            value = item[key]
            if not isinstance(value, str) or any(c in value for c in ('?', '#', '%', '\\')):
                raise ValueError(f'Invalid industry {key}')
            relative = value[1:] if key == 'url' else value
            path = PurePosixPath(relative)
            if (not relative.startswith('hp-management/') or '..' in path.parts
                    or '.' in value.split('/') or path.is_absolute() or str(path) != relative):
                raise ValueError(f'Industry {key} must stay under hp-management/')
            if key == 'url' and (not value.startswith('/') or not value.endswith('.html') or value == '/hp-management/index.html'):
                raise ValueError('Industry URL must be its own HP HTML URL, not the hub')
            if key == 'source' and (not value.endswith('.html') or value == 'hp-management/index.html'):
                raise ValueError('Industry source must be its own HTML file')
            if key == 'checkout_config' and not value.endswith('.json'):
                raise ValueError('Checkout config must be JSON')
            if item['status'] == 'published' and not (site / relative).is_file() and key != 'url':
                raise ValueError(f'Published industry {key} does not exist: {value}')
            if key != 'url' and not (site / relative).resolve().is_relative_to(site.resolve()):
                raise ValueError('Industry path escapes site')
        for key in seen:
            if item[key] in seen[key]:
                raise ValueError(f'Duplicate industry {key}: {item[key]}')
            seen[key].add(item[key])
        records.append(dict(item))
    return records


@lru_cache(maxsize=1)
def _catalog():
    return validate_catalog(json.loads(CATALOG.read_text()))


def published_industries():
    return [dict(item) for item in _catalog() if item['status'] == 'published']


def featured_industries():
    return [item for item in published_industries() if item['featured']][:2]


def published_aliases():
    return {HUB_URL: HUB_SOURCE, **{item['url']: item['source'] for item in published_industries()
            if item['url'].lstrip('/') != item['source']}}
