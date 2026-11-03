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


_spec = importlib.util.spec_from_file_location('cn_device_status_release_under_test', Path(__file__).with_name('release_cn_device_status.py'))
R = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = R
_spec.loader.exec_module(R)
REPO = Path(__file__).resolve().parents[1]


def container(container_id=None, image=None):
    cid = container_id or R.BASES['backend'][0]
    return {'Id': cid, 'Image': image or R.BASES['backend'][1], 'RestartCount': 0,
            'Config': {'Image': image or R.BASES['backend'][1], 'Env': ['A=synthetic'], 'Labels': {}, 'Hostname': cid[:12]},
            'HostConfig': {'NetworkMode': 'compose_default'}, 'Mounts': [],
            'NetworkSettings': {'Networks': {'compose_default': {'IPAddress': '192.0.2.2', 'Aliases': ['backend', cid[:12]]}}},
            'State': {'Running': True, 'StartedAt': '2026-10-31T16:51:34.293214151Z', 'Pid': 42,
                      'Status': 'running', 'Restarting': False, 'Dead': False, 'Paused': False,
                      'Health': {'Status': 'healthy'}}}


def scope_plan():
    live = R.read_json(REPO / 'releases/20261102.1/cn/backend-runtime-manifest.json')
    image = R.read_json(REPO / 'releases/cn-20261101.1/backend-runtime-manifest.json')
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
        orphanAnswerContext=R.P.expected_orphan_context(plan['baselines']['backend']),
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

    def test_only_live232_plus_reviewed_four_files_and_hot_manifest_rollback(self):
        plan = scope_plan()
        R.check_candidate_scope(plan)
        self.assertEqual(len(plan['baselines']['backend']['inventory']), 232)
        self.assertEqual(len(plan['candidates']['backend']['inventory']), 233)
        self.assertEqual(len(R.APPROVED_BACKEND_SHA256), 4)
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
                del plan['candidates']['backend']['inventory'][R.TIMING_PATH]
            with self.subTest(mutation=mutation), self.assertRaisesRegex(R.GuardError, 'backend_input_set_changed'):
                R.check_candidate_scope(plan)

    def test_every_reviewed_source_is_hard_pinned(self):
        for name in R.APPROVED_BACKEND_SHA256:
            plan = scope_plan()
            plan['candidates']['backend']['inventory'][name] = R.digest(b'unreviewed')
            with self.subTest(path=name), self.assertRaisesRegex(R.GuardError, 'unreviewed_device_status_source'):
                R.check_candidate_scope(plan)

    def test_rollback_cannot_revert_download_manifest_or_use_naked_base(self):
        for mutation in ('manifest', 'image', 'extra'):
            plan = scope_plan()
            if mutation == 'manifest':
                plan['candidates']['backendRollback']['inventory'] = plan['baselines']['backend']['imageInventory']
            elif mutation == 'image':
                plan['candidates']['backendRollback']['image'] = R.BASES['backend'][1]
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
            with patch.object(R, 'ROOT', root), patch.object(R, 'inspect', return_value=image), \
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
            with patch.object(R, 'ROOT', root), patch.object(R, 'inspect', return_value=image), \
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
                 patch.object(R, 'runtime_contract', return_value=plan['runtimeBefore']):
                R.verify_runtime(manifest, plan, {'backend': {'kind': 'new'}}, final=True)
                original.assert_called_once()
            with patch.object(R.M, 'verify_runtime'), patch.object(R, 'inventory', return_value={}), \
                 self.assertRaisesRegex(R.GuardError, 'non_target_web_files_changed'):
                R.verify_runtime(manifest, plan, {})
            with patch.object(R.M, 'verify_runtime'), patch.object(R, 'inventory', return_value=plan['webInventory']), \
                 patch.object(R, 'runtime_contract', return_value={}), self.assertRaisesRegex(R.GuardError, 'runtime_dependencies_changed'):
                R.verify_runtime(manifest, plan, {})


if __name__ == '__main__':
    unittest.main()
