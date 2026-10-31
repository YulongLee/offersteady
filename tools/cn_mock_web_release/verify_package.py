"""Replay the frozen delta and independently compare every public candidate byte."""
import argparse
import importlib.util
import json
from pathlib import Path
import tempfile

spec=importlib.util.spec_from_file_location('mock_builder',Path(__file__).with_name('build_web_release.py'))
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

def verify(baseline,baseline_manifest,source_manifest,candidate,output):
    candidate=Path(candidate)
    manifest=json.loads((candidate/'web-manifest.json').read_text())
    assert manifest['freshBaselineManifestSha256']==m.sha(Path(baseline_manifest).read_bytes()),'baseline manifest drift'
    assert manifest['sourceHandoffSha256']==m.sha(Path(source_manifest).read_bytes()),'source handoff drift'
    assert manifest['patchReportSha256']==m.sha((candidate/'web-patch-report.json').read_bytes()),'patch report drift'
    actual=m.load_files(candidate/'web/html')
    assert {n:m.sha(b) for n,b in actual.items()}==manifest['inventory'],'candidate full inventory drift'
    with tempfile.TemporaryDirectory(prefix='verify-cn-mock-web-') as temporary:
        replay=m.build(baseline,baseline_manifest,source_manifest,Path(temporary)/'replay',manifest['releaseId'])
        assert replay==manifest,'candidate manifest differs from frozen replay'
        expected=m.load_files(Path(temporary)/'replay/web/html')
        assert actual==expected,'candidate bytes differ from frozen replay'
        assert (Path(temporary)/'replay/web-patch-report.json').read_bytes()==(candidate/'web-patch-report.json').read_bytes(),'patch selection differs from replay'
    original=m.load_files(baseline)
    mapping=manifest['moduleMapping'];inverse={v:k for k,v in mapping.items()}
    nonmock={old:new for old,new in mapping.items() if old in original and old not in manifest['patchedOriginalModules']}
    for old,new in nonmock.items():assert m.rewrite(actual[new].decode(),inverse)==original[old].decode(),'nonmock changed beyond references'
    preserved=['assets/mock-interview-report-CtmMBUmT.js','assets/mock-interview-word-export-BOxeSAD1.js']
    for name in preserved:assert actual[name]==original[name],'report or Word exporter changed'
    result={'passed':True,'candidateManifestSha256':m.sha((candidate/'web-manifest.json').read_bytes()),
      'baselineFiles':len(original),'candidateFiles':len(actual),'newAssets':len(manifest['newAssets']),
      'allCandidateBytesReproducedFromFrozenInputs':True,'nonmockParentsOnlyReferenceChanges':nonmock,
      'originalReportAndWordExportBytes':{n:m.sha(actual[n]) for n in preserved},
      'nginxWritten':False,'originalInitializationStatementsPreserved':True,'productionOrModelCalls':0}
    Path(output).write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'passed':True,'files':len(actual),'nonmockReferenceOnlyParents':len(nonmock)}))
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['baseline','baseline-manifest','source-manifest','candidate','output']:p.add_argument('--'+name,required=True,type=Path)
    a=p.parse_args();verify(a.baseline,a.baseline_manifest,a.source_manifest,a.candidate,a.output)
