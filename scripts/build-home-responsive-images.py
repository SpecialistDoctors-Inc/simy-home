#!/usr/bin/env python3
"""Build smaller home manga variants with Pillow; keep the full-size originals."""
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'site/assets/home-manga-preview'

def main():
    before = after = 0
    for locale in ('ja', 'en', 'es', 'fr', 'hi', 'zh-Hans'):
        for scene in ('hero', 'product'):
            stem = ('hero' if scene == 'hero' else 'product-ja-v2') if locale == 'ja' else f'{scene}-{locale}'
            source = ASSETS / f'{stem}.webp'
            with Image.open(source) as image:
                for width in (640, 1024):
                    target = ASSETS / f'{stem}-{width}.webp'
                    height = round(image.height * width / image.width)
                    image.resize((width, height), Image.Resampling.LANCZOS).save(target, 'WEBP', quality=88, method=6)
                    before += source.stat().st_size
                    after += target.stat().st_size
    print(f'Built 24 variants: {after:,} bytes, compared with {before:,} original bytes at the same request count.')

if __name__ == '__main__':
    main()
