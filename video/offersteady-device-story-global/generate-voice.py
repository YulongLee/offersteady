"""Generate scene narration. Credential is read without echo and never persisted."""
import getpass,json,urllib.request,urllib.error,subprocess
from pathlib import Path
root=Path(__file__).resolve().parent
out=root/'public/audio/voice';out.mkdir(parents=True,exist_ok=True)
segments=[
(.35,4.7,'Your interview on the computer. Your guidance on the phone.'),
(5.3,11.7,'Install and open the OfferSteady companion app, then allow microphone and screen access.'),
(12.3,19.7,'On your phone, sign in to the same account and enter the connection code shown on your computer.'),
(20.3,28.7,'Start the interview. Your computer captures the conversation while your phone shows the live transcript. Tap Quick Answer whenever you need guidance.'),
(29.3,35.7,'Use the key idea first, then open the detailed answer based on the materials selected for this session.'),
(36.2,40.7,'Want more room? Open the interview page on a tablet.'),
(41.15,44.8,'Prefer your computer? Use the web app there.'),
(45.2,48.8,'OfferSteady. The computer runs it. You choose where to view it.')]
key=getpass.getpass('MiniMax credential (hidden): ').replace('\\_','_').strip()
records=[]
for i,(start,end,line) in enumerate(segments,1):
 path=out/f'voice-{i:02}.mp3'
 payload={'model':'speech-2.8-hd','text':line,'stream':False,'language_boost':'English','voice_setting':{'voice_id':'English_Trustworthy_Man','speed':1.02,'vol':1,'pitch':0,'emotion':'calm'},'audio_setting':{'sample_rate':44100,'bitrate':128000,'format':'mp3','channel':1}}
 req=urllib.request.Request('https://api.minimaxi.com/v1/t2a_v2',data=json.dumps(payload).encode(),headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'})
 try:
  with urllib.request.urlopen(req,timeout=120) as response: data=json.load(response)
 except urllib.error.HTTPError as e: raise SystemExit(f'Voice {i}: HTTP {e.code}')
 status=data.get('base_resp',{})
 if status.get('status_code')!=0: raise SystemExit(f'Voice {i}: provider error {status.get("status_code")}')
 path.write_bytes(bytes.fromhex(data['data']['audio']))
 duration=float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','default=nw=1:nk=1',str(path)]))
 record={'id':i,'start':start,'end':end,'text':line,'sourceDuration':duration,'file':str(path.relative_to(root))}
 records.append(record);print(f'Voice {i}: {duration:.2f}s, window {end-start:.2f}s',flush=True)
 (root/'voiceover.json').write_text(json.dumps(records,ensure_ascii=False,indent=2))
key=None
