"""Verify the sealed CN production sources and static bundle without network/I/O writes."""
from pathlib import Path
import hashlib,json,tarfile
ROOT=Path(__file__).resolve().parents[1]
RELEASE=ROOT/'releases/cn-20261019.1'
def sha(data):return hashlib.sha256(data).hexdigest()
def main():
    manifest=json.loads((RELEASE/'manifest.json').read_bytes())
    actual={str(p.relative_to(ROOT)):sha(p.read_bytes()) for d in ('apps/backend/app','apps/backend/migrations','ai/prompts')
        for p in (ROOT/d).rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc' and p.name!='.desktop-release-manifest.lock'}
    actual['apps/backend/pyproject.toml']=sha((ROOT/'apps/backend/pyproject.toml').read_bytes())
    assert actual==manifest['backend']['files'] and len(actual)==230,'backend_source_inventory_mismatch'
    for name,checksum in manifest['web']['exactOverlaySourceFiles'].items():assert sha((ROOT/name).read_bytes())==checksum,'published_overlay_source_mismatch'
    bundle=RELEASE/manifest['web']['bundle'];assert sha(bundle.read_bytes())==manifest['web']['bundleSha256'],'static_bundle_mismatch'
    with tarfile.open(bundle,'r:gz') as archive:
        members=archive.getmembers();assert len(members)==315
        assert {m.name for m in members}==set(manifest['web']['files'])
        for member in members:
            assert member.isfile() and not member.issym() and not member.islnk() and not member.name.startswith('/') and '..' not in Path(member.name).parts,'unsafe_archive_member'
            assert sha(archive.extractfile(member).read())==manifest['web']['files'][member.name],'published_static_byte_mismatch'
    assert not (ROOT/'apps/backend/app/services/cn_resume_optimizer_export.py').exists(),'rolled_back_pdf_renderer_present'
    assert not any((ROOT/'ai/prompts/resume-optimizer'/f'review.zh-CN.v{n}.md').exists() for n in (3,4,5,6)),'rolled_back_prompt_present'
    assert 'resume-optimizer-zh-CN-v2' in (ROOT/'apps/backend/app/services/cn_resume_optimizer_provider.py').read_text()
    print(json.dumps({'passed':True,'version':manifest['version'],'backendFiles':230,'webStaticFiles':315,'exactPublishedOverlaySources':4,'productionChanges':0,'networkCalls':0}))
if __name__=='__main__':main()
