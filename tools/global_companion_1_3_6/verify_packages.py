"""Offline verification of frozen Global 1.3.6 official packages. No app launch/upload."""
from __future__ import annotations
import argparse
import importlib.util
import json
from pathlib import Path
import plistlib
import re
import struct
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('companion136_archive_primitives', ROOT / 'tools/companion_1_3_6_local/verify_packages.py')
V = importlib.util.module_from_spec(spec)
spec.loader.exec_module(V)
require = V.require
EXPECTED_RUNTIME = {'productEdition':'global', 'releaseChannel':'global',
                    'webWorkspaceUrl':'https://offersteady.com/app', 'apiBaseUrl':'https://offersteady.com/api/v1'}
BUNDLE_ID = 'com.offersteady.companion.global'
RUNTIME_INPUT = 'apps/desktop/build/generated/global-runtime-config.json'


def assert_runtime(value):
    require(value == EXPECTED_RUNTIME, 'global_runtime_configuration_changed')


def blocked(name):
    parts = Path(name).parts
    return V.forbidden_name(name) or any(p.startswith('.env') or p in {'device-pairing.json','device-credential.bin'}
        or p.endswith(('.pem','.key','.pfx')) for p in parts)


def source_inputs(root):
    root = Path(root)
    result = V.source_inventory(root)
    for name in [RUNTIME_INPUT, 'apps/desktop/vite.config.mts','apps/desktop/tsconfig.main.json',
                 'apps/desktop/tsconfig.renderer.json','tsconfig.base.json']:
        p = root / name
        require(p.is_file() and not p.is_symlink(), 'source_input_missing')
        result[name] = V.file_digest(p)
    assert_runtime(json.loads((root / RUNTIME_INPUT).read_text()))
    return dict(sorted(result.items()))


def freeze(root, output):
    root = Path(root)
    files = V.inventory(root / 'apps/desktop/dist')
    require('main/index.js' in files and 'renderer/index.html' in files, 'dist_entry_missing')
    require(not any(blocked(n) for n in files), 'blocked_runtime_file')
    require(not any(n.endswith(('.test.js','.test.mjs','.spec.js','.spec.mjs')) for n in files), 'compiled_test_in_runtime')
    V.assert_package_json(json.loads((root / 'apps/desktop/package.json').read_text()))
    html = (root / 'apps/desktop/dist/renderer/index.html').read_text()
    require('<title>OfferSteady Companion</title>' in html, 'global_renderer_title_missing')
    value = {'schemaVersion':1, 'version':'1.3.6','edition':'global','sourceFiles':source_inputs(root),
             'distFiles':files,'runtime':EXPECTED_RUNTIME}
    native = root / 'apps/desktop/dist/native/macos-capture/OfferSteadyCaptureRuntime'
    if native.exists(): value['nativeCompiledPayloadSha256'] = V.canonical_native_digest(native)
    V.save(output,value)
    return {'passed':True,'sourceFileCount':len(value['sourceFiles']),'distFileCount':len(files)}


def load_manifest(root, path):
    m = json.loads(Path(path).read_text())
    require(m.get('schemaVersion') == 1 and m.get('version') == '1.3.6' and m.get('edition') == 'global', 'source_manifest_invalid')
    require(m['sourceFiles'] == source_inputs(root), 'frozen_global_source_drift')
    assert_runtime(m['runtime'])
    return m


def check_resources(resources):
    files = V.inventory(resources, allow_links=True)
    require('global-runtime-config.json' in files, 'global_runtime_resource_missing')
    require(not any(blocked(n) for n in files if n != 'global-runtime-config.json'), 'blocked_resource_file')
    assert_runtime(json.loads((Path(resources) / 'global-runtime-config.json').read_text()))
    return files


def check_asar(resources, manifest):
    a = V.read_asar(Path(resources) / 'app.asar')
    V.assert_package_json(a['packageJson'])
    V.compare_dist(a['files'],manifest)
    require(not any(blocked(n) for n in a['files']), 'blocked_asar_file')
    require(not any(n.startswith('dist/native/') for n in a['files']), 'native_runtime_in_asar')
    require(not any(n.endswith(('.test.js','.test.mjs','.spec.js','.spec.mjs')) for n in a['files']), 'compiled_test_in_asar')
    return a


def assert_english_permissions(info):
    for key in ('NSMicrophoneUsageDescription','NSAudioCaptureUsageDescription','NSScreenCaptureUsageDescription'):
        value = info.get(key)
        require(isinstance(value,str) and bool(value.strip()) and not re.search(r'[\u3400-\u9fff]',value), 'global_english_permission_missing')


