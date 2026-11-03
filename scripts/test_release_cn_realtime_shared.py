"""Synthetic controller contracts; all Docker/network/production calls mocked."""
from contextlib import ExitStack
from copy import deepcopy
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

import pytest


_spec = importlib.util.spec_from_file_location('cn_realtime_shared_release_under_test', Path(__file__).with_name('release_cn_realtime_shared.py'))
R = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = R
_spec.loader.exec_module(R)
REPO = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def no_unmocked_process_or_network():
    R._idle_authorization = None
    with patch('subprocess.run', side_effect=AssertionError('unmocked process forbidden')), \
         patch('socket.create_connection', side_effect=AssertionError('network forbidden')):
        yield
    R._idle_authorization = None


def container(container_id=None, image=None):
    cid = container_id or R.BASES['backend'][0]
    return {'Id': cid, 'Image': image or R.BASES['backend'][1], 'RestartCount': 0,
            'Config': {'Image': image or R.BASES['backend'][1], 'Env': ['A=synthetic'], 'Labels': {}, 'Hostname': cid[:12], 'Entrypoint': [], 'Cmd': ['uvicorn', 'app.main:app', '--host', '0.0.0.0', '--port', '8000']},
            'HostConfig': {'NetworkMode': 'compose_default'}, 'Mounts': [],
            'NetworkSettings': {'Networks': {'compose_default': {'IPAddress': '192.0.2.2', 'Aliases': ['backend', cid[:12]]}}},
            'State': {'Running': True, 'StartedAt': '2026-10-31T16:51:34.293214151Z', 'Pid': 42,
                      'Status': 'running', 'Restarting': False, 'Dead': False, 'Paused': False,
                      'Health': {'Status': 'healthy'}}}


def scope_plan():
    live = R.read_json(REPO / 'docs/releases/cn-device-status-20261103.1/backend-runtime-manifest.json')
    image = deepcopy(live)
    settings = R.digest(b'synthetic-unchanged-settings')
    return {'baselines': {'backend': {'id': R.BASES['backend'][0], 'image': R.BASES['backend'][1],
                'startedAt': container()['State']['StartedAt'], 'inventory': live, 'imageInventory': image, 'settingsSha256': settings}},
            'candidates': {'backend': {'image': 'sha256:' + 'a' * 64, 'inventory': live | R.APPROVED_BACKEND_SHA256, 'settingsSha256': settings},
                'backendRollback': {'image': R.ROLLBACK_IMAGE, 'inventory': live, 'settingsSha256': settings}}}


def frozen_plan(root):
    plan = scope_plan()
    plan['supportFiles'] = {}
    for name in R.support_paths():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        data = (REPO / 'scripts' / name).read_bytes()
        path.write_bytes(data)
        plan['supportFiles'][name] = R.digest(data)
    probe = b'print("synthetic probe, never executed")\n'
    result = json.dumps({'passed': True, 'image': plan['candidates']['backend']['image']}).encode()
    (root / 'candidate-probe.py').write_bytes(probe)
    (root / 'candidate-probe-result.json').write_bytes(result)
    schema = R.read_json(REPO / 'releases/cn-20261101.1/openapi.json')
    plan.update(releaseId=R.RELEASE, financialAnchorMs=R.FINANCIAL_ANCHOR_MS,
        openapiBefore={'paths': sorted(schema['paths']), 'schemaSha256': R.digest(R.canonical(schema))},
        nginxInputs={'/etc/nginx/nginx.conf': R.digest(b'synthetic-nginx'), '/etc/nginx/conf.d/default.conf': R.digest(b'synthetic-vhost')},
        nonTargets={'compose-web-1': {}, **{f'synthetic-non-target-{n}': {} for n in range(6)}},
        webInventory=R.read_json(REPO / 'releases/cn-20261101.1/web-static-manifest.json'),
        runtimeBefore={'python': '3.13.15', 'distributions': {f'synthetic-dist-{n}': '1.0' for n in range(44)}},
        orphanAnswerContext=R.P.expected_orphan_context(plan['baselines']['backend']), ancillaryInputs=deepcopy(R.ANCILLARY_INPUTS),
        candidateProbe={'scriptSha256': R.digest(probe), 'resultSha256': R.digest(result)})
    return plan


class PlanTests(unittest.TestCase):
    def tearDown(self):
        R.bind_primitives()

    def check(self, root, plan):
        (root / 'input.json').write_text(json.dumps(plan))
        with patch.object(R, 'ROOT', root):
            return R.check_plan()

    def test_complete_frozen_plan_accepts_list_or_complete_dict_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plan = frozen_plan(root)
            self.assertEqual(self.check(root, plan), plan)
            plan['openapiBefore']['paths'] = R.read_json(REPO / 'releases/cn-20261101.1/openapi.json')['paths']
            self.assertEqual(self.check(root, plan), plan)

    def test_only_live233_plus_reviewed_twelve_files_and_fixed_baseline_rollback(self):
        plan = scope_plan()
        R.check_candidate_scope(plan)
        self.assertEqual(len(plan['baselines']['backend']['inventory']), 233)
        self.assertEqual(len(plan['candidates']['backend']['inventory']), 237)
        self.assertEqual(len(R.APPROVED_BACKEND_SHA256), 12)
        self.assertEqual(R.expected_inventory(plan, 'backend', 'rollback')[R.MANIFEST_PATH], R.MANIFEST_SHA256)

    def test_self_consistent_changed_baseline_is_rejected(self):
        for source in ('inventory', 'imageInventory'):
            plan = scope_plan()
            plan['baselines']['backend'][source]['apps/backend/app/main.py'] = R.digest(b'foreign-source')
            with self.subTest(source=source), self.assertRaisesRegex(R.GuardError, 'baseline_source_manifest_changed'):
                R.check_candidate_scope(plan)

    def test_non_target_source_or_missing_input_is_rejected(self):
        for name in ('apps/backend/app/modules/screenshot_answer.py', 'apps/backend/app/desktop_release_manifest.json',
                     'apps/backend/app/core/config.py', 'apps/backend/pyproject.toml'):
            plan = scope_plan()
            plan['candidates']['backend']['inventory'][name] = R.digest(b'foreign-change')
            with self.subTest(path=name), self.assertRaisesRegex(R.GuardError, 'unapproved_backend_input_changed'):
                R.check_candidate_scope(plan)
        for mutation in ('add', 'remove'):
            plan = scope_plan()
            if mutation == 'add':
                plan['candidates']['backend']['inventory']['apps/backend/app/unapproved.py'] = R.digest(b'added')
            else:
                del plan['candidates']['backend']['inventory'][sorted(R.ADDED_PATHS)[0]]
            with self.subTest(mutation=mutation), self.assertRaisesRegex(R.GuardError, 'backend_input_set_changed'):
                R.check_candidate_scope(plan)

    def test_every_reviewed_source_is_hard_pinned(self):
        for name in R.APPROVED_BACKEND_SHA256:
            plan = scope_plan()
            plan['candidates']['backend']['inventory'][name] = R.digest(b'unreviewed')
            with self.subTest(path=name), self.assertRaisesRegex(R.GuardError, 'unreviewed_realtime_shared_source'):
                R.check_candidate_scope(plan)

    def test_rollback_cannot_revert_download_manifest_or_use_naked_base(self):
        for mutation in ('manifest', 'image', 'extra'):
            plan = scope_plan()
            if mutation == 'manifest':
                plan['candidates']['backendRollback']['inventory'] = dict(plan['baselines']['backend']['inventory'], **{R.MANIFEST_PATH: R.digest(b'old-manifest')})
            elif mutation == 'image':
                plan['candidates']['backendRollback']['image'] = 'sha256:' + 'b' * 64
            else:
                plan['candidates']['backendRollback']['inventory'] = dict(plan['baselines']['backend']['inventory'], extra=R.digest(b'extra'))
            with self.subTest(mutation=mutation), self.assertRaisesRegex(R.GuardError, 'rollback_hot_manifest_not_preserved'):
                R.check_candidate_scope(plan)

    def test_targets_and_settings_cannot_expand(self):
        for service in ('web', 'material-worker', 'global-backend'):
            plan = scope_plan()
            plan['candidates'][service] = deepcopy(plan['candidates']['backend'])
            with self.subTest(service=service), self.assertRaisesRegex(R.GuardError, 'candidate_components_changed'):
                R.check_candidate_scope(plan)
        for key in ('backend', 'backendRollback'):
            plan = scope_plan()
            plan['candidates'][key]['settingsSha256'] = R.digest(b'changed-settings')
            with self.subTest(key=key), self.assertRaisesRegex(R.GuardError, 'candidate_manifest_invalid'):
                R.check_candidate_scope(plan)

    def test_all_344_settings_preserved_and_pool_remains_false(self):
        before = {f'synthetic-{n}': n for n in range(341)} | {'product_edition': 'cn', 'environment': 'production', 'cn_hot_database_pool_enabled': False}
        for kind in ('baseline', 'new', 'rollback'):
            self.assertEqual(R.expected_settings(before, kind), before)
        for changed in (before | {'cn_hot_database_pool_enabled': True}, before | {'product_edition': 'global'}, before | {'extra': True}):
            with self.assertRaisesRegex(R.GuardError, 'settings_contract_changed'):
                R.expected_settings(changed, 'new')

    def test_support_probe_and_financial_anchor_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plan = frozen_plan(root)
            for key in (True, 0, R.FINANCIAL_ANCHOR_MS + 1):
                with self.subTest(anchor=key), self.assertRaisesRegex(R.GuardError, 'financial_anchor_invalid'):
                    self.check(root, plan | {'financialAnchorMs': key})
            for name, reason in (('release_cn_mock.py', 'release_controller_drift'),
                                 ('candidate-probe.py', 'candidate_probe_drift'), ('candidate-probe-result.json', 'candidate_probe_drift')):
                original = (root / name).read_bytes()
                (root / name).write_bytes(b'changed')
                with self.subTest(path=name), self.assertRaisesRegex(R.GuardError, reason):
                    self.check(root, plan)
                (root / name).write_bytes(original)

    def test_schema_nontarget_dependency_and_web_contracts_are_fixed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            original = frozen_plan(root)
            for target, key, value, reason in (
                ('openapiBefore', 'paths', [], 'schema_contract_changed'),
                ('runtimeBefore', 'python', '3.14.0', 'runtime_dependency_contract_changed'),
                ('runtimeBefore', 'distributions', {}, 'runtime_dependency_contract_changed'),
            ):
                plan = deepcopy(original)
                plan[target][key] = value
                with self.subTest(field=key), self.assertRaisesRegex(R.GuardError, reason):
                    self.check(root, plan)
            plan = deepcopy(original)
            del plan['nonTargets']['compose-web-1']
            with self.assertRaisesRegex(R.GuardError, 'non_target_scope_changed'):
                self.check(root, plan)
            plan = deepcopy(original)
            plan['webInventory']['index.html'] = 'invalid'
            with self.assertRaisesRegex(R.GuardError, 'web_inventory_invalid'):
                self.check(root, plan)


