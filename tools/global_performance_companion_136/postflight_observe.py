"""Host-only read-only acceptance; emit aggregates, never configuration or logs.

This tool imports only reviewed helper definitions, not the release entrypoint.
It never starts a container or changes a file. Run after the separate controller
verify. The original public Worker inventory is supplied as a pinned JSON file.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import stat
import subprocess
import sys
import time

ROOT = Path('/opt/offersteady-global/releases/20261102-global-performance-companion-136-1')
INPUT_SHA = 'd9c7e0336533f1865374c8c9e0049e954029c9d39ee4edbb636aa66d592e7e08'
WORKER_INVENTORY_SHA = 'd13f52ff29ed8c4f1ce13f872cf07ccf81f8aa19861f0e19eca735b7c4b1c4b6'
WORKER_SETTINGS_SHA = '43bd096f3a8fbd94566d7fe1c5bb899b1a8e42bc076db3c718226599e64211cd'
PUBLIC_SCHEMA_BYTES = {
    'openapiBefore': 'e2f33fbe450150f71999e8a516dcb9918d4c6df153fff1b0c6f1375730a6eb11',
    'openapiAfter': 'ce7abd5ece94920ceb756de7284c142a51da489764e23c196cc88f0253144ca3',
}
PROJECT = 'offersteady-global'
TAIL = 4000


class ObservationError(RuntimeError):
    pass


def require(ok, reason):
    if not ok:
        raise ObservationError(reason)


def digest(value):
    return hashlib.sha256(value).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()


def read_json(path):
    return json.loads(path.read_bytes())


def run_readonly(args, *, timeout=60, **kwargs):
    # Deliberately do not call helper.run: failed command diagnostics can contain
    # private data and this observer must not create even a diagnostic file.
    require(args[:2] in (['docker', 'inspect'], ['docker', 'exec'], ['docker', 'logs'], ['docker', 'ps']),
            'observer_command_outside_readonly_scope')
    response = subprocess.run(args, capture_output=True, timeout=timeout, **kwargs)
    require(response.returncode == 0, 'readonly_observation_command_failed')
    return response


def load_helpers(root, plan):
    modules = []
    for filename, name in [('base_helpers.py', 'postflight_helpers'), ('ownership_primitives.py', 'postflight_ownership')]:
        path = root / filename
        require(digest(path.read_bytes()) == plan['supportFiles'][filename], 'observer_helper_drift')
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
        modules.append(module)
    helper, ownership = modules
    inspect = lambda name: json.loads(run_readonly(['docker', 'inspect', name], timeout=15).stdout)[0]
    for module in modules:
        for key, value in dict(ROOT=root, PROJECT=PROJECT, run=run_readonly, inspect=inspect,
                               require=require, digest=digest, canonical=canonical, H=helper,
                               BASES={s:(v['id'], v['image']) for s,v in plan['baselines'].items()},
                               environment=helper.environment,
                               expected_environment=lambda before, service, kind: helper.environment(before)).items():
            setattr(module, key, value)
    return helper, ownership


def checked_file(path, mode):
    metadata = path.lstat()
    require(stat.S_ISREG(metadata.st_mode) and metadata.st_uid == 0 and metadata.st_gid == 0
            and stat.S_IMODE(metadata.st_mode) == mode, 'release_file_permissions_changed')


def check_permissions(root, plan, prepared):
    public = {**plan['supportFiles'], 'input.json': INPUT_SHA,
              plan['globalManifest']['path']: plan['globalManifest']['sha256']}
    for key in ('openapiBefore', 'openapiAfter'):
        path = plan[key]['path']
        public[path] = PUBLIC_SCHEMA_BYTES[key]
    require(len(public) == 16, 'public_payload_file_count_changed')
    for name, checksum in public.items():
        path = root / name
        checked_file(path, 0o644)
        require(digest(path.read_bytes()) == checksum, 'public_payload_content_changed')
        for parent in path.relative_to(root).parents:
            require(not (root / parent).is_symlink(), 'release_parent_is_linked')
    private_files = set(prepared['privateFiles']) | {'prepared.json', 'progress.json', 'deployed.json'}
    for service in ('backend', 'web'):
        directory = root / service
        info = directory.lstat()
        require(stat.S_ISDIR(info.st_mode) and info.st_uid == info.st_gid == 0
                and stat.S_IMODE(info.st_mode) == 0o700, 'private_directory_permissions_changed')
        for path in directory.rglob('*'):
            require(path.is_file() and not path.is_symlink(), 'unexpected_private_entry')
            private_files.add(str(path.relative_to(root)))
    for name in private_files:
        checked_file(root / name, 0o600)
    return {'publicFilesRoot0644': len(public), 'privateFilesRoot0600': len(private_files),
            'privateDirectoriesRoot0700': 2, 'publicContentUnchanged': True}


def log_counts(raw):
    lines = raw.decode('utf-8', errors='replace').splitlines()
    return {'rows': len(lines), 'tailLimitReached': len(lines) >= TAIL,
            'errorLines': sum(bool(re.search(r'"(?:level|levelname)"\s*:\s*"(?:ERROR|CRITICAL)"|\b(?:ERROR|CRITICAL):|\[(?:error|crit|alert|emerg)\]', x)) for x in lines),
            'tracebacks': sum('Traceback (most recent call last)' in x for x in lines),
            'http5xx': sum(bool(re.search(r'"[A-Z]+ [^" ]+ HTTP/[0-9.]+"\s+5\d\d\b|"(?:status|status_code|statusCode)"\s*:\s*5\d\d\b', x)) for x in lines)}


def observe(root, worker_file, since_ms, *, now_ms=None):
    now_ms = int(time.time() * 1000) if now_ms is None else now_ms
    require(type(since_ms) is int and 0 <= now_ms - since_ms <= 3_600_000, 'observation_window_invalid')
    require(digest((root / 'input.json').read_bytes()) == INPUT_SHA, 'fixed_input_changed')
    plan, prepared, progress = (read_json(root / x) for x in ('input.json', 'prepared.json', 'progress.json'))
    require(read_json(root / 'deployed.json').get('deployed') is True
            and prepared['inputSha256'] == INPUT_SHA, 'release_not_deployed')
    helper, ownership = load_helpers(root, plan)
    names = set(run_readonly(['docker', 'ps', '-a', '--format', '{{.Names}}']).stdout.decode().splitlines())
    require(names == set(plan['nonTargets']) | {PROJECT+'-backend-1', PROJECT+'-web-1'}
            and len(names) == 8 and len(plan['nonTargets']) == 6
            and set(prepared['nonTargets']) == set(plan['nonTargets']), 'container_set_changed')
    for name, signature in plan['nonTargets'].items():
        require(signature == prepared['nonTargets'][name]
                and helper.container_signature(helper.inspect(name)) == signature, 'non_target_full_signature_changed')
    components = []
    for service in ('backend', 'web'):
        target, entry = prepared['targets'][service], progress[service]
        current = helper.inspect(PROJECT+'-'+service+'-1')
        require(entry['kind'] == 'new' and current['Id'] == entry['id']
                and current['Image'] == entry['image'] == plan['candidates'][service]['image']
                and ownership.ownership_signature(current) == entry['ownershipSignature'], 'target_candidate_ownership_changed')
        ownership.assert_context_owner(current, target, 'new')
        ownership.runtime_invariant(read_json(root / service / 'container-before.json'), current, target, 'new')
        require(current['State']['Running'] is True and current['RestartCount'] == 0, 'target_lifecycle_unhealthy')
        health = current['State'].get('Health', {}).get('Status')
        require(service != 'backend' or health == 'healthy', 'backend_unhealthy')
        components.append({'component': service, 'candidateOwned': True, 'running': True,
                           'health': health, 'restartCount': 0})
    backend_settings = ownership.settings('backend')
    require(backend_settings == read_json(root / 'backend/settings-before.private.json')
            and len(backend_settings) == 379 and digest(canonical(backend_settings)) == plan['baselines']['backend']['settingsSha256'],
            'backend_effective_settings_changed')
    require(digest(worker_file.read_bytes()) == WORKER_INVENTORY_SHA, 'worker_baseline_inventory_changed')
    worker_inventory = ownership.inventory('material-worker')
    require(len(worker_inventory) == 267 and worker_inventory == read_json(worker_file), 'worker_full267_inventory_changed')
    worker_settings = ownership.settings('material-worker')
    require(len(worker_settings) == 354 and digest(canonical(worker_settings)) == WORKER_SETTINGS_SHA,
            'worker_effective_settings_changed')
    permissions = check_permissions(root, plan, prepared)
    iso = lambda value: datetime.datetime.fromtimestamp(value / 1000, datetime.timezone.utc).isoformat()
    rows = []
    for service in ('backend', 'web', 'material-worker'):
        response = run_readonly(['docker', 'logs', '--timestamps', '--since', iso(since_ms), '--until', iso(now_ms),
                                 '--tail', str(TAIL), PROJECT+'-'+service+'-1'], timeout=20)
        separator = b'\n' if response.stdout and response.stderr and not response.stdout.endswith(b'\n') else b''
        rows.append({'component': service, **log_counts(response.stdout + separator + response.stderr)})
    return {'passed': True, 'readOnly': True, 'fromMs': since_ms, 'toMs': now_ms,
            'durationSeconds': round((now_ms-since_ms)/1000, 1), 'components': components,
            'allSixNonTargetsFullSignaturesUnchanged': True, 'backendSettingsFields': 379,
            'backendSettingsUnchanged': True, 'workerFullInventoryInputs': 267,
            'workerInventoryUnchanged': True, 'workerSettingsFields': 354,
            'workerSettingsSha256': WORKER_SETTINGS_SHA, 'workerSettingsUnchanged': True,
            'permissions': permissions, 'logCounts': rows, 'rawLogsExported': False,
            'configurationExported': False, 'userIdentifiersExported': False,
            'providerCalls': 0, 'databaseWrites': 0, 'lifecycleActions': 0}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--release-root', type=Path, default=ROOT)
    parser.add_argument('--worker-inventory', type=Path, required=True)
    parser.add_argument('--since-ms', type=int, required=True)
    args = parser.parse_args(argv)
    try:
        result = observe(args.release_root, args.worker_inventory, args.since_ms)
        print(json.dumps(result, separators=(',', ':')))
        return 0
    except Exception:
        # Do not print exception values, paths, commands, configuration or raw
        # logs even for a failed inspect/parser/helper call.
        print(json.dumps({'passed': False, 'reason': 'postflight_observation_failed',
                          'rawLogsExported': False, 'configurationExported': False}))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
