"""Synthetic release-controller checks; no Docker, SSH, users or providers."""
from copy import deepcopy
from contextlib import ExitStack
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('cn_mock_release_under_test', Path(__file__).with_name('release_cn_mock.py'))
R = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = R
spec.loader.exec_module(R)


def container(container_id=None, image=None):
    cid = container_id or R.BASES['backend'][0]
    return {'Id': cid, 'Image': image or R.BASES['backend'][1], 'RestartCount': 0,
            'Config': {'Image': image or R.BASES['backend'][1], 'Env': ['A=synthetic'], 'Labels': {}, 'Hostname': cid[:12]},
            'HostConfig': {'NetworkMode': 'compose_default'}, 'Mounts': [],
            'NetworkSettings': {'Networks': {'compose_default': {'IPAddress': '192.0.2.2', 'Aliases': ['backend', cid[:12]]}}},
            'State': {'Running': True, 'StartedAt': '2026-10-28T16:54:25.131951115Z', 'Pid': 42,
                      'Status': 'running', 'Restarting': False, 'Dead': False, 'Paused': False,
                      'Health': {'Status': 'healthy'}}}


def scope_plan():
    sha = R.digest(b'original')
    backend = {'apps/backend/app/main.py': sha, 'ai/prompts/current.md': sha, 'apps/backend/pyproject.toml': sha}
    backend.update({name: sha for name in R.BACKEND_ALLOWED if not name.endswith('/mock_interview_diagnostics.py')})
    settings_sha = R.digest(b'unchanged-effective-settings')
    web = {'index.html': sha, 'guide.html': sha, 'privacy.html': sha, 'terms.html': sha,
           'offersteady-build.json': sha, 'seo/pricing.html': sha, 'assets/existing-12345678.js': sha}
    new = dict(web, **{'index.html': R.digest(b'new-html'), 'assets/current-23456789.js': R.digest(b'new')})
    return {'baselines': {'backend': {'inventory': backend, 'settingsSha256': settings_sha}, 'web': {'inventory': web}},
            'candidates': {'backend': {'image': 'sha256:' + 'a' * 64, 'inventory': backend | R.APPROVED_BACKEND_SHA256, 'settingsSha256': settings_sha},
                           'web': {'image': 'sha256:' + 'b' * 64, 'inventory': new},
                           'webRollback': {'image': 'sha256:' + 'c' * 64, 'inventory': web | {'assets/current-23456789.js': R.digest(b'new')}}}}


def frozen_plan(root):
    """Freeze only public controller/support bytes into a synthetic directory."""
    plan = scope_plan()
    for service, (container_id, image) in R.BASES.items():
        plan['baselines'][service].update(id=container_id, image=image,
            startedAt='2026-10-28T16:54:25.131951115Z')
    prefix = 'release_support/cn_upload20m_model1017_20261021_r2/'
    files = {Path(R.__file__).name, 'release_cn_upload20m_model1017_v2.py', prefix + 'base_helpers.py',
             *(prefix + name for name in (*R.GATES, R.TCP_GATE))}
    plan['supportFiles'] = {}
    for name in files:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        data = (Path(R.__file__).parent / name).read_bytes()
        path.write_bytes(data)
        plan['supportFiles'][name] = R.digest(data)
    probe = b'print("synthetic probe, never executed")\n'
    result = json.dumps({'passed': True, 'image': plan['candidates']['backend']['image']}).encode()
    (root / 'candidate-probe.py').write_bytes(probe)
    (root / 'candidate-probe-result.json').write_bytes(result)
    plan.update(releaseId=R.RELEASE, financialAnchorMs=R.FINANCIAL_ANCHOR_MS,
                openapiBefore={}, nonTargets={},
                nginxInputs={'/etc/nginx/nginx.conf': R.digest(b'unchanged-nginx'),
                             '/etc/nginx/conf.d/default.conf': R.digest(b'unchanged-vhost')},
                orphanAnswerContext=R.P.expected_orphan_context(plan['baselines']['backend']),
                candidateProbe={'scriptSha256': R.digest(probe), 'resultSha256': R.digest(result)})
    return plan