class GateTests(unittest.TestCase):
    def tearDown(self):
        R.bind_primitives()

    def test_same_seven_readonly_gates_and_fixed_financial_anchor_are_reused(self):
        self.assertEqual(R.GATES, R.M.GATES)
        self.assertEqual(len(R.GATES), 7)
        self.assertEqual(R.FINANCIAL_ANCHOR_MS, 1792600214792)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'backend').mkdir()
            before = container()
            (root / 'backend/container-before.json').write_text(json.dumps(before))
            context = R.P.expected_orphan_context({'startedAt': before['State']['StartedAt']})
            with patch.object(R, 'ROOT', root):
                R.bind_primitives()
                args = R.P.gate_command({'orphanAnswerContext': context})
            self.assertIn('OFFERSTEADY_RELEASE_ORIGINAL_BACKEND_STARTED_AT_MS=1792600214792', args)
            self.assertIn(R.BASES['backend'][1], args)
            self.assertIn('--read-only', args)
            self.assertIn('--env-file', args)
            self.assertNotIn('--allow-existing-preparation-page', args)

    def test_protected_unknown_and_unreadable_gates_stop(self):
        raw = {'atMs': 1, 'sampleAgeMs': 5, 'liveInterviews': 0, 'recentPreparing': 0, 'activeInterviews': 0,
               'activeWebSessions': 0, 'activeAudioStreams': 0}
        for counts, code, reason in ((raw | {'activeInterviews': 1}, 75, 'protected_user_work_cutover_deferred'),
                                     (raw | {'sampleAgeMs': 90000}, 75, 'protected_work_gate_unavailable')):
            response = subprocess.CompletedProcess([], code, json.dumps(counts).encode(), b'')
            with patch.object(R.P, 'gate_command', return_value=['synthetic-readonly']), patch.object(R.P, 'GATES', (R.GATES[0],)), \
                 patch.object(R.P.subprocess, 'run', return_value=response), patch.object(R.P, 'save'), \
                 patch.object(R, 'verify_single_writer'), \
                 patch.object(R.M, 'bind_primitives'), patch.object(R, 'bind_primitives'), \
                 self.assertRaisesRegex(R.GuardError, reason):
                R.idle_gates({})

    def test_tcp_gates_accept_owned_candidate_but_busy_or_unknown_never_cutover(self):
        current = container('a' * 64, 'sha256:' + 'b' * 64)
        progress = {'backend': {'id': current['Id'], 'image': current['Image'], 'kind': 'new'}}
        for count, namespace, reason in ((0, 'synthetic-ns', None), (1, 'synthetic-ns', 'protected_user_work_cutover_deferred'),
                                         (0, 'wrong-ns', 'protected_tcp_gate_unavailable')):
            value = {'passed': True, 'atMs': int(time.time() * 1000), 'establishedPort8000': count, 'tablesRead': 2,
                     'scannedRows': 4, 'scope': 'container_tcp8000_established_only', 'networkNamespaceSha256': namespace}
            response = subprocess.CompletedProcess([], 0, json.dumps(value).encode(), b'')
            with patch.object(R.M, 'inspect', return_value=current), patch.object(R.M, 'read_json', return_value=container()), \
                 patch.object(R.H, 'running_process_identity', return_value=('same',)), patch.object(R.H, 'host_network_namespace', return_value='synthetic-ns'), \
                 patch.object(R.M.subprocess, 'run', return_value=response), patch.object(R.M, 'save'):
                if reason:
                    with self.assertRaisesRegex(R.GuardError, reason):
                        R.tcp_gate({}, progress)
                else:
                    R.tcp_gate({}, progress)


