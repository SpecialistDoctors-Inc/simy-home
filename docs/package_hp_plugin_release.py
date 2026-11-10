"""Assemble a customer release kit from a verified native build and current guides."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import shutil
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def build(native_build, output, release_date):
    native_build, output = native_build.resolve(), output.resolve()
    proof = json.loads((native_build/'build-receipt.json').read_text())
    source = native_build/'package/plugins/hp-local-editor'
    plugin = json.loads((source/'plugin.json').read_text())
    version = plugin['version']
    require(proof['platform'] == 'darwin-arm64', 'wrong native platform')
    require(digest(source/'bin/hp') == proof['binary_sha256'], 'binary digest mismatch')
    for name, checksum in proof['source_sha256'].items():
        require(digest(source/name) == checksum, 'source digest mismatch: '+name)
    archive = Path(proof['archive'])
    require(digest(archive) == proof['archive_sha256'], 'archive digest mismatch')
    with zipfile.ZipFile(archive) as bundle:
        names = bundle.namelist()
        required = {'INSTALL.md', '.agents/plugins/marketplace.json', 'plugins/hp-local-editor/bin/hp',
                    'plugins/hp-local-editor/skills/hp-local-editor/references/customer-guide.md'}
        require(required <= set(names), 'missing package entry')
        require(hashlib.sha256(bundle.read('INSTALL.md')).hexdigest() == proof['installer_guide_sha256'], 'installer guide digest mismatch')
        require(bundle.getinfo('plugins/hp-local-editor/bin/hp').external_attr >> 16 & 0o111, 'runtime is not executable')
        require(not any('/.hp/' in name or '/output/' in name or
            name.endswith(('.pem', '.sqlite3', '.env', '/auth.json')) for name in names), 'unexpected private file')
        for name in names:
            if name.endswith(('.md', '.py', '.json', '.js', '.html')):
                content = bundle.read(name)
                require(b'BEGIN PRIVATE KEY' not in content and b'/Users/' not in content, 'private data in '+name)
        require(bundle.read('plugins/hp-local-editor/skills/hp-local-editor/references/customer-guide.md') == (ROOT/'docs/hp-single-plugin-customer-guide.md').read_bytes(), 'bundled guide differs from release guide')
    guide_proof = json.loads((output/'guide-build.json').read_text())
    require(guide_proof['version'] == version and guide_proof['date'] == release_date, 'guide version/date mismatch')
    require(guide_proof['pdf_sha256'] == digest(output/'HPローカル編集_はじめ方.pdf'), 'PDF digest mismatch')
    require(guide_proof['customer_guide_sha256'] == digest(ROOT/'docs/hp-single-plugin-customer-guide.md'), 'PDF guide source is stale')
    require(guide_proof['generator_sha256'] == digest(ROOT/'docs/build_hp_plugin_guide.py'), 'PDF generator is stale')
    output.mkdir(parents=True, exist_ok=True)
    plugin_name = f'hp-local-editor-{version}-mac-apple-silicon.zip'
    shutil.copyfile(archive, output/plugin_name)
    shutil.copyfile(ROOT/'docs/hp-single-plugin-customer-guide.md', output/'HPローカル編集_はじめ方.md')
    shutil.copyfile(ROOT/'docs/hp-local-editor-operator-guide.md', output/'HPローカル編集_運用ガイド.md')
    checksum = digest(output/plugin_name)
    prompt = (
        'このHPプラグインを導入して、編集を始めたいです。\n'
        '導入済みなら、作業中の変更を引き継いで更新してください。\n'
    )
    (output/'導入依頼.txt').write_text(prompt)
    names = [plugin_name, 'HPローカル編集_はじめ方.pdf', 'HPローカル編集_はじめ方.md', '導入依頼.txt']
    hashes = {name: digest(output/name) for name in names}
    manifest = {'version': version, 'built_for': 'macOS Apple Silicon', 'date': release_date,
        'files': hashes.copy(), 'native_binary_sha256': proof['binary_sha256'],
        'contents': ['native runtime', 'HP MCP connection', 'local editing skill', 'customer guide'],
        'service_origin': 'https://hp-control.simy.one', 'publication': 'local distribution candidate'}
    (output/'release-manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n')
    kit = output/f'HPローカル編集-{version}-配布セット.zip'
    with zipfile.ZipFile(kit, 'w', zipfile.ZIP_DEFLATED) as bundle:
        for name in names:
            bundle.write(output/name, name)
    with zipfile.ZipFile(kit) as bundle:
        require(set(bundle.namelist()) == set(names), 'unexpected kit entry')
        for name,value in hashes.items():
            require(hashlib.sha256(bundle.read(name)).hexdigest() == value, 'kit digest mismatch: '+name)
    result = {'kit': str(kit), 'bytes': kit.stat().st_size, 'plugin_sha256': checksum,
              'kit_sha256': digest(kit), 'files': names}
    (output/'package-receipt.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--native-build', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--date', type=datetime.date.fromisoformat, required=True)
    args = parser.parse_args()
    build(args.native_build, args.output, args.date.isoformat())
