"""Synthetic release-boundary regression tests; never contact Docker or production."""
from copy import deepcopy
import importlib.util
import json
import io
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

spec=importlib.util.spec_from_file_location('cn_search_release',Path(__file__).with_name('release_cn_search_content.py'))
R=importlib.util.module_from_spec(spec);spec.loader.exec_module(R)


def container(identity='a'*64,image=R.BASE_IMAGE):
    return {'Id':identity,'Image':image,'RestartCount':0,
      'State':{'StartedAt':'2026-10-21T16:30:14.792888863Z','Running':True},
      'Config':{'Image':image,'Env':['A=value'],'Hostname':identity[:12],'Labels':{'app':'cn'},'Cmd':['nginx'],'User':''},
      'HostConfig':{'NetworkMode':'compose_default','Binds':None},'Mounts':[],
      'NetworkSettings':{'Networks':{'compose_default':{'Aliases':['web',identity,identity[:12]],'IPAMConfig':None}}}}


class ReleaseBoundaryTests(unittest.TestCase):
    @staticmethod
    def pricing():
        return {'catalog':[{'id':'pass-1','displayName':'合成一天会员','kind':'time_pass','priceCents':100,'catalogVersion':1,'durationDays':1,'knowledgeIndexAllowance':0}], 'rates':{k:1 for k in R.RATE_KEYS}}

    def test_public_catalog_normalization_and_fresh_mismatch(self):
        expected=self.pricing();billing={'catalog':[{**item,'published':True,'irrelevant':'not used'} for item in expected['catalog']],'rates':{**expected['rates'],'irrelevant':1}}
        self.assertEqual(R.normalized_pricing({'data':{'billing':billing}}),expected)
        class Response(io.BytesIO):status=200
        def response():return Response(json.dumps({'data':{'billing':billing}}).encode())
        with patch.object(R,'check_pricing_binding',return_value=expected),patch.object(R,'build_opener') as factory:
            factory.return_value.open.side_effect=lambda *args,**kwargs:response()
            R.fresh_pricing({}, {'pricing':{'fingerprint':R.pricing_fingerprint(expected)}})
            billing['catalog'][0]['priceCents']=101
            with self.assertRaisesRegex(R.GuardError,'public_catalog_changed'):R.fresh_pricing({}, {'pricing':{'fingerprint':R.pricing_fingerprint(expected)}})

    def test_strict_created_owner_labels(self):
        target={'frozenComposeFiles':['/private/compose.before'],'frozenEnvFiles':['/private/env.before'],'composeDirectory':'/opt/offersteady/current/infra/compose'}
        c=container();c['Config']['Labels'].update({'com.docker.compose.project':'compose','com.docker.compose.service':'web','com.docker.compose.project.config_files':','.join(target['frozenComposeFiles']+[str(R.ROOT/'web/new.compose.json')]),'com.docker.compose.project.environment_file':','.join(target['frozenEnvFiles']),'com.docker.compose.project.working_dir':target['composeDirectory']})
        R.owned_labels(c,target,'new')
        for field in ('com.docker.compose.project','com.docker.compose.service','com.docker.compose.project.config_files','com.docker.compose.project.environment_file','com.docker.compose.project.working_dir'):
            changed=deepcopy(c);changed['Config']['Labels'][field]='unrelated'
            with self.subTest(field=field),self.assertRaisesRegex(R.GuardError,'released_compose_owner_changed'):R.owned_labels(changed,target,'new')

    def test_stopped_baseline_is_not_false_success_when_restart_fails(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'prepared.private.json').write_text('{}');(root/'web').mkdir();(root/'web/container-before.json').write_text('{}')
            stopped=container(R.BASE_ID);stopped['State'].update(Running=False,Pid=0,Status='exited',Restarting=False,Dead=False,Paused=False)
            with patch.object(R,'ROOT',root),patch.object(R,'checked_plan',return_value=({},{})),patch.object(R,'current_kind',return_value=('baseline',stopped)),patch.object(R,'frozen_checks'),patch.object(R,'runtime_invariant'),patch.object(R,'gates'),patch.object(R,'run',side_effect=RuntimeError('synthetic docker start failure')) as run,patch.object(R,'public_checks') as checks,patch.object(R,'save') as save:
                with self.assertRaisesRegex(R.GuardError,'cutover_failed_rollback_needs_attention'):R.restore_after_failure({}, {}, {})
                run.assert_called_once_with(['docker','start',R.BASE_ID]);checks.assert_not_called();self.assertFalse(save.call_args.args[1]['rollbackSucceeded'])

    def test_owned_created_config_failure_records_progress_and_rolls_back(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'web').mkdir()
            target={'frozenComposeFiles':['/private/compose.before'],'frozenEnvFiles':['/private/env.before'],'composeDirectory':'/opt/offersteady/current/infra/compose'}
            state={'target':target,'newImage':'sha256:new','rollbackImage':'sha256:rollback'}
            before=container(R.BASE_ID);(root/'web/container-before.json').write_text(json.dumps(before));(root/'prepared.private.json').write_text(json.dumps(state))
            active=[before]; original_invariant=R.runtime_invariant
            def command(args,**kwargs):
                if args[:2]==['docker','compose']:
                    kind='rollback' if str(root/'web/rollback.compose.json') in args else 'new'
                    c=container(('c' if kind=='rollback' else 'b')*64,state[kind+'Image'])
                    c['Config']['Labels'].update({'com.docker.compose.project':'compose','com.docker.compose.service':'web','com.docker.compose.project.config_files':','.join(target['frozenComposeFiles']+[str(root/'web'/f'{kind}.compose.json')]),'com.docker.compose.project.environment_file':','.join(target['frozenEnvFiles']),'com.docker.compose.project.working_dir':target['composeDirectory']})
                    active[0]=c
                return subprocess.CompletedProcess(args,0,b'',b'')
            def invariant(old,new,image):
                if image=='sha256:new':raise R.GuardError('runtime_configuration_changed')
                original_invariant(old,new,image)
            def verified(*args,**kwargs):return 'baseline' if active[0]['Image']==R.BASE_IMAGE else 'rollback'
            with patch.object(R,'ROOT',root),patch.object(R,'checked_plan',return_value=({},{})),patch.object(R,'inspect',side_effect=lambda name:active[0]),patch.object(R,'run',side_effect=command),patch.object(R,'runtime_invariant',side_effect=invariant),patch.object(R,'verify_runtime',side_effect=verified),patch.object(R,'gates'),patch.object(R,'fresh_pricing'),patch.object(R,'frozen_checks'),patch.object(R,'public_checks'):
                with self.assertRaisesRegex(R.GuardError,'cutover_failed_rollback_succeeded'):R.deploy()
            self.assertEqual(json.loads((root/'progress.json').read_text())['kind'],'rollback')
            self.assertEqual(active[0]['Image'],'sha256:rollback')

    @staticmethod
    def exception_authorization():return {'allowExistingPreparationPage':True,'scope':'one-existing-preparation-page'}

    def extra_gate_counts(self):
        with patch.object(R.H,'ROOT',R.SUPPORT):protected,informational=R.H.gate_contract('extra_idle_gate.py')
        return {key:0 for key in protected|informational}

    def run_extra_gate(self,raw,flag,code=75):
        backend=container();plan={'authorization':self.exception_authorization(),'baseline':{'nonTargets':{'compose-backend-1':R.simple_signature(backend)}}}
        result=subprocess.CompletedProcess([],code,json.dumps(raw).encode(),b'')
        with patch.object(R,'ALLOW_EXISTING_PREPARATION_PAGE',flag),patch.object(R,'PREPARATION_EXCEPTION_APPLIED',False),patch.object(R,'inspect',return_value=backend),patch.object(R,'GATES',('extra_idle_gate.py',)),patch.object(R.subprocess,'run',return_value=result),patch.object(R,'save'):
            return R.gates(plan)

    def test_one_existing_preparation_page_requires_current_explicit_flag(self):
        raw=self.extra_gate_counts();raw['preparationPageLeases']=1
        with self.assertRaisesRegex(R.GuardError,'protected_user_work_cutover_deferred'):self.run_extra_gate(raw,False)
        records=self.run_extra_gate(raw,True)
        self.assertEqual(records[0]['counts'],raw)
        self.assertEqual(records[0]['counts']['preparationPageLeases'],1)
        self.assertTrue(records[0]['preparationOnlyExceptionApplied'])
        self.assertTrue(records[0]['authorization']['explicitAllowExistingPreparationPage'])

    def test_preparation_exception_never_covers_other_protected_or_unknown_work(self):
        raw=self.extra_gate_counts();raw['preparationPageLeases']=1
        for key in ('livePageLeases','mockPreparingProtected','mockListening','unfinishedChatTasks','unfinishedScreenshotTasks','unknownPageLeases','invalidRuntimeMetadata','metadataReadFailures'):
            blocked=dict(raw);blocked[key]=1
            with self.subTest(field=key),self.assertRaises(R.GuardError):self.run_extra_gate(blocked,True)
        with self.assertRaises(R.GuardError):self.run_extra_gate(dict(raw,preparationPageLeases=2),True)
        for code in (0,1,12):
            with self.subTest(exit=code),self.assertRaises(R.GuardError):self.run_extra_gate(raw,True,code)
        with patch.object(R,'ALLOW_EXISTING_PREPARATION_PAGE',True):
            self.assertFalse(R.preparation_only_exception('active_work_gate.py',{'recentAudioTracks':1},75,False,{'recentAudioTracks'}))
            self.assertFalse(R.preparation_only_exception('legacy-gates/idle_gate.py',{'recentPreparing':1},75,False,{'recentPreparing'}))
            self.assertFalse(R.preparation_only_exception('financial_idle_gate.py',{'pendingValidCheckoutOrders':1},75,False,{'pendingValidCheckoutOrders'}))

    def test_input_authorization_does_not_implicitly_enable_flag(self):
        p={'authorization':self.exception_authorization()}
        with patch.object(R,'ALLOW_EXISTING_PREPARATION_PAGE',False):
            R.validate_authorization(p);self.assertFalse(R.action_authorization(p)['explicitAllowExistingPreparationPage'])
        with patch.object(R,'ALLOW_EXISTING_PREPARATION_PAGE',True):
            with self.assertRaisesRegex(R.GuardError,'explicit_preparation_authorization_missing'):R.validate_authorization({})
            with self.assertRaisesRegex(R.GuardError,'release_authorization_scope_invalid'):R.validate_authorization({'authorization':{'allowExistingPreparationPage':True,'scope':'all-preparation-pages'}})

    def test_runtime_invariant_allows_only_image_container_and_compose_identity(self):
        before=container();after=container('b'*64,'sha256:new');after['Config']['Image']='sha256:new';after['Config']['Labels']['com.docker.compose.config-hash']='new'
        R.runtime_invariant(before,after,'sha256:new')
        for mutation in ('env','mount','command','network','label','host'):
            changed=deepcopy(after)
            if mutation=='env':changed['Config']['Env']=['A=different']
            elif mutation=='mount':changed['Mounts']=[{'Type':'bind','Source':'/different','Destination':'/app'}]
            elif mutation=='command':changed['Config']['Cmd']=['other']
            elif mutation=='network':changed['NetworkSettings']['Networks']['other']={}
            elif mutation=='label':changed['Config']['Labels']['app']='global'
            elif mutation=='host':changed['HostConfig']['Binds']=['unexpected']
            with self.subTest(mutation=mutation),self.assertRaises(R.GuardError):R.runtime_invariant(before,changed,'sha256:new')

    def test_financial_anchor_handles_docker_nanoseconds(self):
        self.assertEqual(R.started_ms('2026-10-21T16:30:14.792888863Z'),R.started_ms('2026-10-21T16:30:14.792888+00:00'))

    def test_current_owner_drift_never_replaced(self):
        with tempfile.TemporaryDirectory() as d,patch.object(R,'ROOT',Path(d)),patch.object(R,'inspect',return_value=container('x'*64)):
            with self.assertRaises(R.GuardError):R.current_kind({})

    def test_controller_rejects_symlink_payload(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'file').write_text('public');(root/'alias').symlink_to(root/'file')
            with self.assertRaises(R.GuardError):R.inventory_files(root)

    def gate(self,raw,code=0):
        backend=container();plan={'baseline':{'nonTargets':{'compose-backend-1':R.simple_signature(backend)}}}
        result=subprocess.CompletedProcess([],code,json.dumps(raw).encode(),b'')
        with patch.object(R,'inspect',return_value=backend),patch.object(R,'GATES',('legacy-gates/idle_gate.py',)),patch.object(R.subprocess,'run',return_value=result) as execute,patch.object(R,'save'):
            value=R.gates(plan)
            self.assertIn('OFFERSTEADY_RELEASE_ORIGINAL_BACKEND_STARTED_AT_MS=', ' '.join(execute.call_args.args[0]))
            return value

    def test_all_clear_gate_uses_readonly_existing_script(self):
        raw={'atMs':1,'sampleAgeMs':5,'liveInterviews':0,'recentPreparing':0,'activeInterviews':0,'activeWebSessions':0,'activeAudioStreams':0}
        self.assertEqual(len(self.gate(raw)),1)

    def test_active_user_defers_and_stale_or_unknown_metadata_fail_closed(self):
        raw={'atMs':1,'sampleAgeMs':5,'liveInterviews':0,'recentPreparing':0,'activeInterviews':0,'activeWebSessions':0,'activeAudioStreams':0}
        busy=dict(raw,liveInterviews=1)
        with self.assertRaisesRegex(R.GuardError,'protected_user_work_cutover_deferred'):self.gate(busy,75)
        for invalid in (dict(raw,sampleAgeMs=90000),dict(raw,extra=0),dict(raw,activeAudioStreams=None)):
            with self.assertRaisesRegex(R.GuardError,'protected_work_gate_unavailable'):self.gate(invalid,75)

    def test_non_target_drift_is_refused(self):
        before=container();expected=R.H.container_signature(before)
        changed=deepcopy(before);changed['RestartCount']=1
        state={'nonTargets':{'compose-backend-1':expected}}
        result=subprocess.CompletedProcess([],0,b'compose-web-1\ncompose-backend-1\n',b'')
        with patch.object(R,'run',return_value=result),patch.object(R,'inspect',return_value=changed):
            with self.assertRaisesRegex(R.GuardError,'non_target_changed'):R.check_non_targets(state)

    def test_completed_owned_release_never_restarts_or_repeats_gates(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'prepared.private.json').write_text('{}');(root/'deployed.json').write_text('{}')
            with patch.object(R,'ROOT',root),patch.object(R,'checked_plan',return_value=({},{})),patch.object(R,'verify_runtime',return_value='new'),patch.object(R,'public_checks') as checks,patch.object(R,'gates') as gates,patch.object(R,'switch') as switch,patch.object(R,'emit'):
                R.deploy();checks.assert_called_once();gates.assert_not_called();switch.assert_not_called()

    def test_protected_work_stops_deploy_before_switch(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'prepared.private.json').write_text('{}')
            with patch.object(R,'ROOT',root),patch.object(R,'checked_plan',return_value=({},{})),patch.object(R,'verify_runtime',return_value='baseline'),patch.object(R,'gates',side_effect=R.GuardError('protected_user_work_cutover_deferred')),patch.object(R,'switch') as switch:
                with self.assertRaisesRegex(R.GuardError,'protected_user_work_cutover_deferred'):R.deploy()
                switch.assert_not_called()

    def test_failed_owned_cutover_uses_compatibility_rollback(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'prepared.private.json').write_text('{}')
            with patch.object(R,'ROOT',root),patch.object(R,'checked_plan',return_value=({},{})),patch.object(R,'verify_runtime',side_effect=['baseline','baseline','baseline','rollback']),patch.object(R,'gates'),patch.object(R,'frozen_checks'),patch.object(R,'current_kind',return_value=('new',{})),patch.object(R,'public_checks'),patch.object(R,'fresh_pricing'),patch.object(R,'save'),patch.object(R,'switch',side_effect=[RuntimeError('synthetic cutover failure'),None]) as switch:
                with self.assertRaisesRegex(R.GuardError,'cutover_failed_rollback_succeeded'):R.deploy()
                self.assertEqual([call.args[1] for call in switch.call_args_list],['new','rollback'])

    def test_unknown_cutover_owner_prevents_rollback_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'prepared.private.json').write_text('{}')
            with patch.object(R,'ROOT',root),patch.object(R,'checked_plan',return_value=({},{})),patch.object(R,'verify_runtime',return_value='baseline'),patch.object(R,'gates'),patch.object(R,'current_kind',side_effect=R.GuardError('released_owner_changed')),patch.object(R,'fresh_pricing'),patch.object(R,'save'),patch.object(R,'switch',side_effect=RuntimeError('synthetic cutover failure')) as switch:
                with self.assertRaisesRegex(R.GuardError,'cutover_failed_rollback_needs_attention'):R.deploy()
                self.assertEqual(switch.call_count,1)

    def test_nginx_probe_reads_only_pinned_image_configuration(self):
        result=subprocess.CompletedProcess([],0,b'public nginx configuration',b'')
        with patch.object(R,'run',return_value=result) as execute:
            self.assertEqual(R.nginx_sha(image='sha256:candidate'),R.digest(result.stdout))
            args=execute.call_args.args[0]
            self.assertIn('sha256:candidate',args);self.assertEqual(args[-1],'/etc/nginx/conf.d/default.conf')

    def test_candidate_inventory_checks_unprivileged_static_readability(self):
        result=subprocess.CompletedProcess([],0,(R.digest(b'public')+'  ./public.html\n').encode(),b'')
        with patch.object(R,'run',return_value=result) as execute:
            self.assertEqual(R.inventory(image='sha256:candidate',unprivileged=True),{'public.html':R.digest(b'public')})
            args=execute.call_args.args[0]
            self.assertEqual(args[args.index('--user')+1],'nginx')
            self.assertEqual(args[args.index('--network')+1],'none')
            self.assertIn('--read-only',args)
        with self.assertRaisesRegex(R.GuardError,'inventory_probe_scope_invalid'):R.inventory(unprivileged=True)

    def test_self_consistent_manifest_cannot_authorize_old_asset_replacement(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); html=root/'candidate/html'; html.mkdir(parents=True)
            baseline={}
            for n in range(328):
                name='seo/pricing.html' if n==0 else f'assets/original-{n}.js'; path=html/name;path.parent.mkdir(parents=True,exist_ok=True)
                path.write_bytes(b'original');baseline[name]=R.digest(b'original')
            modules={}
            for n in range(11):
                name=f'assets/NewModule{n}-{n:08x}.js';(html/name).write_bytes(b'new')
                modules[name]={'sha256':R.digest(b'new')}
            nginx=root/'candidate/nginx/default.conf';nginx.parent.mkdir();nginx.write_bytes(b'public synthetic nginx')
            pricing=root/'pricing.json';expected=self.pricing();pricing.write_text(json.dumps(expected))
            support={}
            for name in ('release_cn_search_content.py',*(('release_support/cn_upload20m_model1017_20261021_r2/'+n) for n in ('base_helpers.py',*R.GATES))):
                path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(b'synthetic pinned support');support[name]=R.digest(path.read_bytes())
            manifest={'releaseId':R.RELEASE,'baseWebImage':R.BASE_IMAGE,'packageReady':True,'inventory':R.inventory_files(html),'newModules':modules,'nginx':{'beforeSha256':R.digest(nginx.read_bytes()),'afterSha256':R.digest(nginx.read_bytes())},'pricing':{'fingerprint':R.pricing_fingerprint(expected),'htmlSha256':R.digest((html/'seo/pricing.html').read_bytes())}}
            manifest_path=root/'candidate/release-manifest.json'
            plan={'releaseId':R.RELEASE,'baseline':{'web':{'id':R.BASE_ID,'image':R.BASE_IMAGE},'inventory':baseline,'nginxSha256':R.digest(nginx.read_bytes())},'candidateManifestSha256':'','supportFiles':support,'pricingSha256':R.digest(pricing.read_bytes())}
            def write_plan():
                manifest_path.write_text(json.dumps(manifest));plan['candidateManifestSha256']=R.digest(manifest_path.read_bytes());(root/'input.json').write_text(json.dumps(plan))
            write_plan()
            with patch.object(R,'ROOT',root):
                R.checked_plan()
                # Even updating all hashes cannot authorize changing an original JS URL.
                (html/'assets/original-1.js').write_bytes(b'changed')
                manifest['inventory']=R.inventory_files(html);write_plan()
                with self.assertRaisesRegex(R.GuardError,'unapproved_original_changed'):R.checked_plan()



if __name__=='__main__':unittest.main(verbosity=2)