class LifecycleTests(unittest.TestCase):
    def tearDown(self):
        R.bind_primitives()

    def deployment(self, root, *, progress=None):
        stack = ExitStack()
        stack.enter_context(patch.object(R, 'ROOT', root))
        stack.enter_context(patch.object(R.M, 'ROOT', root))
        stack.enter_context(patch.object(R, 'check_plan', return_value=scope_plan()))
        stack.enter_context(patch.object(R, 'load_state', return_value=({'targets': {'backend': {'newImage': 'synthetic-image'}}}, progress or {})))
        mocks = {name: stack.enter_context(patch.object(R, name)) for name in ('verify_runtime', 'idle_gates', 'tcp_gate', 'public_checks', 'save', 'emit', 'check_files')}
        return stack, mocks

    def test_preflight_never_switches_and_active_work_defers(self):
        with tempfile.TemporaryDirectory() as directory:
            stack, mocks = self.deployment(Path(directory))
            with stack, patch.object(R, 'switch') as switch:
                R.deploy(preflight=True)
                switch.assert_not_called()
                mocks['idle_gates'].assert_called_once()
                mocks['tcp_gate'].assert_called_once()
            stack, mocks = self.deployment(Path(directory))
            mocks['idle_gates'].side_effect = R.GuardError('protected_user_work_cutover_deferred')
            with stack, patch.object(R, 'switch') as switch:
                with self.assertRaisesRegex(R.GuardError, 'protected_user_work_cutover_deferred'):
                    R.deploy()
                switch.assert_not_called()

    def test_only_backend_is_switched(self):
        with tempfile.TemporaryDirectory() as directory:
            stack, mocks = self.deployment(Path(directory))
            with stack, patch.object(R, 'switch') as switch:
                R.deploy()
                self.assertEqual([(call.args[3], call.args[4]) for call in switch.call_args_list], [('backend', 'new')])
                self.assertEqual(mocks['save'].call_args.args[1]['services'], ['backend'])

    def test_completed_release_verifies_without_restart_or_gates(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'deployed.json').write_text('{}')
            stack, mocks = self.deployment(root)
            with stack, patch.object(R, 'verify') as verify, patch.object(R, 'switch') as switch:
                R.deploy()
                verify.assert_called_once()
                switch.assert_not_called()
                mocks['idle_gates'].assert_not_called()

    def test_final_switch_repeats_plan_files_ownership_work_and_tcp_before_compose(self):
        events = []
        target = {'container': 'compose-backend-1', 'newImage': 'sha256:' + 'a' * 64,
                  'frozenComposeFiles': ['frozen-base'], 'newOverlay': 'frozen-new'}
        current = container()
        with ExitStack() as stack:
            for name in ('check_plan', 'check_files', 'targets_owned', 'idle_gates', 'tcp_gate'):
                stack.enter_context(patch.object(R.M, name, side_effect=lambda *a, _name=name, **k: events.append(_name)))
            stack.enter_context(patch.object(R, 'bind_primitives'))
            stack.enter_context(patch.object(R.M, 'inspect', return_value=current))
            stack.enter_context(patch.object(R.M, 'save'))
            stack.enter_context(patch.object(R.H, 'compose_args', return_value=['synthetic-compose']))
            stack.enter_context(patch.object(R.M, 'run', side_effect=lambda *a, **k: (_ for _ in ()).throw(RuntimeError('synthetic-stop-after-compose'))))
            with self.assertRaisesRegex(RuntimeError, 'synthetic-stop-after-compose'):
                R.switch({'targets': {'backend': target}}, {}, {}, 'backend', 'new')
        self.assertEqual(events, ['check_plan', 'check_files', 'targets_owned', 'idle_gates', 'tcp_gate'])

    def test_busy_drift_and_unknown_gate_never_start_rollback(self):
        reasons = ('protected_user_work_cutover_deferred', 'protected_work_gate_unavailable', 'protected_tcp_gate_unavailable',
                   'non_target_container_changed', 'release_container_owner_changed', 'runtime_source_or_static_drift',
                   'effective_settings_drift', 'runtime_dependencies_changed', 'non_target_web_files_changed', 'future_unknown_state')
        for reason in reasons:
            with tempfile.TemporaryDirectory() as directory:
                stack, _ = self.deployment(Path(directory))
                with stack, patch.object(R, 'switch', side_effect=R.GuardError(reason)), patch.object(R, 'rollback') as rollback:
                    with self.subTest(reason=reason), self.assertRaisesRegex(R.GuardError, reason):
                        R.deploy()
                    rollback.assert_not_called()

    def test_unknown_exception_is_not_automatically_recovered(self):
        with tempfile.TemporaryDirectory() as directory:
            stack, _ = self.deployment(Path(directory))
            with stack, patch.object(R, 'switch', side_effect=RuntimeError('synthetic-unknown')), patch.object(R, 'rollback') as rollback:
                with self.assertRaisesRegex(RuntimeError, 'synthetic-unknown'):
                    R.deploy()
                rollback.assert_not_called()

    def test_owned_health_failure_reports_real_recovery_result(self):
        for failed in (False, True):
            with tempfile.TemporaryDirectory() as directory:
                stack, mocks = self.deployment(Path(directory))
                error = R.GuardError('protected_user_work_cutover_deferred') if failed else None
                with stack, patch.object(R, 'switch', side_effect=R.GuardError('target_health_failed')), patch.object(R, 'rollback', side_effect=error):
                    with self.assertRaisesRegex(R.GuardError, 'cutover_failed_rollback_' + ('needs_attention' if failed else 'succeeded')):
                        R.deploy()
                    self.assertEqual(mocks['save'].call_args.args[1]['rollbackSucceeded'], not failed)

    def test_rollback_only_reverts_proven_backend_and_verifies_hot_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            progress = {'backend': {'kind': 'new'}}
            stack, mocks = self.deployment(Path(directory), progress=progress)
            def reverted(manifest, plan, current, service, kind):
                current[service]['kind'] = kind
            with stack, patch.object(R.M, 'targets_owned') as owners, patch.object(R, 'switch', side_effect=reverted) as switch:
                R.rollback()
                owners.assert_called_once()
                self.assertEqual([(call.args[3], call.args[4]) for call in switch.call_args_list], [('backend', 'rollback')])
                mocks['verify_runtime'].assert_called_once()
                self.assertTrue(mocks['save'].call_args.args[1]['manifestPreserved'])

    def test_foreign_rollback_owner_blocks_all_mutation(self):
        with tempfile.TemporaryDirectory() as directory:
            stack, _ = self.deployment(Path(directory), progress={'backend': {'kind': 'new'}})
            with stack, patch.object(R.M, 'targets_owned', side_effect=R.GuardError('release_container_owner_changed')), patch.object(R, 'switch') as switch:
                with self.assertRaisesRegex(R.GuardError, 'release_container_owner_changed'):
                    R.rollback()
                switch.assert_not_called()

    def stopped_original(self, root, *, foreign=False, busy=False, start_error=False):
        before = container()
        current = deepcopy(before)
        current['State'].update(Running=False, Pid=0, Status='exited')
        if foreign:
            current['Config']['Env'] = ['A=foreign-change']
        (root / 'backend').mkdir()
        (root / 'backend/container-before.json').write_text(json.dumps(before))
        manifest = {'targets': {'backend': {'container': 'compose-backend-1'}}}
        commands = []
        events = []
        def command(args, **kwargs):
            commands.append(args)
            events.append('start')
            if start_error:
                raise RuntimeError('synthetic-start-failed')
            current['State'].update(Running=True, Pid=43, Status='running', StartedAt='2026-11-03T00:00:00.000000000Z')
            return subprocess.CompletedProcess(args, 0, b'', b'')
        stack = ExitStack()
        stack.enter_context(patch.object(R, 'ROOT', root))
        stack.enter_context(patch.object(R, 'check_plan', return_value=scope_plan()))
        stack.enter_context(patch.object(R.M, 'ROOT', root))
        stack.enter_context(patch.object(R, 'load_state', return_value=(manifest, {})))
        stack.enter_context(patch.object(R, 'check_files'))
        stack.enter_context(patch.object(R.M, 'targets_owned'))
        stack.enter_context(patch.object(R, 'inspect', return_value=current))
        stack.enter_context(patch.object(R.M, 'inspect', return_value=current))
        stack.enter_context(patch.object(R, 'run', side_effect=command))
        def gate(_):
            events.append('work')
            if busy:
                raise R.GuardError('protected_user_work_cutover_deferred')
        stack.enter_context(patch.object(R, 'idle_gates', side_effect=gate))
        stack.enter_context(patch.object(R, 'tcp_gate', side_effect=lambda *a, **k: events.append('tcp')))
        verify = stack.enter_context(patch.object(R, 'verify_runtime'))
        public = stack.enter_context(patch.object(R, 'public_checks'))
        stack.enter_context(patch.object(R, 'emit'))
        return stack, commands, events, verify, public

    def test_stopped_original_restoration_needs_double_owner_proof_and_both_gates(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            stack, commands, events, verify, public = self.stopped_original(root)
            with stack:
                R.rollback()
            self.assertEqual(commands, [['docker', 'start', R.BASES['backend'][0]]])
            self.assertEqual(events, ['work', 'tcp', 'start'])
            verify.assert_called_once()
            public.assert_called_once()
            self.assertEqual(set(R.read_json(root / 'baseline-restorations.json')), {'backend'})
            saved = R.read_json(root / 'backend/container-before.json')
            self.assertEqual(saved['State']['StartedAt'], '2026-10-31T16:51:34.293214151Z')

    def test_stopped_original_foreign_or_busy_never_restarts(self):
        for foreign, busy, reason in ((True, False, 'baseline_stopped_process_unproven'), (False, True, 'protected_user_work_cutover_deferred')):
            with tempfile.TemporaryDirectory() as directory:
                stack, commands, events, verify, public = self.stopped_original(Path(directory), foreign=foreign, busy=busy)
                with stack, self.assertRaisesRegex(R.GuardError, reason):
                    R.rollback()
                self.assertEqual(commands, [])
                verify.assert_not_called()
                public.assert_not_called()

    def test_stopped_original_start_failure_never_claims_restored(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            stack, commands, events, verify, public = self.stopped_original(root, start_error=True)
            with stack, self.assertRaisesRegex(RuntimeError, 'synthetic-start-failed'):
                R.rollback()
            self.assertEqual(commands, [['docker', 'start', R.BASES['backend'][0]]])
            self.assertFalse((root / 'rollback-result.json').exists())
            verify.assert_not_called()
            public.assert_not_called()


class CandidateAndVerificationTests(unittest.TestCase):
    def tearDown(self):
        R.bind_primitives()

    def test_both_fixed_images_use_original_layers_and_readonly_no_network_probe(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plan = frozen_plan(root)
            (root / 'runtime.env.private').write_text('SYNTHETIC=private\n')
            probe_result = R.read_json(root / 'candidate-probe-result.json')
            image = {'Config': {'synthetic': 'unchanged'}, 'RootFS': {'Layers': ['original-layer']}}
            commands = []
            def command(args, **kwargs):
                commands.append((args, kwargs))
                return subprocess.CompletedProcess(args, 0, json.dumps(probe_result).encode(), b'')
            def image_inventory(service, *, image=None):
                return next(item['inventory'] for item in plan['candidates'].values() if item['image'] == image)
            with patch.object(R, 'ROOT', root), patch.object(R, 'inspect', return_value=image), patch.object(R, 'verify_ancillary_inputs'), \
                 patch.object(R, 'inventory', side_effect=image_inventory) as inventory, patch.object(R, 'run', side_effect=command):
                R.candidate_checks(plan, root / 'runtime.env.private')
            self.assertEqual(inventory.call_count, 2)
            self.assertEqual(len(commands), 1)
            args, kwargs = commands[0]
            self.assertIn('--read-only', args)
            self.assertEqual(args[args.index('--network') + 1], 'none')
            self.assertEqual(args[args.index('--env-file') + 1], str(root / 'runtime.env.private'))
            self.assertIn(plan['candidates']['backend']['image'], args)
            self.assertEqual(kwargs['input'], (root / 'candidate-probe.py').read_bytes())

    def test_bad_image_inventory_or_probe_output_never_prepares(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plan = frozen_plan(root)
            image = {'Config': {}, 'RootFS': {'Layers': ['synthetic-original']}}
            with patch.object(R, 'ROOT', root), patch.object(R, 'inspect', return_value=image), patch.object(R, 'inventory', return_value={}), \
                 patch.object(R, 'run') as run:
                with self.assertRaisesRegex(R.GuardError, 'candidate_image_inventory_drift'):
                    R.candidate_checks(plan, root / 'runtime.env.private')
                run.assert_not_called()
            def image_inventory(service, *, image=None):
                return next(item['inventory'] for item in plan['candidates'].values() if item['image'] == image)
            with patch.object(R, 'ROOT', root), patch.object(R, 'inspect', return_value=image), patch.object(R, 'verify_ancillary_inputs'), \
                 patch.object(R, 'inventory', side_effect=image_inventory), patch.object(R, 'run', return_value=subprocess.CompletedProcess([], 0, b'{"passed":false}', b'')):
                with self.assertRaisesRegex(R.GuardError, 'candidate_actual_probe_mismatch'):
                    R.candidate_checks(plan, root / 'runtime.env.private')

    def test_public_checks_verify_existing_routes_without_openapi_proxy_assumption(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plan = frozen_plan(root)
            requests = []
            class Response(io.BytesIO):
                status = 200
            class Opener:
                def open(self, request, timeout):
                    requests.append(request.full_url)
                    if '/healthz' in request.full_url:
                        return Response(b'{"data":{"status":"ok"}}')
                    return Response(b'synthetic-static')
            plan['webInventory'] = dict.fromkeys(plan['webInventory'], R.digest(b'synthetic-static'))
            with patch.object(R, 'ROOT', root), patch.object(R, 'build_opener', return_value=Opener()):
                R.public_checks(plan, {'backend': {'kind': 'new'}})
            self.assertTrue(all('openapi' not in request for request in requests))
            for path in ('/login', '/app/mock-interviews', '/app/resume-optimizer', '/app/written-exams', '/healthz'):
                self.assertTrue(any(request.split('?')[0] == 'https://mianshiwen.cn' + path for request in requests))
            self.assertEqual(len(R.read_json(root / 'public-verification.json')['checks']), 16)

    def test_verify_runtime_checks_web_bytes_and_installed_dependencies(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plan = frozen_plan(root)
            manifest = {'targets': {'backend': {}}}
            with patch.object(R.M, 'verify_runtime') as original, patch.object(R, 'inventory', return_value=plan['webInventory']), \
                 patch.object(R, 'runtime_contract', return_value=plan['runtimeBefore']), patch.object(R, 'verify_ancillary_inputs'), patch.object(R, 'verify_single_writer'):
                R.verify_runtime(manifest, plan, {'backend': {'kind': 'new'}}, final=True)
                original.assert_called_once()
            with patch.object(R.M, 'verify_runtime'), patch.object(R, 'inventory', return_value={}), \
                 self.assertRaisesRegex(R.GuardError, 'non_target_web_files_changed'):
                R.verify_runtime(manifest, plan, {})
            with patch.object(R.M, 'verify_runtime'), patch.object(R, 'inventory', return_value=plan['webInventory']), \
                 patch.object(R, 'runtime_contract', return_value={}), self.assertRaisesRegex(R.GuardError, 'runtime_dependencies_changed'):
                R.verify_runtime(manifest, plan, {})


class EntityAndWriterTests(unittest.TestCase):
    def tearDown(self):
        R.bind_primitives()

    @staticmethod
    def entity_counts():
        protected = ('activeCnBindings', 'activeCnCandidates', 'pendingCnCandidateClaims', 'recentCnEntityWrites',
                     'unknownCnSessionStates', 'invalidCnEntityMetadata', 'cnEntityReadFailures',
                     'cnEntityScanLimitExceeded', 'cnEntityMutationDetected')
        informational = ('cnBoundBindings', 'cnStaleBindings', 'cnRetiredBindings', 'cnCandidates',
                         'cnRetiredCandidates', 'cnHistoricalEntities', 'scannedCnEntityRecords')
        return dict.fromkeys((*protected, *informational), 0) | {'atMs': int(time.time() * 1000)}

    def test_eighth_gate_is_additive_and_reviewed_hook_cannot_recurse(self):
        events = []
        R.bind_primitives()
        with tempfile.TemporaryDirectory() as directory, patch.object(R, 'ROOT', Path(directory)), \
             patch.object(R, 'verify_single_writer', side_effect=lambda: events.append('single')), \
             patch.object(R, '_reviewed_idle_gates', side_effect=lambda _: events.append('seven') or ['original-seven']), \
             patch.object(R, 'entity_idle_gate', side_effect=lambda _: events.append('entity')):
            (R.ROOT / 'last-idle-gates.json').write_text('[]')
            (R.ROOT / 'last-entity-idle-gate.json').write_text('{}')
            self.assertIs(R.M.idle_gates, R.idle_gates)
            self.assertEqual(R.M.idle_gates({}), ['original-seven'])
        self.assertEqual(events, ['single', 'seven', 'entity'])
        self.assertEqual(R.GATES, R.M.GATES)
        self.assertEqual(len(R.GATES), 7)

    def test_entity_gate_contract_zero_history_is_idle_but_work_is_not(self):
        with patch.object(R, 'save') as save:
            counts = self.entity_counts() | {'cnRetiredBindings': 42, 'cnHistoricalEntities': 99}
            R.validate_entity_gate(counts, 0)
            save.assert_called_once_with('last-entity-idle-gate.json', counts)
        for field in ('activeCnBindings', 'activeCnCandidates', 'pendingCnCandidateClaims',
                      'recentCnEntityWrites', 'cnEntityMutationDetected'):
            with self.subTest(field=field), patch.object(R, 'save'), \
                 self.assertRaisesRegex(R.GuardError, 'protected_user_work_cutover_deferred'):
                R.validate_entity_gate(self.entity_counts() | {field: 1}, 75)

    def test_entity_unknown_read_failure_shape_boolean_age_and_exit_fail_closed(self):
        for field in ('unknownCnSessionStates', 'invalidCnEntityMetadata', 'cnEntityReadFailures', 'cnEntityScanLimitExceeded'):
            with self.subTest(field=field), patch.object(R, 'save'), \
                 self.assertRaisesRegex(R.GuardError, 'protected_entity_gate_unavailable'):
                R.validate_entity_gate(self.entity_counts() | {field: 1}, 75)
        base = self.entity_counts()
        malformed = [({}, 0), (base | {'unreviewed': 0}, 0), (base | {'cnCandidates': False}, 0),
                     (base | {'cnCandidates': -1}, 0), (base | {'atMs': base['atMs']-10001}, 0),
                     (base | {'atMs': base['atMs']+100000}, 0), (base, 75), (base, 1),
                     (base | {'activeCnBindings': 1}, 0)]
        for counts, code in malformed:
            with self.subTest(value=counts, code=code), patch.object(R, 'save'), \
                 self.assertRaisesRegex(R.GuardError, 'protected_entity_gate_unavailable'):
                R.validate_entity_gate(counts, code)

    def test_entity_gate_runs_pinned_readonly_command_and_never_constructs_repo(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plan = frozen_plan(root)
            counts = self.entity_counts()
            with patch.object(R, 'ROOT', root), patch.object(R.P, 'gate_command', return_value=['synthetic-readonly-gate']) as command, \
                 patch.object(R.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, json.dumps(counts).encode(), b'')) as process, \
                 patch.object(R, 'save'):
                R.entity_idle_gate({'synthetic': 'manifest'})
            command.assert_called_once_with({'synthetic': 'manifest'})
            self.assertEqual(process.call_args.args[0], ['synthetic-readonly-gate'])
            self.assertEqual(process.call_args.kwargs['input'], (root / R.ENTITY_GATE).read_bytes())
            self.assertEqual(process.call_args.kwargs['timeout'], 25)
            self.assertEqual(R.digest((root / R.ENTITY_GATE).read_bytes()), plan['supportFiles'][R.ENTITY_GATE])

    def test_new_and_rollback_switch_both_repeat_all_eight_gates_before_tcp_and_compose(self):
        for kind in ('new', 'rollback'):
            events = []
            R.bind_primitives()
            target = {'container': 'compose-backend-1', 'newImage': 'sha256:'+'a'*64, 'rollbackImage': R.ROLLBACK_IMAGE,
                      'frozenComposeFiles': ['frozen-base'], 'newOverlay': 'frozen-new', 'rollbackOverlay': 'frozen-rollback'}
            with ExitStack() as stack:
                directory = stack.enter_context(tempfile.TemporaryDirectory())
                root = Path(directory)
                stack.enter_context(patch.object(R, 'ROOT', root))
                (root / 'last-idle-gates.json').write_text('[]')
                (root / 'last-entity-idle-gate.json').write_text('{}')
                stack.enter_context(patch.object(R, 'bind_primitives'))
                for name in ('check_plan', 'check_files', 'targets_owned'):
                    stack.enter_context(patch.object(R.M, name, side_effect=lambda *a, _name=name, **k: events.append(_name)))
                stack.enter_context(patch.object(R, 'verify_single_writer', side_effect=lambda: events.append('single')))
                stack.enter_context(patch.object(R, '_reviewed_idle_gates', side_effect=lambda _: events.append('seven')))
                stack.enter_context(patch.object(R, 'entity_idle_gate', side_effect=lambda _: events.append('entity')))
                stack.enter_context(patch.object(R.M, 'tcp_gate', side_effect=lambda *a, **k: events.append('tcp')))
                stack.enter_context(patch.object(R.M, 'inspect', return_value=container()))
                stack.enter_context(patch.object(R.M, 'save'))
                stack.enter_context(patch.object(R.H, 'compose_args', return_value=['synthetic-compose']))
                def compose(*a, **k):
                    events.append('compose')
                    raise RuntimeError('synthetic-stop-after-compose')
                stack.enter_context(patch.object(R.M, 'run', side_effect=compose))
                with self.subTest(kind=kind), self.assertRaisesRegex(RuntimeError, 'synthetic-stop-after-compose'):
                    R.switch({'targets': {'backend': target}}, {}, {}, 'backend', kind)
            self.assertEqual(events, ['check_plan', 'check_files', 'targets_owned', 'single', 'seven', 'entity', 'tcp', 'compose'])

    def test_entity_busy_or_unknown_before_actual_rollback_never_mutates(self):
        for reason in ('protected_user_work_cutover_deferred', 'protected_entity_gate_unavailable'):
            R.bind_primitives()
            target = {'container': 'compose-backend-1'}
            with ExitStack() as stack:
                stack.enter_context(patch.object(R, 'bind_primitives'))
                for name in ('check_plan', 'check_files', 'targets_owned'):
                    stack.enter_context(patch.object(R.M, name))
                stack.enter_context(patch.object(R, 'verify_single_writer'))
                stack.enter_context(patch.object(R, '_reviewed_idle_gates'))
                stack.enter_context(patch.object(R, 'entity_idle_gate', side_effect=R.GuardError(reason)))
                mutation = stack.enter_context(patch.object(R.M, 'run'))
                tcp = stack.enter_context(patch.object(R.M, 'tcp_gate'))
                with self.subTest(reason=reason), self.assertRaisesRegex(R.GuardError, reason):
                    R.switch({'targets': {'backend': target}}, {}, {'backend': {'kind': 'new'}}, 'backend', 'rollback')
                mutation.assert_not_called()
                tcp.assert_not_called()

    def writer(self, *, current=None, names='compose-backend-1\n', value=None, read_error=False, owner_changed=False):
        current = current or container()
        commands = []
        def command(args, **kwargs):
            commands.append(args)
            if args[:2] == ['docker', 'ps']:
                return subprocess.CompletedProcess(args, 0, names.encode(), b'')
            if read_error:
                raise RuntimeError('synthetic-private-process-error')
            return subprocess.CompletedProcess(args, 0, json.dumps({'serverProcesses': 1} if value is None else value).encode(), b'')
        after = deepcopy(current)
        if owner_changed:
            after['State']['StartedAt'] = '2026-11-04T00:00:00Z'
        stack = ExitStack()
        stack.enter_context(patch.object(R, 'inspect', side_effect=[current, after]))
        stack.enter_context(patch.object(R, 'run', side_effect=command))
        return stack, commands

    def test_single_writer_matches_container_command_environment_and_actual_process(self):
        stack, commands = self.writer()
        with stack:
            R.verify_single_writer()
        self.assertEqual(commands[0], ['docker', 'ps', '--filter', 'label=com.docker.compose.service=backend', '--format', '{{.Names}}'])
        self.assertEqual(commands[1][:6], ['docker', 'exec', R.BASES['backend'][0], 'python', '-B', '-c'])
        self.assertIn('FileNotFoundError', commands[1][-1])
        self.assertIn('--multiprocessing-fork', commands[1][-1])
        for extra in (['--workers', '1'], ['--workers=1']):
            current = container();current['Config']['Cmd'] += extra
            stack, _ = self.writer(current=current)
            with stack:
                R.verify_single_writer()

    def test_exact_actual_dockerfile_python_module_command_and_versioned_python_are_supported(self):
        lines = (REPO / 'infra/docker/backend.Dockerfile').read_text().splitlines()
        actual = json.loads(next(line.removeprefix('CMD ') for line in lines if line.startswith('CMD ')))
        self.assertEqual(actual, ['python', '-m', 'uvicorn', 'app.main:app', '--host', '0.0.0.0', '--port', '8000', '--app-dir', 'apps/backend'])
        for interpreter in ('python', 'python3', '/usr/local/bin/python3.13', '/usr/local/bin/python3.13.15'):
            current = container();current['Config']['Cmd'] = [interpreter, *actual[1:]]
            stack, commands = self.writer(current=current)
            with stack, self.subTest(interpreter=interpreter):
                R.verify_single_writer()
            self.assertEqual(len(commands), 2)
        current = container();current['Config']['Entrypoint'] = ['python', '-m', 'uvicorn'];current['Config']['Cmd'] = actual[3:]
        stack, commands = self.writer(current=current)
        with stack:
            R.verify_single_writer()
        self.assertEqual(len(commands), 2)

    def test_module_form_keeps_worker_environment_and_process_proof(self):
        for option in ([], ['--workers', '1'], ['--workers=1']):
            current = container();current['Config']['Cmd'] = ['python', '-m', 'uvicorn', 'app.main:app', *option]
            stack, _ = self.writer(current=current)
            with stack:
                R.verify_single_writer()
        for option, environment in ((['--workers', '2'], []), (['--workers=2'], []), ([], ['WEB_CONCURRENCY=2']), ([], ['GUNICORN_CMD_ARGS=--workers=2'])):
            current = container();current['Config']['Cmd'] = ['python3.13', '-m', 'uvicorn', 'app.main:app', *option]
            current['Config']['Env'] += environment
            stack, commands = self.writer(current=current)
            with stack, self.subTest(option=option, environment=environment), self.assertRaisesRegex(R.GuardError, 'single_writer_config_unproven'):
                R.verify_single_writer()
            self.assertEqual(len(commands), 1)
        current = container();current['Config']['Cmd'] = ['python', '-m', 'uvicorn', 'app.main:app']
        stack, _ = self.writer(current=current, value={'serverProcesses': 2})
        with stack, self.assertRaisesRegex(R.GuardError, 'single_writer_process_count_unproven'):
            R.verify_single_writer()

    def test_module_support_never_admits_shell_wrapper_other_module_or_malformed_command(self):
        for command in (['sh', '-c', 'python -m uvicorn app.main:app'], ['/usr/bin/env', 'python', '-m', 'uvicorn', 'app.main:app'],
                        ['python-wrapper', '-m', 'uvicorn', 'app.main:app'], ['python3.13-evil', '-m', 'uvicorn', 'app.main:app'],
                        ['python', '-c', 'uvicorn.run()'], ['python', '-m', 'gunicorn', 'app.main:app'],
                        ['python', '-m', 'uvicorn'], ['python', '-B', '-m', 'uvicorn', 'app.main:app'],
                        ['python', '-m', 'uvicorn', 'wrong.main:app'], ['python', '-m', 'uvicorn', 'app.main:app', '--reload'],
                        ['python', '-m', 'uvicorn', 'app.main:app', '--workers'], [], [None], 'python -m uvicorn app.main:app'):
            current = container();current['Config']['Cmd'] = command
            stack, commands = self.writer(current=current)
            with stack, self.subTest(command=command), self.assertRaisesRegex(R.GuardError, 'single_writer_command_unproven'):
                R.verify_single_writer()
            self.assertEqual(len(commands), 1)

    def test_multiple_or_unreadable_server_processes_fail_closed_including_boolean(self):
        for value in ({'serverProcesses': 0}, {'serverProcesses': 2}, {'serverProcesses': True}, {'serverProcesses': 1.0},
                      {'serverProcesses': 1, 'extra': 0}, []):
            stack, _ = self.writer(value=value)
            with stack, self.subTest(value=value), self.assertRaisesRegex(R.GuardError, 'single_writer_process_count_unproven'):
                R.verify_single_writer()
        stack, _ = self.writer(read_error=True)
        with stack, self.assertRaisesRegex(R.GuardError, 'single_writer_process_read_failed'):
            R.verify_single_writer()
        stack, _ = self.writer(owner_changed=True)
        with stack, self.assertRaisesRegex(R.GuardError, 'single_writer_owner_changed'):
            R.verify_single_writer()

    def test_extra_backend_and_worker_configuration_never_reaches_process_probe(self):
        values = []
        values.append((container(), 'compose-backend-1\nforeign-backend\n', 'single_backend_container_unproven'))
        for command in (['gunicorn', 'app.main:app'], ['uvicorn', 'app.main:app', '--reload'],
                        ['uvicorn', 'wrong.main:app'], ['uvicorn', 'app.main:app', '--workers']):
            current = container();current['Config']['Cmd'] = command
            values.append((current, 'compose-backend-1\n', 'single_writer_command_unproven'))
        for setting in ('WEB_CONCURRENCY=2', 'WEB_CONCURRENCY=0', 'GUNICORN_CMD_ARGS=--workers=2'):
            current = container();current['Config']['Env'].append(setting)
            values.append((current, 'compose-backend-1\n', 'single_writer_config_unproven'))
        for option in (['--workers', '2'], ['--workers=2']):
            current = container();current['Config']['Cmd'] += option
            values.append((current, 'compose-backend-1\n', 'single_writer_config_unproven'))
        for current, names, reason in values:
            stack, commands = self.writer(current=current, names=names)
            with stack, self.subTest(reason=reason), self.assertRaisesRegex(R.GuardError, reason):
                R.verify_single_writer()
            self.assertEqual(len(commands), 1)

    def test_stopped_owned_original_needs_proven_dead_process_and_no_competing_container(self):
        current = container();current['State'].update(Running=False, Pid=0, Status='exited')
        stack, commands = self.writer(current=current, names='')
        with stack:
            R.verify_single_writer()
        self.assertEqual(len(commands), 1)
        current['State']['Pid'] = 10
        stack, _ = self.writer(current=current, names='')
        with stack, self.assertRaisesRegex(R.GuardError, 'single_writer_stopped_process_unproven'):
            R.verify_single_writer()

    def test_actual_proc_probe_counts_spawn_workers_ignores_inspector_and_disappeared_pid(self):
        stack, commands = self.writer()
        with stack:
            R.verify_single_writer()
        code = commands[1][-1]
        class Entry:
            def __init__(self, args):
                self.args = args
            def read_bytes(self):
                if self.args is None:
                    raise FileNotFoundError('synthetic transient PID')
                return b'\0'.join(self.args) + b'\0'
        rows = []
        class Proc:
            def __init__(self, path):
                assert path == '/proc'
            def glob(self, pattern):
                assert pattern == '[0-9]*/cmdline'
                return [Entry(args) for args in rows]
        inspector = [b'python', b'-B', b'-c', code.encode()]
        cases = [([[b'/usr/local/bin/uvicorn', b'app.main:app'], inspector, None], 1),
                 ([[b'/usr/local/bin/python', b'/usr/local/bin/uvicorn', b'app.main:app'], inspector], 1),
                 ([[b'python', b'-m', b'uvicorn', b'app.main:app'], [b'python', b'-c', b'spawn', b'--multiprocessing-fork']], 2),
                 ([[b'gunicorn', b'app.main:app'], [b'python', b'-m', b'multiprocessing.spawn']], 2)]
        for rows, expected in cases:
            output = io.StringIO()
            with self.subTest(expected=expected), patch('pathlib.Path', Proc), patch('sys.stdout', output):
                exec(compile(code, '<synthetic-proc-probe>', 'exec'), {})
            self.assertEqual(json.loads(output.getvalue()), {'serverProcesses': expected})

    def test_ancillary_format_is_pinned_separately_in_plan_running_and_both_images(self):
        plan = scope_plan() | {'ancillaryInputs': deepcopy(R.ANCILLARY_INPUTS)}
        relative = next(iter(R.ANCILLARY_INPUTS))
        data = (REPO / relative).read_bytes()
        self.assertEqual(R.digest(data), R.ANCILLARY_INPUTS[relative])
        with patch.object(R.H, 'read_container', return_value=data) as live, patch.object(R.M, 'read_image_file', return_value=data) as image:
            R.verify_ancillary_inputs(plan)
            R.verify_ancillary_inputs(plan, image='synthetic-candidate')
            R.verify_ancillary_inputs(plan, image=R.ROLLBACK_IMAGE)
        live.assert_called_once_with('compose-backend-1', '/app/' + relative)
        self.assertEqual(image.call_count, 2)
        with patch.object(R.H, 'read_container', return_value=b'changed'), self.assertRaisesRegex(R.GuardError, 'ancillary_input_drift'):
            R.verify_ancillary_inputs(plan)
        for changed in ({}, R.ANCILLARY_INPUTS | {'unapproved': R.digest(b'extra')}):
            with self.subTest(changed=changed), self.assertRaisesRegex(R.GuardError, 'ancillary_inputs_contract_changed'):
                R.verify_ancillary_inputs(plan | {'ancillaryInputs': changed})

    def test_twelve_sources_non_targets_eighth_gate_and_ancillary_contract_are_frozen(self):
        plan = scope_plan()
        old, new = plan['baselines']['backend']['inventory'], plan['candidates']['backend']['inventory']
        self.assertEqual(len(set(new)-set(R.APPROVED_BACKEND_SHA256)), 225)
        self.assertEqual({path for path in old if old[path] != new[path]} | (set(new)-set(old)), set(R.APPROVED_BACKEND_SHA256))
        self.assertIn(R.ENTITY_GATE, R.support_paths())
        self.assertEqual(plan['candidates']['backendRollback']['image'], R.BASES['backend'][1])
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            original = frozen_plan(root)
            original_bytes = (root / R.ENTITY_GATE).read_bytes()
            (root / 'input.json').write_text(json.dumps(original))
            with patch.object(R, 'ROOT', root):
                R.check_plan()
                (root / R.ENTITY_GATE).write_bytes(b'changed')
                with self.assertRaisesRegex(R.GuardError, 'release_controller_drift'):
                    R.check_plan()
                (root / R.ENTITY_GATE).write_bytes(original_bytes)
                for changed in ({}, R.ANCILLARY_INPUTS | {'unapproved': R.digest(b'extra')}):
                    (root / 'input.json').write_text(json.dumps(original | {'ancillaryInputs': changed}))
                    with self.assertRaisesRegex(R.GuardError, 'ancillary_inputs_contract_changed'):
                        R.check_plan()


class PreparationTests(unittest.TestCase):
    def tearDown(self):
        R.bind_primitives()

    def test_prepared_reentry_rechecks_work_and_tcp_without_refreezing_or_switching(self):
        for busy in (False, True):
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                prepared = b'{"synthetic":"unchanged-preparation"}'
                (root / 'prepared.json').write_bytes(prepared)
                manifest, progress = {'targets': {'backend': {}}}, {}
                events = []
                def idle(_):
                    events.append('idle')
                    if busy:
                        raise R.GuardError('protected_user_work_cutover_deferred')
                with ExitStack() as stack:
                    stack.enter_context(patch.object(R, 'ROOT', root))
                    stack.enter_context(patch.object(R, 'check_plan', return_value=scope_plan()))
                    stack.enter_context(patch.object(R, 'load_state', return_value=(manifest, progress)))
                    stack.enter_context(patch.object(R, 'verify_runtime', side_effect=lambda *a, **k: events.append('verify')))
                    stack.enter_context(patch.object(R, 'idle_gates', side_effect=idle))
                    tcp = stack.enter_context(patch.object(R, 'tcp_gate', side_effect=lambda *a, **k: events.append('tcp')))
                    emit = stack.enter_context(patch.object(R, 'emit'))
                    freeze = stack.enter_context(patch.object(R.H, 'freeze'))
                    switch = stack.enter_context(patch.object(R, 'switch'))
                    if busy:
                        with self.assertRaisesRegex(R.GuardError, 'protected_user_work_cutover_deferred'):
                            R.prepare()
                        tcp.assert_not_called()
                        emit.assert_not_called()
                    else:
                        R.prepare()
                        emit.assert_called_once_with(prepared=True, alreadyPrepared=True, productionChanged=False)
                        tcp.assert_called_once_with(manifest, progress)
                    freeze.assert_not_called()
                    switch.assert_not_called()
                self.assertEqual(events, ['verify', 'idle'] + ([] if busy else ['tcp']))
                self.assertEqual((root / 'prepared.json').read_bytes(), prepared)

    def test_initial_prepare_freezes_then_gates_without_production_mutation_and_busy_remains_reentrant(self):
        for busy in (False, True):
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                plan = frozen_plan(root)
                current = container()
                plan['baselines']['backend'].update(R.H.container_signature(current))
                before = {f'synthetic-{n}': n for n in range(341)} | {'product_edition': 'cn', 'environment': 'production', 'cn_hot_database_pool_enabled': False}
                plan['baselines']['backend']['settingsSha256'] = R.P.settings_sha(before)
                for candidate in plan['candidates'].values():
                    candidate['settingsSha256'] = plan['baselines']['backend']['settingsSha256']
                non_targets = {name: container(R.digest(name.encode()), 'sha256:'+'f'*64) for name in plan['nonTargets']}
                plan['nonTargets'] = {name: R.H.container_signature(value) for name, value in non_targets.items()}
                (root / 'input.json').write_text(json.dumps(plan))
                events, commands = [], []
                def freeze(value, service):
                    events.append('freeze')
                    (root / service).mkdir()
                    (root / service / 'rendered-before.json').write_text(json.dumps({'services': {'backend': {'image': value['Image']}}}))
                    (root / service / 'container-before.json').write_text(json.dumps(value))
                    return {'container': 'compose-backend-1', 'service': 'backend'}
                def idle(manifest):
                    events.append('idle')
                    self.assertTrue((root / 'prepared.json').exists())
                    if busy:
                        raise R.GuardError('protected_user_work_cutover_deferred')
                def command(args, **kwargs):
                    commands.append(args)
                    assert args == ['docker', 'ps', '--format', '{{.Names}}']
                    return subprocess.CompletedProcess(args, 0, ('\n'.join(['compose-backend-1', *non_targets])+'\n').encode(), b'')
                with ExitStack() as stack:
                    stack.enter_context(patch.object(R, 'ROOT', root))
                    stack.enter_context(patch.object(R, 'check_plan', return_value=plan))
                    stack.enter_context(patch.object(R.P, 'schema', return_value={'paths': {}}))
                    stack.enter_context(patch.object(R.P, 'check_schema'))
                    stack.enter_context(patch.object(R.P, 'nginx_inputs', return_value=plan['nginxInputs']))
                    stack.enter_context(patch.object(R, 'inspect', side_effect=lambda name: current if name == 'compose-backend-1' else non_targets[name]))
                    stack.enter_context(patch.object(R, 'inventory', side_effect=lambda service, **kwargs: plan['webInventory'] if service == 'web' else plan['baselines']['backend']['inventory']))
                    stack.enter_context(patch.object(R, 'runtime_contract', return_value=plan['runtimeBefore']))
                    stack.enter_context(patch.object(R, 'verify_ancillary_inputs'))
                    stack.enter_context(patch.object(R, 'verify_single_writer'))
                    stack.enter_context(patch.object(R.H, 'freeze', side_effect=freeze))
                    stack.enter_context(patch.object(R.P, 'settings', return_value=before))
                    stack.enter_context(patch.object(R.H, 'rendered', side_effect=lambda target, frozen, overlay: R.read_json(overlay)))
                    stack.enter_context(patch.object(R, 'run', side_effect=command))
                    stack.enter_context(patch.object(R, 'candidate_checks'))
                    stack.enter_context(patch.object(R, 'verify_runtime', side_effect=lambda *a, **k: events.append('verify')))
                    stack.enter_context(patch.object(R, 'idle_gates', side_effect=idle))
                    tcp = stack.enter_context(patch.object(R, 'tcp_gate', side_effect=lambda *a, **k: events.append('tcp')))
                    stack.enter_context(patch.object(R, 'emit'))
                    switch = stack.enter_context(patch.object(R, 'switch'))
                    if busy:
                        with self.assertRaisesRegex(R.GuardError, 'protected_user_work_cutover_deferred'):
                            R.prepare()
                        tcp.assert_not_called()
                    else:
                        R.prepare()
                        tcp.assert_called_once()
                    switch.assert_not_called()
                self.assertEqual(events, ['freeze', 'verify', 'idle'] + ([] if busy else ['tcp']))
                self.assertTrue((root / 'prepared.json').exists())
                self.assertEqual(commands, [['docker', 'ps', '--format', '{{.Names}}']])


class AuthorizedResidualTcpTests(unittest.TestCase):
    def tearDown(self):
        R._idle_authorization = None
        R.bind_primitives()

    @staticmethod
    def idle_raw(path):
        if path == 'legacy-gates/readiness-idle.py':
            return {'mockPhases': {'preparing': 0, 'completed': 0}}
        with patch.object(R.H, 'ROOT', R.SUPPORT):
            protected, informational = R.H.gate_contract(path)
        result = dict.fromkeys(protected | informational, 0)
        if path == 'legacy-gates/check-idle.py':
            result['checked_at'] = '2026-11-04T00:00:00Z'
        elif path == 'legacy-gates/idle_gate.py':
            result.update(atMs=int(time.time()*1000), sampleAgeMs=0)
        return result

    def scenario(self, *, count=1, current=None):
        stack = ExitStack()
        root = Path(stack.enter_context(tempfile.TemporaryDirectory()))
        frozen_plan(root)
        (root / 'backend').mkdir()
        before = container()
        (root / 'backend/container-before.json').write_text(json.dumps(before))
        current = current or deepcopy(before)
        manifest = {'targets': {'backend': {'container': 'compose-backend-1'}},
                    'orphanAnswerContext': R.P.expected_orphan_context({'startedAt': before['State']['StartedAt']})}
        values = {'passed': True, 'atMs': int(time.time()*1000), 'establishedPort8000': count, 'tablesRead': 2,
                  'scannedRows': 4, 'scope': 'container_tcp8000_established_only', 'networkNamespaceSha256': 'synthetic-ns'}
        entity = EntityAndWriterTests.entity_counts()
        controls = {'blockedGate': None, 'blockedField': None, 'entity': entity, 'tcpReadFailure': False}
        commands = []
        gate_number = 0
        def command(args, **kwargs):
            nonlocal gate_number
            if args[:2] == ['docker', 'exec']:
                commands.append('tcp')
                if controls['tcpReadFailure']:
                    raise RuntimeError('synthetic-private-tcp-read-error')
                return subprocess.CompletedProcess(args, 0, json.dumps(values).encode(), b'')
            self.assertEqual(args[:2], ['docker', 'run'])
            if kwargs['input'] == (root / R.ENTITY_GATE).read_bytes():
                commands.append('entity')
                result = controls['entity']
                return subprocess.CompletedProcess(args, 75 if any(result[field] for field in (
                    'activeCnBindings', 'activeCnCandidates', 'pendingCnCandidateClaims', 'recentCnEntityWrites',
                    'unknownCnSessionStates', 'invalidCnEntityMetadata', 'cnEntityReadFailures',
                    'cnEntityScanLimitExceeded', 'cnEntityMutationDetected')) else 0, json.dumps(result).encode(), b'')
            path = R.GATES[gate_number % len(R.GATES)]
            gate_number += 1
            commands.append(path)
            result = self.idle_raw(path)
            code = 0
            if controls['blockedGate'] == path:
                result[controls['blockedField']] = 1
                code = 75
            return subprocess.CompletedProcess(args, code, json.dumps(result).encode(), b'')
        stack.enter_context(patch.object(R, 'ROOT', root))
        R.bind_primitives()
        stack.enter_context(patch.object(R, 'verify_single_writer'))
        stack.enter_context(patch.object(R, 'inspect', return_value=current))
        stack.enter_context(patch.object(R.M, 'inspect', return_value=current))
        stack.enter_context(patch.object(R.H, 'running_process_identity', side_effect=lambda c: (c['Id'], c['State']['Pid'], c['State']['StartedAt'])))
        stack.enter_context(patch.object(R.H, 'host_network_namespace', return_value='synthetic-ns'))
        stack.enter_context(patch.object(R.subprocess, 'run', side_effect=command))
        return stack, root, manifest, current, values, controls, commands

    def test_exact_original_one_connection_exception_runs_all_real_gate_validation_and_is_consumed(self):
        stack, root, manifest, _, _, _, commands = self.scenario()
        with stack:
            self.assertIs(R.M.tcp_gate, R.tcp_gate)
            R.idle_gates(manifest)
            self.assertIsNotNone(R._idle_authorization)
            R.M.tcp_gate(manifest, {})
            self.assertIsNone(R._idle_authorization)
            audit = R.read_json(root / 'last-user-authorized-tcp-exception.json')
            self.assertEqual(audit['establishedPort8000'], 1)
            self.assertTrue(audit['normalTcpProcessNamespaceAndFreshnessChecksPassed'])
            self.assertFalse(audit['recoveryExceptionAllowed'])
            self.assertEqual(commands, [*R.GATES, 'entity', 'tcp'])
            with self.assertRaisesRegex(R.GuardError, 'authorized_tcp_idle_proof_missing_or_stale'):
                R.tcp_gate(manifest, {})

    def test_zero_tcp_still_passes_without_exception_or_idle_override(self):
        stack, root, manifest, _, _, _, commands = self.scenario(count=0)
        with stack:
            R.tcp_gate(manifest, {})
            self.assertEqual(commands, ['tcp'])
            self.assertFalse((root / 'last-user-authorized-tcp-exception.json').exists())

    def test_old_saved_gate_files_without_inprocess_proof_cannot_authorize(self):
        stack, root, manifest, _, _, _, _ = self.scenario()
        with stack:
            (root / 'last-idle-gates.json').write_text('[]')
            (root / 'last-entity-idle-gate.json').write_text('{}')
            with self.assertRaisesRegex(R.GuardError, 'authorized_tcp_idle_proof_missing_or_stale'):
                R.tcp_gate(manifest, {})
            self.assertFalse((root / 'last-user-authorized-tcp-exception.json').exists())

    def test_proof_expiry_or_changed_gate_evidence_cannot_authorize(self):
        for mutation in ('age', 'legacy', 'entity'):
            stack, root, manifest, _, _, _, _ = self.scenario()
            with stack, self.subTest(mutation=mutation):
                R.idle_gates(manifest)
                if mutation == 'age':
                    R._idle_authorization['atMonotonic'] -= 11
                else:
                    name = 'last-idle-gates.json' if mutation == 'legacy' else 'last-entity-idle-gate.json'
                    (root / name).write_text('{}')
                with self.assertRaisesRegex(R.GuardError, 'authorized_tcp_idle_proof_missing_or_stale'):
                    R.tcp_gate(manifest, {})
                self.assertIsNone(R._idle_authorization)
                self.assertFalse((root / 'last-user-authorized-tcp-exception.json').exists())

    def test_real_legacy_live_mock_lease_and_unfinished_task_busy_clear_previous_proof(self):
        cases = [(R.GATES[0], 'liveInterviews'), ('extra_idle_gate.py', 'mockListening'),
                 ('extra_idle_gate.py', 'livePageLeases'), ('extra_idle_gate.py', 'unfinishedChatTasks'),
                 ('active_work_gate.py', 'connectedDesktopPublishers')]
        for gate, field in cases:
            stack, root, manifest, _, _, controls, _ = self.scenario()
            with stack, self.subTest(field=field):
                R.idle_gates(manifest)
                controls.update(blockedGate=gate, blockedField=field)
                with self.assertRaisesRegex(R.GuardError, 'protected_user_work_cutover_deferred'):
                    R.idle_gates(manifest)
                self.assertIsNone(R._idle_authorization)
                with self.assertRaisesRegex(R.GuardError, 'authorized_tcp_idle_proof_missing_or_stale'):
                    R.tcp_gate(manifest, {})
                self.assertFalse((root / 'last-user-authorized-tcp-exception.json').exists())

    def test_real_entity_claim_active_or_unknown_gate_clears_previous_proof(self):
        for field, reason in (('pendingCnCandidateClaims', 'protected_user_work_cutover_deferred'),
                              ('activeCnBindings', 'protected_user_work_cutover_deferred'),
                              ('cnEntityReadFailures', 'protected_entity_gate_unavailable')):
            stack, root, manifest, _, _, controls, _ = self.scenario()
            with stack, self.subTest(field=field):
                R.idle_gates(manifest)
                controls['entity'][field] = 1
                with self.assertRaisesRegex(R.GuardError, reason):
                    R.idle_gates(manifest)
                self.assertIsNone(R._idle_authorization)
                with self.assertRaisesRegex(R.GuardError, 'authorized_tcp_idle_proof_missing_or_stale'):
                    R.tcp_gate(manifest, {})
                self.assertFalse((root / 'last-user-authorized-tcp-exception.json').exists())

    def test_more_than_one_boolean_stale_namespace_shape_and_read_errors_never_override(self):
        cases = [('count', {'establishedPort8000': 2}, 'protected_user_work_cutover_deferred'),
                 ('boolean', {'establishedPort8000': True}, 'protected_tcp_gate_unavailable'),
                 ('stale', {'atMs': int(time.time()*1000)-10001}, 'protected_tcp_gate_unavailable'),
                 ('namespace', {'networkNamespaceSha256': 'wrong-ns'}, 'protected_tcp_gate_unavailable'),
                 ('shape', {'unreviewed': 0}, 'protected_tcp_gate_unavailable')]
        for label, changed, reason in cases:
            stack, root, manifest, _, values, _, _ = self.scenario()
            with stack, self.subTest(label=label):
                R.idle_gates(manifest)
                values.update(changed)
                with self.assertRaisesRegex(R.GuardError, reason):
                    R.tcp_gate(manifest, {})
                self.assertIsNone(R._idle_authorization)
                self.assertFalse((root / 'last-user-authorized-tcp-exception.json').exists())
        stack, root, manifest, _, _, controls, _ = self.scenario()
        with stack:
            R.idle_gates(manifest)
            controls['tcpReadFailure'] = True
            with self.assertRaisesRegex(R.GuardError, 'protected_tcp_gate_unavailable'):
                R.tcp_gate(manifest, {})
            self.assertFalse((root / 'last-user-authorized-tcp-exception.json').exists())

    def test_foreign_owner_new_writer_and_any_recovery_still_require_zero_tcp(self):
        for mode in ('foreign', 'new', 'recovery'):
            current = container() if mode == 'recovery' else container('c'*64, 'sha256:'+'d'*64)
            stack, root, manifest, _, _, _, _ = self.scenario(current=current)
            progress = {'backend': {'id': current['Id'], 'image': current['Image'], 'kind': 'new'}} if mode == 'new' else {}
            reason = 'tcp_container_owner_changed' if mode == 'foreign' else 'protected_user_work_cutover_deferred'
            with stack, self.subTest(mode=mode):
                R.idle_gates(manifest)
                with self.assertRaisesRegex(R.GuardError, reason):
                    R.tcp_gate(manifest, progress, recovery=mode == 'recovery')
                self.assertFalse((root / 'last-user-authorized-tcp-exception.json').exists())

    def test_original_signature_change_after_normal_tcp_validation_still_blocks_exception(self):
        stack, root, manifest, _, _, _, _ = self.scenario()
        with stack:
            R.idle_gates(manifest)
            changed = container();changed['State']['StartedAt'] = '2026-11-04T00:00:00Z'
            with patch.object(R, 'inspect', return_value=changed), \
                 self.assertRaisesRegex(R.GuardError, 'authorized_tcp_original_owner_changed'):
                R.tcp_gate(manifest, {})
            self.assertFalse((root / 'last-user-authorized-tcp-exception.json').exists())


if __name__ == '__main__':
    unittest.main()
