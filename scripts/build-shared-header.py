#!/usr/bin/env python3
"""Apply the common static header to every visitor page; --check detects drift."""
import argparse
from shared_header import SITE, apply, exclusion

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    stale, count = [], 0
    for file in sorted(SITE.rglob('*.html')):
        source = file.read_text()
        path = file.relative_to(SITE).as_posix()
        if exclusion(path, source):
            continue
        output = apply(source, path)
        count += 1
        if output != source:
            if args.check:
                stale.append(path)
            else:
                file.write_text(output)
    if stale:
        raise SystemExit('Stale shared headers: ' + ', '.join(stale))
    print(f'{count} shared headers ' + ('verified.' if args.check else 'generated.'))

if __name__ == '__main__':
    main()