def native_global_identity(path):
    data = Path(path).read_bytes()
    require(len(data) >= 32 and data[:4] == b'\xcf\xfa\xed\xfe','native_macho64_required')
    commands,size = struct.unpack_from('<II',data,16)
    require(0 < commands <= 4096 and 32+size <= len(data),'native_commands_invalid')
    position, found = 32, []
    for _ in range(commands):
        require(position+8 <= 32+size,'native_commands_invalid')
        command,length = struct.unpack_from('<II',data,position)
        require(length >= 8 and position+length <= 32+size,'native_commands_invalid')
        if command == 0x19:
            require(length >= 72,'native_segment_invalid')
            sections = struct.unpack_from('<I',data,position+64)[0]
            require(72+sections*80 <= length,'native_sections_invalid')
            for index in range(sections):
                section=position+72+index*80
                if data[section:section+16].rstrip(b'\0') != b'__info_plist': continue
                section_size=struct.unpack_from('<Q',data,section+40)[0]
                offset=struct.unpack_from('<I',data,section+48)[0]
                require(section_size > 0 and offset+section_size <= len(data),'native_info_bounds_invalid')
                found.append(plistlib.loads(data[offset:offset+section_size]))
        position += length
    require(position == 32+size and len(found)==1,'native_info_missing_or_ambiguous')
    require(found[0].get('CFBundleIdentifier') == BUNDLE_ID,'native_global_identity_changed')
    assert_english_permissions(found[0])


def check_all_macho_architectures(app, arch):
    magics = {b'\xcf\xfa\xed\xfe',b'\xfe\xed\xfa\xcf',b'\xce\xfa\xed\xfe',b'\xfe\xed\xfa\xce',
              b'\xca\xfe\xba\xbe',b'\xbe\xba\xfe\xca',b'\xca\xfe\xba\xbf',b'\xbf\xba\xfe\xca'}
    count = 0
    for path in Path(app).rglob('*'):
        if path.is_symlink() or not path.is_file(): continue
        with path.open('rb') as handle: magic = handle.read(4)
        if magic not in magics: continue
        require(V.macho_architecture(path) == arch,'mac_component_architecture_mismatch')
        count += 1
    require(count >= 3,'mac_component_architecture_inventory_incomplete')
    return count


def check_mac(root, app, arch, artifact, manifest):
    app,artifact = Path(app).resolve(),Path(artifact).resolve()
    info = plistlib.loads((app / 'Contents/Info.plist').read_bytes())
    require(info.get('CFBundleIdentifier') == BUNDLE_ID and info.get('CFBundleShortVersionString') == '1.3.6'
            and info.get('CFBundleVersion') == '1.3.6', 'global_mac_identity_changed')
    require(info.get('CFBundleExecutable') == 'OfferSteady Companion Global', 'global_mac_executable_changed')
    assert_english_permissions(info)
    require(str(info.get('LSMinimumSystemVersion')) in {'14.2','14.2.0'}, 'minimum_os_changed')
    require(artifact.name == f'OfferSteady-Companion-Global-1.3.6-macOS-{arch}.dmg', 'global_mac_filename_changed')
    require(V.macho_architecture(app / 'Contents/MacOS/OfferSteady Companion Global') == arch, 'mac_main_architecture_changed')
    native = app / 'Contents/Resources/app/native/macos-capture/OfferSteadyCaptureRuntime'
    require(V.macho_architecture(native) == arch and V.canonical_native_digest(native) == manifest['nativeCompiledPayloadSha256'], 'native_payload_or_architecture_changed')
    native_global_identity(native)
    macho_count = check_all_macho_architectures(app,arch)
    check_resources(app / 'Contents/Resources')
    check_asar(app / 'Contents/Resources',manifest)
    V.run(['node',Path(root) / 'apps/desktop/scripts/verify-release-mac.mjs','--app',app,
           '--dmg',artifact,'--bundle-id',BUNDLE_ID],timeout=300)
    archive = V.verify_mac_artifact(app,artifact)
    return {'platform':'macos','architecture':arch,'version':'1.3.6','bundleId':BUNDLE_ID,
            'artifact':archive,'globalRuntimeVerified':True,'frozenDistFilesVerified':len([n for n in manifest['distFiles'] if not n.startswith('native/')]),
            'nativeCompiledPayloadVerified':True,'machOComponentsArchitectureVerified':macho_count,'nativeGlobalIdentityAndEnglishPermissionsVerified':True,'actualSignatureAndAudioEntitlementsPassed':True,
            'appAndDmgNotarizedStapledGatekeeperPassed':True,'notarized':True,'signingStatus':'verified'}


