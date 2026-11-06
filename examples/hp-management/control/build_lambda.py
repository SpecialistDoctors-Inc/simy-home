#!/usr/bin/env python3
"""Build a deterministic Python 3.12 x86_64 Lambda ZIP from reviewed inputs.

Requires uv + Node/npm. Dependencies are hash-locked Linux binary wheels; no
source builds or developer environment packages enter the artifact. Optional
--verify-runtime imports the staged package in the official Lambda container.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import re
from pathlib import Path
import shutil
import stat
import subprocess
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parent
LAMBDA_IMAGE = 'public.ecr.aws/lambda/python:3.12@sha256:0fe974382dcb297e80e7feb8c7620d7e8ece5b42b4d01a5a9ffe939c654bf8b0'
MODULES = ('hp_control.py', 'store.py', 'service.py', 'identity.py', 'cloud_auth.py',
           'mcp_adapter.py', 'bundles.py', 'executor.py', 'cloud_providers.py',
           'github_app.py', 'github_workflow.py', 'github_events.py', 'browser_validation.py', 'publisher.py', 'reporting.py', 'cloud_reporting.py')
LEGACY_MODULES = ('google_provider.py','gmail_provider.py','provider_errors.py','ledger.py')


def run(command, cwd, log):
    process = subprocess.Popen(command, cwd=cwd)
    # Record the exact owned child identity at launch. This builder never sends
    # signals or stops containers/processes, even if a build step fails.
    identity = subprocess.run(['ps', '-p', str(process.pid), '-o', 'pid=,ppid=,lstart=,command='],
                              capture_output=True, text=True, check=False).stdout.strip()
    with log.open('a') as stream:
        stream.write(json.dumps({'pid':process.pid, 'command':command, 'identity':identity}) + '\n')
    code = process.wait()
    if code:
        raise RuntimeError('build_step_failed: ' + command[0])


def build(output, verify_runtime=False):
    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    log = output.with_suffix('.processes.jsonl')
    identity=subprocess.run(['ps','-p',str(os.getpid()),'-o','pid=,ppid=,lstart=,command='],capture_output=True,text=True,check=False).stdout.strip()
    with log.open('a') as stream:
        stream.write(json.dumps({'pid':os.getpid(),'ppid':os.getppid(),'command':'build_lambda.py','identity':identity})+'\n')
    lock = ROOT / 'requirements.lock'
    if not lock.is_file():
        raise RuntimeError('runtime_lock_missing')
    locked_bytes = lock.read_bytes()
    requirement_bytes = (ROOT/'requirements.txt').read_bytes()
    locked_pins = dict(re.findall(r'^([A-Za-z0-9_.-]+)==(\S+)', locked_bytes.decode(), re.MULTILINE))
    for line in requirement_bytes.decode().splitlines():
        if not line.strip() or line.lstrip().startswith('#'):
            continue
        match = re.fullmatch(r'([A-Za-z0-9_.-]+)(?:\[[A-Za-z0-9_,.-]+\])?==([^ ]+)', line.strip())
        if not match or locked_pins.get(match[1].lower().replace('_','-')) != match[2]:
            raise RuntimeError('runtime_lock_outdated')
    run(['npm', 'ci', '--ignore-scripts'], ROOT/'ui', log)
    run(['npm', 'run', 'typecheck'], ROOT/'ui', log)
    run(['npm', 'test'], ROOT/'ui', log)
    run(['npm', 'run', 'build'], ROOT/'ui', log)
    html = ROOT/'ui'/'dist'/'publish.html'
    if not html.is_file() or b'/* APP_BUNDLE */' in html.read_bytes():
        raise RuntimeError('official_ui_bundle_missing')
    with tempfile.TemporaryDirectory(prefix='hp-control-lambda-') as directory:
        stage = Path(directory)/'package'
        stage.mkdir()
        run(['uv','pip','install','--python','3.12','--target',str(stage),'--python-version','3.12',
             '--python-platform','x86_64-manylinux2014','--only-binary',':all:',
             '--require-hashes','--no-deps','-r',str(lock)], ROOT, log)
        for module in MODULES:
            source = ROOT/module
            if not source.is_file() or source.is_symlink():
                raise RuntimeError('runtime_module_missing: ' + module)
            shutil.copyfile(source, stage/module)
        for module in LEGACY_MODULES:
            source = ROOT.parent/'runner'/module
            if not source.is_file() or source.is_symlink():
                raise RuntimeError('legacy_provider_missing: '+module)
            shutil.copyfile(source, stage/module)
        (stage/'ui'/'dist').mkdir(parents=True)
        shutil.copyfile(html,stage/'ui'/'dist'/'publish.html')
        native = []
        files = {}
        for path in stage.rglob('*'):
            if not path.is_file():
                continue
            relative = path.relative_to(stage).as_posix()
            if path.is_symlink():
                raise RuntimeError('package_symlink_rejected')
            if any(part in ('bin','__pycache__') for part in path.relative_to(stage).parts) or path.suffix == '.pyc':
                continue
            data = path.read_bytes()
            if path.suffix == '.so':
                # ELF64 little-endian EM_X86_64. A macOS or ARM dependency must
                # never silently ship in this Lambda artifact.
                if data[:6] != b'\x7fELF\x02\x01' or int.from_bytes(data[18:20],'little') != 62:
                    raise RuntimeError('non_linux_x86_64_extension')
                native.append(relative)
            files[relative] = data
        if not native:
            raise RuntimeError('crypto_native_extension_missing')
        if verify_runtime:
            run(['docker','run','--rm','--network','none','--platform','linux/amd64',
                 '--mount','type=bind,source='+str(stage)+',target=/var/task,readonly',
                 '--entrypoint','python',LAMBDA_IMAGE,
                 '-c','import hp_control, browser_validation, cloud_reporting, google_provider, gmail_provider, ledger, boto3, jwt, google.auth, requests, cryptography; from cryptography.hazmat.primitives.asymmetric import rsa; '
                      'assert all(m.__file__.startswith("/var/task/") for m in (hp_control,cloud_reporting,boto3,jwt,google.auth,requests,cryptography)); '
                      'assert callable(hp_control.handler); assert callable(hp_control.consume_commands); '
                      'assert callable(hp_control.dispatch_pending); rsa.generate_private_key(public_exponent=65537,key_size=2048); '
                      'print("Lambda Python3.12 x86_64 imports and RSA verified")'], ROOT, log)
        for module in MODULES:
            if (ROOT/module).read_bytes() != files[module]:
                raise RuntimeError('runtime_source_changed_during_build: '+module)
        for module in LEGACY_MODULES:
            if (ROOT.parent/'runner'/module).read_bytes() != files[module]:
                raise RuntimeError('legacy_provider_changed_during_build: '+module)
        if (ROOT/'requirements.txt').read_bytes() != requirement_bytes:
            raise RuntimeError('runtime_requirements_changed_during_build')
        if lock.read_bytes() != locked_bytes:
            raise RuntimeError('dependency_lock_changed_during_build')
        if html.read_bytes() != files['ui/dist/publish.html']:
            raise RuntimeError('official_ui_changed_during_build')
        with zipfile.ZipFile(output,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
            for name,data in sorted(files.items()):
                info=zipfile.ZipInfo(name,(1980,1,1,0,0,0))
                info.create_system=3
                info.external_attr=(stat.S_IFREG|0o644)<<16
                info.compress_type=zipfile.ZIP_DEFLATED
                archive.writestr(info,data)
    digest=hashlib.sha256(output.read_bytes()).hexdigest()
    metadata={'schema_version':1,'runtime':'python3.12','architecture':'x86_64',
              'sha256':digest,'bytes':output.stat().st_size,'files':len(files),
              'requirements_sha256':hashlib.sha256(locked_bytes).hexdigest(),
              'requirements_input_sha256':hashlib.sha256(requirement_bytes).hexdigest(),
              'source_sha256':{**{name:hashlib.sha256(files[name]).hexdigest() for name in MODULES},
                  **{'runner/'+name:hashlib.sha256(files[name]).hexdigest() for name in LEGACY_MODULES},
                  'ui/dist/publish.html':hashlib.sha256(files['ui/dist/publish.html']).hexdigest()},
              'runtime_image':LAMBDA_IMAGE, 'runtime_container_verified':verify_runtime,'native_extensions':native}
    output.with_suffix('.manifest.json').write_text(json.dumps(metadata,indent=2)+'\n')
    print(json.dumps(metadata))
    return metadata


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'output'/'hp-control-lambda.zip')
    parser.add_argument('--verify-runtime',action='store_true')
    arguments=parser.parse_args()
    build(arguments.output,arguments.verify_runtime)