class FrozenPlanTests(unittest.TestCase):
    def tearDown(self):
        R.bind_primitives()

    def check(self, plan, root):
        (root / 'input.json').write_text(json.dumps(plan))
        with patch.object(R, 'ROOT', root):
            return R.check_plan()

    def test_fully_frozen_synthetic_release_plan_passes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plan = frozen_plan(root)
            self.assertEqual(self.check(plan, root), plan)

    def test_financial_anchor_cannot_be_changed_rebased_or_mistyped(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            original = frozen_plan(root)
            self.assertEqual(R.FINANCIAL_ANCHOR_MS, 1792600214792)
            for value in (True, str(R.FINANCIAL_ANCHOR_MS), -1, 0,
                          R.FINANCIAL_ANCHOR_MS + 1,
                          original['orphanAnswerContext']['baselineBackendStartedAtMs']):
                plan = deepcopy(original)
                plan['financialAnchorMs'] = value
                with self.subTest(value=value), self.assertRaisesRegex(R.GuardError, 'financial_anchor_invalid'):
                    self.check(plan, root)

    def test_current_owner_anchor_remains_independently_frozen(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            original = frozen_plan(root)
            for field, value in (('baselineBackendId', 'foreign-owner'),
                                 ('baselineBackendStartedAtMs', R.FINANCIAL_ANCHOR_MS),
                                 ('baselineBackendStartedAt', '2026-10-21T16:30:14.792888863Z')):
                plan = deepcopy(original)
                plan['orphanAnswerContext'][field] = value
                with self.subTest(field=field), self.assertRaisesRegex(R.GuardError, 'original_process_anchor_drift'):
                    self.check(plan, root)

    def test_frozen_support_and_probe_bytes_cannot_change(self):
        for name, reason in (('release_cn_mock.py', 'release_controller_drift'),
                             ('candidate-probe.py', 'candidate_probe_drift'),
                             ('candidate-probe-result.json', 'candidate_probe_drift')):
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                plan = frozen_plan(root)
                (root / name).write_bytes(b'unreviewed replacement')
                with self.subTest(path=name), self.assertRaisesRegex(R.GuardError, reason):
                    self.check(plan, root)


class CandidatePolicyTests(unittest.TestCase):
    def test_incremental_scope_keeps_original_chunks_and_adds_compatible_rollback(self):
        R.check_candidate_scope(scope_plan())

    def test_old_asset_or_public_content_cannot_be_replaced_by_self_consistent_hashes(self):
        for name in ('assets/existing-12345678.js', 'seo/pricing.html'):
            p = scope_plan()
            p['candidates']['web']['inventory'][name] = R.digest(b'unapproved')
            with self.subTest(path=name), self.assertRaisesRegex(R.GuardError, 'unapproved_web_input_changed'):
                R.check_candidate_scope(p)

    def test_only_approved_backend_files_change(self):
        p = scope_plan()
        p['candidates']['backend']['inventory']['ai/prompts/current.md'] = R.digest(b'unapproved')
        with self.assertRaisesRegex(R.GuardError, 'unapproved_backend_input_changed'):
            R.check_candidate_scope(p)
        p = scope_plan()
        p['candidates']['backend']['inventory']['apps/backend/app/services/billing.py'] = R.digest(b'unsolicited')
        with self.assertRaisesRegex(R.GuardError, 'backend_input_set_changed'):
            R.check_candidate_scope(p)

    def test_old_assets_cannot_be_deleted(self):
        p = scope_plan()
        del p['candidates']['web']['inventory']['assets/existing-12345678.js']
        with self.assertRaisesRegex(R.GuardError, 'unapproved_web_input_changed'):
            R.check_candidate_scope(p)

    def test_new_assets_must_stay_in_public_asset_scope(self):
        for name in ('unexpected.html', 'assets/../secret.js', '/absolute.js', 'assets/nested/chunk.js'):
            p = scope_plan()
            p['candidates']['web']['inventory'][name] = R.digest(b'new')
            with self.subTest(path=name), self.assertRaisesRegex(R.GuardError, 'new_asset_scope_changed'):
                R.check_candidate_scope(p)

    def test_rollback_needs_both_exact_baseline_and_all_new_chunks(self):
        for mutation in ('missing-new', 'changed-old', 'extra'):
            p = scope_plan()
            files = p['candidates']['webRollback']['inventory']
            if mutation == 'missing-new':
                del files['assets/current-23456789.js']
            elif mutation == 'changed-old':
                files['index.html'] = R.digest(b'wrong')
            else:
                files['unapproved.html'] = R.digest(b'wrong')
            with self.subTest(mutation=mutation), self.assertRaisesRegex(R.GuardError, 'compatibility_rollback_inventory_changed'):
                R.check_candidate_scope(p)

    def test_worker_or_global_cannot_be_added_as_target(self):
        p = scope_plan()
        p['candidates']['material-worker'] = deepcopy(p['candidates']['backend'])
        with self.assertRaisesRegex(R.GuardError, 'candidate_components_changed'):
            R.check_candidate_scope(p)

    def test_every_effective_setting_is_preserved_for_new_and_rollback(self):
        baseline = {'product_edition': 'cn', 'environment': 'production', 'chat_quick_model': 'unchanged',
                    'cn_hot_database_pool_enabled': False, 'cn_hot_database_pool_max_size': 4,
                    'cn_hot_database_pool_max_waiting': 16, 'cn_hot_database_pool_timeout_seconds': 3.0,
                    'arbitrary_existing_setting': 'must-also-be-preserved'}
        for kind in ('baseline', 'new', 'rollback'):
            with self.subTest(kind=kind):
                expected = R.expected_settings(baseline, kind)
                self.assertEqual(expected, baseline)
                self.assertIsNot(expected, baseline)
        self.assertEqual(R.expected_settings({}, 'new'), {})

    def test_candidate_settings_digest_must_equal_actual_baseline(self):
        p = scope_plan()
        p['candidates']['backend']['settingsSha256'] = R.digest(b'changed-setting')
        with self.assertRaisesRegex(R.GuardError, 'candidate_settings_scope_changed'):
            R.check_candidate_scope(p)

    def test_exactly_five_reviewed_backend_files_have_fixed_source_hashes(self):
        self.assertEqual(set(R.APPROVED_BACKEND_SHA256), R.BACKEND_ALLOWED)
        self.assertEqual(len(R.BACKEND_ALLOWED), 5)
        self.assertEqual(R.BACKEND_ALLOWED, {
            'apps/backend/app/services/mock_interview_runtime.py',
            'apps/backend/app/modules/mock_interview.py',
            'apps/backend/app/services/mock_interview_generation.py',
            'apps/backend/app/services/mock_interview_jobs.py',
            'apps/backend/app/services/mock_interview_diagnostics.py',
        })
        for name in R.BACKEND_ALLOWED:
            p = scope_plan()
            p['candidates']['backend']['inventory'][name] = R.digest(b'unreviewed-replacement')
            with self.subTest(path=name), self.assertRaisesRegex(R.GuardError, 'unreviewed_mock_backend_source'):
                R.check_candidate_scope(p)

    def test_only_new_diagnostics_file_can_extend_backend_input_set(self):
        for extra in ('apps/backend/app/core/config.py', 'apps/backend/app/services/mock_interview_tts.py',
                      'apps/backend/app/services/unrelated.py'):
            p = scope_plan()
            p['candidates']['backend']['inventory'][extra] = R.digest(b'unapproved-addition')
            with self.subTest(path=extra), self.assertRaisesRegex(R.GuardError, 'backend_input_set_changed'):
                R.check_candidate_scope(p)
        p = scope_plan()
        del p['candidates']['backend']['inventory']['apps/backend/app/services/mock_interview_diagnostics.py']
        with self.assertRaisesRegex(R.GuardError, 'backend_input_set_changed'):
            R.check_candidate_scope(p)

    def test_html_only_resource_url_normalization_preserves_semantics(self):
        before = b'<h1>Existing</h1><script src="/assets/main-12345678.js"></script>'
        resource = before.replace(b'main-12345678', b'main-23456789')
        self.assertEqual(R.normalize_html_resources(before), R.normalize_html_resources(resource))
        self.assertNotEqual(R.normalize_html_resources(before), R.normalize_html_resources(resource.replace(b'Existing', b'Changed')))

    def test_framework_is_bound_to_this_release_without_model_overrides(self):
        R.bind_primitives()
        self.assertEqual(R.P.ROOT, R.ROOT)
        self.assertEqual(R.H.ROOT, R.ROOT)
        self.assertEqual(set(R.P.BASES), {'backend', 'web'})
        before = container()
        self.assertEqual(R.P.expected_environment(before, 'backend', 'new'), {'A': 'synthetic'})
        rendered = {'services': {'backend': {'image': 'old', 'environment': {'A': 'same'}}, 'web': {'image': 'other'}}}
        expected = deepcopy(rendered)
        expected['services']['backend']['image'] = 'new'
        self.assertEqual(R.P.expected_render(rendered, 'backend', 'new', 'new'), expected)


class GateTests(unittest.TestCase):
    def tearDown(self):
        R.bind_primitives()

    def run_gate(self, path, raw, exit_code=0):
        response = subprocess.CompletedProcess([], exit_code, json.dumps(raw).encode(), b'')
        with patch.object(R, 'anchored_gate_command', return_value=['synthetic-readonly-gate']), patch.object(R.P, 'GATES', (path,)), \
             patch.object(R.P.subprocess, 'run', return_value=response), patch.object(R.P, 'save'):
            return R.idle_gates({})

    def test_live_interview_and_stale_metadata_fail_closed(self):
        raw = {'atMs': 1, 'sampleAgeMs': 5, 'liveInterviews': 0, 'recentPreparing': 0, 'activeInterviews': 0,
               'activeWebSessions': 0, 'activeAudioStreams': 0}
        self.assertEqual(len(self.run_gate('legacy-gates/idle_gate.py', raw)), 1)
        for key in ('liveInterviews', 'recentPreparing', 'activeInterviews', 'activeWebSessions', 'activeAudioStreams'):
            with self.subTest(field=key), self.assertRaisesRegex(R.GuardError, 'protected_user_work_cutover_deferred'):
                self.run_gate('legacy-gates/idle_gate.py', raw | {key: 1}, 75)
        with self.assertRaisesRegex(R.GuardError, 'protected_work_gate_unavailable'):
            self.run_gate('legacy-gates/idle_gate.py', raw | {'sampleAgeMs': 90000}, 75)

    def test_every_protected_preparation_task_financial_or_unknown_count_blocks(self):
        for path in ('extra_idle_gate.py', 'active_work_gate.py', 'resume_optimizer_idle_gate.py', 'financial_idle_gate.py'):
            with patch.object(R.H, 'ROOT', R.SUPPORT):
                protected, informational = R.H.gate_contract(path)
            zero = dict.fromkeys(protected | informational, 0)
            self.assertEqual(len(self.run_gate(path, zero)), 1)
            for name in protected:
                with self.subTest(gate=path, field=name), self.assertRaises(R.GuardError):
                    self.run_gate(path, zero | {name: 1}, 75)
        self.assertNotIn('--allow-existing-preparation-page', Path(R.__file__).read_text())

    def test_unknown_mock_phase_blocks(self):
        self.assertEqual(len(self.run_gate('legacy-gates/readiness-idle.py', {'mockPhases': {'completed': 1}})), 1)
        for phase in ('future-phase', 'listening', 'generating_report'):
            with self.subTest(phase=phase), self.assertRaises(R.GuardError):
                self.run_gate('legacy-gates/readiness-idle.py', {'mockPhases': {phase: 1}}, 75)

    def test_financial_anchor_uses_original_process_even_after_candidate_switch(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / 'backend').mkdir()
            before = container()
            (root / 'backend/container-before.json').write_text(json.dumps(before))
            context = {'baselineBackendId': before['Id'], 'baselineBackendStartedAt': before['State']['StartedAt'],
                       'baselineBackendStartedAtMs': R.P.docker_started_at_ms(before['State']['StartedAt'])}
            with patch.object(R.P, 'ROOT', root):
                args = R.P.gate_command({'orphanAnswerContext': context})
            self.assertIn('OFFERSTEADY_RELEASE_ORIGINAL_BACKEND_STARTED_AT_MS=' + str(R.FINANCIAL_ANCHOR_MS), args)
            self.assertNotIn('OFFERSTEADY_RELEASE_ORIGINAL_BACKEND_STARTED_AT_MS=' + str(context['baselineBackendStartedAtMs']), args)
            self.assertLess(R.FINANCIAL_ANCHOR_MS, context['baselineBackendStartedAtMs'])
            self.assertIn(R.BASES['backend'][1], args)
            self.assertIn('--read-only', args)
            self.assertNotIn('--network=host', args)

    def test_financial_wrapper_requires_current_original_owner_before_reanchoring(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'backend').mkdir()
            before = container()
            (root / 'backend/container-before.json').write_text(json.dumps(before))
            context = {'baselineBackendId': before['Id'], 'baselineBackendStartedAt': before['State']['StartedAt'],
                       'baselineBackendStartedAtMs': R.P.docker_started_at_ms(before['State']['StartedAt'])}
            with patch.object(R.P, 'ROOT', root):
                for field, value in (('baselineBackendId', 'foreign-owner'),
                                     ('baselineBackendStartedAtMs', R.FINANCIAL_ANCHOR_MS),
                                     ('baselineBackendStartedAt', '2026-10-21T16:30:14.792888863Z')):
                    changed = context | {field: value}
                    with self.subTest(field=field), self.assertRaisesRegex(R.GuardError, 'original_process_snapshot_anchor_drift'):
                        R.anchored_gate_command({'orphanAnswerContext': changed})

    def test_financial_wrapper_rejects_missing_duplicate_or_forward_anchor(self):
        current_anchor = R.P.docker_started_at_ms(container()['State']['StartedAt'])
        previous = 'OFFERSTEADY_RELEASE_ORIGINAL_BACKEND_STARTED_AT_MS=' + str(current_anchor)
        manifest = {'orphanAnswerContext': {'baselineBackendStartedAtMs': current_anchor}}
        for args in ([], ['docker', previous, previous]):
            with patch.object(R, '_ORIGINAL_GATE_COMMAND', return_value=args), self.subTest(args=args), \
                 self.assertRaisesRegex(R.GuardError, 'financial_anchor_invalid'):
                R.anchored_gate_command(manifest)
        earlier = R.FINANCIAL_ANCHOR_MS - 1
        with patch.object(R, '_ORIGINAL_GATE_COMMAND', return_value=[
                'OFFERSTEADY_RELEASE_ORIGINAL_BACKEND_STARTED_AT_MS=' + str(earlier)]), \
             self.assertRaisesRegex(R.GuardError, 'financial_anchor_invalid'):
            R.anchored_gate_command({'orphanAnswerContext': {'baselineBackendStartedAtMs': earlier}})

    def tcp(self, values=None, *, code=0, progress=None, image=None):
        current = container(image=image)
        value = {'passed': True, 'atMs': int(time.time() * 1000), 'establishedPort8000': 0, 'tablesRead': 2,
                 'scannedRows': 4, 'scope': 'container_tcp8000_established_only', 'networkNamespaceSha256': 'synthetic-namespace'}
        value.update(values or {})
        response = subprocess.CompletedProcess([], code, json.dumps(value).encode(), b'')
        with patch.object(R, 'inspect', return_value=current), patch.object(R, 'read_json', return_value=current), \
             patch.object(R.H, 'running_process_identity', return_value=('same',)), patch.object(R.H, 'host_network_namespace', return_value='synthetic-namespace'), \
             patch.object(R.subprocess, 'run', return_value=response), patch.object(R, 'save'):
            R.tcp_gate({}, progress or {})

    def test_tcp_busy_stale_wrong_namespace_or_malformed_count_blocks(self):
        self.tcp()
        with self.assertRaisesRegex(R.GuardError, 'protected_user_work_cutover_deferred'):
            self.tcp({'establishedPort8000': 1})
        for value in ({'atMs': int(time.time() * 1000) - 11000}, {'networkNamespaceSha256': 'other'},
                      {'establishedPort8000': True}, {'tablesRead': 1}, {'scope': 'all-host-traffic'}):
            with self.subTest(value=value), self.assertRaisesRegex(R.GuardError, 'protected_tcp_gate_unavailable'):
                self.tcp(value)

    def test_tcp_accepts_journaled_candidate_not_only_baseline_image(self):
        image = 'sha256:' + 'a' * 64
        self.tcp(progress={'backend': {'id': R.BASES['backend'][0], 'image': image}}, image=image)

    def test_stopped_baseline_tcp_recovery_requires_original_static_owner(self):
        before = container()
        stopped = deepcopy(before)
        stopped['State'].update(Running=False, Pid=0, Status='exited')
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / 'backend').mkdir()
            (root / 'backend/container-before.json').write_text(json.dumps(before))
            with patch.object(R, 'ROOT', root), patch.object(R, 'inspect', return_value=stopped), patch.object(R, 'save') as save:
                R.tcp_gate({}, {}, recovery=True)
                self.assertEqual(save.call_args.args[1], {'passed': True, 'method': 'stoppedProcessProof'})
                with self.assertRaises(R.GuardError):
                    R.tcp_gate({}, {}, recovery=False)
                stopped['Config']['Env'] = ['A=foreign-change']
                with self.assertRaisesRegex(R.GuardError, 'baseline_stopped_process_unproven'):
                    R.tcp_gate({}, {}, recovery=True)

    def test_stopped_owned_candidate_tcp_recovery_never_uses_unjournaled_identity(self):
        candidate = container('a' * 64, 'sha256:' + 'b' * 64)
        candidate['State'].update(Running=False, Pid=0, Status='exited')
        progress = {'backend': {'id': candidate['Id'], 'image': candidate['Image'], 'kind': 'new'}}
        with patch.object(R, 'inspect', return_value=candidate), patch.object(R, 'read_json', return_value=container()), patch.object(R, 'save'):
            R.tcp_gate({}, progress, recovery=True)
            with self.assertRaisesRegex(R.GuardError, 'tcp_container_owner_changed'):
                R.tcp_gate({}, {}, recovery=True)
            with self.assertRaisesRegex(R.GuardError, 'stopped_process_proof_unavailable'):
                R.tcp_gate({}, progress, recovery=False)


class MutationTests(unittest.TestCase):
    def deployment_patches(self, root, *, progress=None):
        stack = ExitStack()
        stack.enter_context(patch.object(R, 'ROOT', root))
        stack.enter_context(patch.object(R, 'check_plan', return_value=scope_plan()))
        stack.enter_context(patch.object(R, 'load_state', return_value=({'targets': {'backend': {'newImage': 'b'}, 'web': {'newImage': 'w'}}}, progress or {})))
        mocks = {}
        for name in ('verify_runtime', 'idle_gates', 'tcp_gate', 'public_checks', 'save', 'emit', 'check_files', 'targets_owned'):
            mocks[name] = stack.enter_context(patch.object(R, name))
        return stack, mocks

    def test_preflight_never_mutates_and_active_work_defers_before_switch(self):
        with tempfile.TemporaryDirectory() as d:
            stack, mocks = self.deployment_patches(Path(d))
            with stack, patch.object(R, 'switch') as switch:
                R.deploy(preflight=True)
                switch.assert_not_called()
                mocks['idle_gates'].assert_called_once()
                mocks['tcp_gate'].assert_called_once()
            stack, mocks = self.deployment_patches(Path(d))
            mocks['idle_gates'].side_effect = R.GuardError('protected_user_work_cutover_deferred')
            with stack, patch.object(R, 'switch') as switch:
                with self.assertRaisesRegex(R.GuardError, 'protected_user_work_cutover_deferred'):
                    R.deploy()
                switch.assert_not_called()

    def test_completed_release_only_verifies_without_gates_or_restart(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / 'deployed.json').write_text('{}')
            stack, mocks = self.deployment_patches(root)
            with stack, patch.object(R, 'verify') as verify, patch.object(R, 'switch') as switch:
                R.deploy()
                verify.assert_called_once()
                switch.assert_not_called()
                mocks['idle_gates'].assert_not_called()

    def test_only_backend_and_web_are_switched(self):
        with tempfile.TemporaryDirectory() as d:
            stack, _ = self.deployment_patches(Path(d))
            with stack, patch.object(R, 'switch') as switch:
                R.deploy()
                self.assertEqual([(c.args[3], c.args[4]) for c in switch.call_args_list], [('backend', 'new'), ('web', 'new')])

    def test_partial_release_busy_does_not_override_user_or_roll_back_active_work(self):
        with tempfile.TemporaryDirectory() as d:
            stack, _ = self.deployment_patches(Path(d), progress={'backend': {'kind': 'new'}})
            with stack, patch.object(R, 'switch', side_effect=R.GuardError('protected_user_work_cutover_deferred')) as switch, patch.object(R, 'rollback') as rollback:
                with self.assertRaisesRegex(R.GuardError, 'protected_user_work_cutover_deferred'):
                    R.deploy()
                self.assertEqual(switch.call_args.args[3], 'web')
                rollback.assert_not_called()

    def test_foreign_drift_stops_without_overwriting_owner(self):
        for reason in ('non_target_container_changed', 'release_container_owner_changed', 'runtime_source_or_static_drift', 'release_controller_drift'):
            with tempfile.TemporaryDirectory() as d:
                stack, _ = self.deployment_patches(Path(d))
                with stack, patch.object(R, 'switch', side_effect=R.GuardError(reason)), patch.object(R, 'rollback') as rollback:
                    with self.subTest(reason=reason), self.assertRaisesRegex(R.GuardError, reason):
                        R.deploy()
                    rollback.assert_not_called()

    def test_owned_health_failure_attempts_rollback_and_reports_actual_result(self):
        for failure in (False, True):
            with tempfile.TemporaryDirectory() as d:
                stack, mocks = self.deployment_patches(Path(d))
                rollback_error = R.GuardError('protected_user_work_cutover_deferred') if failure else None
                with stack, patch.object(R, 'switch', side_effect=R.GuardError('target_health_failed')), patch.object(R, 'rollback', side_effect=rollback_error):
                    suffix = 'needs_attention' if failure else 'succeeded'
                    with self.subTest(failed=failure), self.assertRaisesRegex(R.GuardError, 'cutover_failed_rollback_' + suffix):
                        R.deploy()
                    self.assertEqual(mocks['save'].call_args.args[1]['rollbackSucceeded'], not failure)

    def test_rollback_only_reverts_owned_targets_and_checks_success(self):
        with tempfile.TemporaryDirectory() as d:
            progress = {'backend': {'kind': 'new'}, 'web': {'kind': 'new'}}
            stack, mocks = self.deployment_patches(Path(d), progress=progress)
            def reverted(manifest, plan, current, service, kind):
                current[service]['kind'] = kind
            with stack, patch.object(R, 'switch', side_effect=reverted) as switch:
                R.rollback()
                self.assertEqual([(c.args[3], c.args[4]) for c in switch.call_args_list], [('web', 'rollback'), ('backend', 'rollback')])
                mocks['public_checks'].assert_called_once()
                self.assertTrue(mocks['save'].call_args.args[1]['restored'])

    def baseline_recovery(self, root, *, busy=False, start_error=False, foreign=False):
        active = {s: container(*R.BASES[s]) for s in R.BASES}
        manifest = {'targets': {s: {'container': 'compose-' + s + '-1'} for s in R.BASES}}
        for service in R.BASES:
            (root / service).mkdir()
            (root / service / 'container-before.json').write_text(json.dumps(active[service]))
        active['backend']['State'].update(Running=False, Pid=0, Status='exited')
        if foreign:
            active['backend']['Config']['Env'] = ['A=foreign-change']
        def observed(name):
            return next(c for s, c in active.items() if name in (c['Id'], 'compose-' + s + '-1'))
        commands = []
        def command(args, **kwargs):
            commands.append(args)
            if args[:2] == ['docker', 'start']:
                if start_error:
                    raise RuntimeError('synthetic Docker start failure')
                active['backend']['State'].update(Running=True, Pid=43, Status='running', StartedAt='2026-10-29T00:00:00.000000000Z')
            return subprocess.CompletedProcess(args, 0, b'', b'')
        stack = ExitStack()
        stack.enter_context(patch.object(R, 'ROOT', root))
        stack.enter_context(patch.object(R, 'check_plan', return_value=scope_plan()))
        stack.enter_context(patch.object(R, 'load_state', return_value=(manifest, {})))
        stack.enter_context(patch.object(R, 'check_files'))
        stack.enter_context(patch.object(R, 'inspect', side_effect=observed))
        stack.enter_context(patch.object(R.P, 'inspect', side_effect=observed))
        stack.enter_context(patch.object(R, 'run', side_effect=command))
        gates = stack.enter_context(patch.object(R, 'idle_gates', side_effect=R.GuardError('protected_user_work_cutover_deferred') if busy else None))
        stack.enter_context(patch.object(R, 'tcp_gate'))
        verify = stack.enter_context(patch.object(R, 'verify_runtime'))
        public = stack.enter_context(patch.object(R, 'public_checks'))
        stack.enter_context(patch.object(R, 'emit'))
        return stack, active, commands, gates, verify, public

    def test_stopped_original_is_restored_only_after_full_gates_and_public_verification(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            stack, active, commands, gates, verify, public = self.baseline_recovery(root)
            with stack:
                R.rollback()
            self.assertEqual(commands, [['docker', 'start', R.BASES['backend'][0]]])
            self.assertTrue(active['backend']['State']['Running'])
            gates.assert_called_once()
            verify.assert_called_once()
            public.assert_called_once()
            self.assertTrue(json.loads((root / 'rollback-result.json').read_text())['restored'])
            self.assertEqual(json.loads((root / 'backend/container-before.json').read_text())['State']['StartedAt'], '2026-10-28T16:54:25.131951115Z')
            self.assertIn('backend', json.loads((root / 'baseline-restorations.json').read_text()))

    def test_stopped_baseline_with_active_work_or_foreign_config_is_never_started(self):
        for busy, foreign in ((True, False), (False, True)):
            with tempfile.TemporaryDirectory() as d:
                root = Path(d)
                stack, _, commands, _, _, public = self.baseline_recovery(root, busy=busy, foreign=foreign)
                with stack, self.subTest(busy=busy, foreign=foreign), self.assertRaises(R.GuardError):
                    R.rollback()
                self.assertEqual(commands, [])
                public.assert_not_called()
                self.assertFalse((root / 'rollback-result.json').exists())

    def test_failed_original_start_is_not_reported_restored(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            stack, active, commands, _, verify, public = self.baseline_recovery(root, start_error=True)
            with stack, self.assertRaisesRegex(RuntimeError, 'synthetic Docker start failure'):
                R.rollback()
            self.assertFalse(active['backend']['State']['Running'])
            self.assertEqual(commands, [['docker', 'start', R.BASES['backend'][0]]])
            verify.assert_not_called()
            public.assert_not_called()
            self.assertFalse((root / 'rollback-result.json').exists())


if __name__ == '__main__':
    unittest.main(verbosity=2)