def certificate_bytes(path):
    data = Path(path).read_bytes(); require(data[:2] == b'MZ','pe_dos_header_invalid')
    p = struct.unpack_from('<I',data,0x3c)[0]; require(data[p:p+4] == b'PE\x00\x00','pe_signature_invalid')
    opt = p + 24; magic = struct.unpack_from('<H',data,opt)[0]; require(magic in {0x10b,0x20b},'pe_optional_header_invalid')
    return struct.unpack_from('<II',data,opt+(112 if magic==0x20b else 96)+4*8)[1]


def check_win(package, artifact, sevenzip, manifest):
    package,artifact,sevenzip = Path(package).resolve(),Path(artifact).resolve(),Path(sevenzip).resolve()
    files = V.inventory(package)
    require(artifact.name == 'OfferSteady-Companion-Global-Setup-1.3.6-Windows-x64.exe', 'global_windows_filename_changed')
    require(not any(blocked(n) for n in files if n != 'resources/global-runtime-config.json'), 'blocked_windows_file')
    check_resources(package / 'resources'); check_asar(package / 'resources',manifest)
    require(V.pe_machine(package / 'OfferSteadyGlobal.exe') == 'x64','windows_app_not_x64')
    require(certificate_bytes(package / 'OfferSteadyGlobal.exe') == 0 and certificate_bytes(artifact) == 0,'unexpected_windows_signing_state')
    require(artifact.stat().st_size > 10*1024*1024,'installer_too_small')
    outer_arch = V.pe_machine(artifact)
    with tempfile.TemporaryDirectory(prefix='global136-installer-') as tmp:
        outer,inner = Path(tmp)/'outer',Path(tmp)/'inner';outer.mkdir();inner.mkdir()
        V.extract_checked(sevenzip,artifact,outer)
        archives = list(outer.rglob('app-64.7z'));require(len(archives)==1,'x64_archive_missing')
        V.extract_checked(sevenzip,archives[0],inner)
        exes = list(inner.rglob('OfferSteadyGlobal.exe'));require(len(exes)==1,'inner_global_executable_missing')
        require(V.inventory(exes[0].parent) == files,'installer_payload_drift')
        require(V.pe_machine(exes[0]) == 'x64' and certificate_bytes(exes[0]) == 0,'inner_windows_architecture_or_signing_changed')
    return {'platform':'windows','architecture':'x64','version':'1.3.6','artifact':{
        'fileName':artifact.name,'fileSizeBytes':artifact.stat().st_size,'sha256':V.file_digest(artifact)},
        'globalRuntimeVerified':True,'frozenDistFilesVerified':len([n for n in manifest['distFiles'] if not n.startswith('native/')]),
        'installedFilesVerified':len(files),'installerPayloadExactlyMatchesPreparedPackage':True,
        'outerAndInnerArchiveIntegrityPassed':True,'installerStubArchitecture':outer_arch,
        'applicationArchitecture':'x64','authenticode':'unsigned-certificate-tables-zero','notarized':False,'signingStatus':'unsigned'}


def main():
    p = argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=['freeze','mac','win'])
    p.add_argument('--root',type=Path,default=ROOT);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--manifest',type=Path);p.add_argument('--app',type=Path);p.add_argument('--arch',choices=['arm64','x64'])
    p.add_argument('--artifact',type=Path);p.add_argument('--package',type=Path);p.add_argument('--sevenzip',type=Path)
    a=p.parse_args()
    if a.command=='freeze': print(json.dumps(freeze(a.root,a.output)));return
    m=load_manifest(a.root,a.manifest)
    r=check_mac(a.root,a.app,a.arch,a.artifact,m) if a.command=='mac' else check_win(a.package,a.artifact,a.sevenzip,m)
    r.update(passed=True,sourceManifestSha256=V.file_digest(a.manifest),physicalDeviceAudioAcceptancePerformed=False,
             providerRequestsPerformed=False,productionUpdated=False)
    V.save(a.output,r);print(json.dumps(r))


if __name__=='__main__':
    try: main()
    except Exception as exc:
        print(json.dumps({'passed':False,'reason':str(exc) if isinstance(exc,V.VerificationError) else type(exc).__name__}));raise SystemExit(1) from None
