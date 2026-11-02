import importlib.util
import json
from pathlib import Path
import tempfile
import struct
import plistlib
import unittest

S=importlib.util.spec_from_file_location('global136_verify',Path(__file__).with_name('verify_packages.py'))
M=importlib.util.module_from_spec(S);S.loader.exec_module(M)

class GlobalPackageGuards(unittest.TestCase):
    def test_only_exact_global_production_runtime_is_accepted(self):
        M.assert_runtime(dict(M.EXPECTED_RUNTIME))
        for key,value in [('productEdition','domestic'),('releaseChannel','local-test'),
                          ('webWorkspaceUrl','https://mianshiwen.cn/app'),('apiBaseUrl','http://localhost:8000/api/v1')]:
            config={**M.EXPECTED_RUNTIME,key:value}
            with self.assertRaises(M.V.VerificationError):M.assert_runtime(config)
        with self.assertRaises(M.V.VerificationError):M.assert_runtime({**M.EXPECTED_RUNTIME,'token':'synthetic-forbidden'})

    def test_config_resource_is_required_and_no_other_overrides_are_allowed(self):
        with tempfile.TemporaryDirectory() as temp:
            r=Path(temp)
            with self.assertRaises(M.V.VerificationError):M.check_resources(r)
            (r/'global-runtime-config.json').write_text(json.dumps(M.EXPECTED_RUNTIME))
            M.check_resources(r)
            for name in ['local-test-runtime.json','global-runtime.json','device-pairing.json','.env','secret.p8','secret.pem']:
                (r/name).write_text('synthetic')
                with self.assertRaises(M.V.VerificationError):M.check_resources(r)
                (r/name).unlink()
            (r/'nested').mkdir();(r/'nested/global-runtime-config.json').write_text(json.dumps(M.EXPECTED_RUNTIME))
            with self.assertRaises(M.V.VerificationError):M.check_resources(r)

    def test_main_package_identity_must_remain_global_version(self):
        M.V.assert_package_json({'name':'@offersteady/desktop','version':'1.3.6','main':'dist/main/index.js'})
        with self.assertRaises(M.V.VerificationError):M.V.assert_package_json({'name':'other','version':'1.3.6','main':'dist/main/index.js'})

    def test_unsafe_archive_paths_remain_rejected(self):
        for name in ['../escape','/absolute','C:\\escape']:
            with self.assertRaises(M.V.VerificationError):M.V.safe_name(name)

    def test_native_embedded_global_identity_and_english_permissions_are_checked(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'synthetic-native'
            info={'CFBundleIdentifier':M.BUNDLE_ID,
                  'NSMicrophoneUsageDescription':'Synthetic microphone permission',
                  'NSAudioCaptureUsageDescription':'Synthetic system audio permission',
                  'NSScreenCaptureUsageDescription':'Synthetic screen permission'}
            def image(value):
                blob=plistlib.dumps(value);data=bytearray(256+len(blob))
                struct.pack_into('<8I',data,0,0xfeedfacf,0x100000c,0,2,1,152,0,0)
                struct.pack_into('<II',data,32,0x19,152);struct.pack_into('<I',data,32+64,1)
                data[104:120]=b'__info_plist'.ljust(16,b'\0')
                struct.pack_into('<Q',data,104+40,len(blob));struct.pack_into('<I',data,104+48,256)
                data[256:]=blob;return data
            path.write_bytes(image(info));M.native_global_identity(path)
            for patch in [{'CFBundleIdentifier':'com.offersteady.companion'},
                          {'NSMicrophoneUsageDescription':''},
                          {'NSAudioCaptureUsageDescription':'合成权限'},
                          {'NSScreenCaptureUsageDescription':None}]:
                path.write_bytes(image({**info,**patch}) if None not in patch.values()
                                 else image({k:v for k,v in {**info,**patch}.items() if v is not None}))
                with self.assertRaises(M.V.VerificationError):M.native_global_identity(path)
            data=image(info);struct.pack_into('<I',data,104+48,len(data)+1);path.write_bytes(data)
            with self.assertRaises(M.V.VerificationError):M.native_global_identity(path)

    def test_every_macho_component_must_match_target_architecture(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            thin=lambda cpu:struct.pack('<II',0xfeedfacf,cpu)
            for name in ['main','Renderer Helper','framework']:(root/name).write_bytes(thin(0x100000c))
            self.assertEqual(M.check_all_macho_architectures(root,'arm64'),3)
            (root/'framework').write_bytes(thin(0x1000007))
            with self.assertRaises(M.V.VerificationError):M.check_all_macho_architectures(root,'arm64')
            (root/'framework').write_bytes(b'\xca\xfe\xba\xbe'+b'\0'*4)
            with self.assertRaises(M.V.VerificationError):M.check_all_macho_architectures(root,'arm64')
            (root/'framework').unlink()
            with self.assertRaises(M.V.VerificationError):M.check_all_macho_architectures(root,'arm64')

if __name__=='__main__':unittest.main()
