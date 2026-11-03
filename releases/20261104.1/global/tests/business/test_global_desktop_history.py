from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace
import pytest
from app.modules import web

BASE=Path(__file__).resolve().parents[1]
OLD=json.loads((BASE/'backend-baseline/apps/backend/app/global_desktop_release_manifest.json').read_text())

@pytest.fixture
def setup_history(monkeypatch,tmp_path):
 path=tmp_path/'global_desktop_release_manifest.json';history=path.with_name('global_desktop_release_history.json');history.write_text(json.dumps(OLD))
 current={'version':1,'entries':[dict(e,version='1.3.6',fileName=e['fileName'].replace('1.3.5','1.3.6')) for e in OLD['entries']]}
 monkeypatch.setattr(web,'get_settings',lambda:SimpleNamespace(product_edition='global'))
 monkeypatch.setattr(web,'_published_desktop_manifest_path',lambda:path)
 monkeypatch.setattr(web,'_published_desktop_manifest',lambda:current)
 return SimpleNamespace(history=history,current=current)

@pytest.mark.parametrize('entry',OLD['entries'])
def test_verified_old_download_keeps_exact_original_metadata(setup_history,entry):
 assert web._published_desktop_entry(entry['fileName'])==entry
 assert web._release_manifest()['entries'][0]['version']=='1.3.6'
 assert len(web._release_manifest()['entries'])==3

@pytest.mark.parametrize('filename',['unknown.exe','../../credentials','OfferSteady-Companion-Global-1.3.4-macOS-arm64.dmg','OfferSteady-Companion-1.3.5-macOS-arm64.dmg','OfferSteady-Companion-Global-1.3.5-macOS-arm64.dmg/../file'])
def test_unknown_path_and_other_edition_cannot_use_history(setup_history,filename):
 assert web._published_desktop_entry(filename) is None

def test_cn_never_reads_history(setup_history,monkeypatch):
 monkeypatch.setattr(web,'get_settings',lambda:SimpleNamespace(product_edition='cn'))
 assert web._published_desktop_entry(OLD['entries'][0]['fileName']) is None

@pytest.mark.parametrize('bad',[None,[],{'entries':'bad'},{'entries':[]},'bad json'])
def test_missing_or_corrupt_history_fails_closed(setup_history,bad):
 if bad is None:setup_history.history.unlink()
 elif bad=='bad json':setup_history.history.write_text('{')
 else:setup_history.history.write_text(json.dumps(bad))
 assert web._published_desktop_entry(OLD['entries'][0]['fileName']) is None

@pytest.mark.parametrize('field,value',[('version','1.3.6'),('objectKey','private/unknown'),('platform','windows'),('architecture','unknown'),('sha256','bad'),('distributionStatus','withdrawn'),('signingStatus','withdrawn')])
def test_modified_history_does_not_grant_other_object_or_release(setup_history,field,value):
 old=deepcopy(OLD);old['entries'][0][field]=value;setup_history.history.write_text(json.dumps(old))
 assert web._published_desktop_entry(OLD['entries'][0]['fileName']) is None

def test_current_match_including_withdrawn_has_priority_over_old_published(setup_history):
 entry=dict(OLD['entries'][0],distributionStatus='withdrawn');setup_history.current['entries'].append(entry)
 assert web._published_desktop_entry(entry['fileName'])==entry
 assert not web._is_public_desktop_entry(web._published_desktop_entry(entry['fileName']))

def test_missing_current_manifest_stays_fail_closed(setup_history,monkeypatch):
 monkeypatch.setattr(web,'_published_desktop_manifest',lambda:None)
 assert web._published_desktop_entry(OLD['entries'][0]['fileName']) is None
