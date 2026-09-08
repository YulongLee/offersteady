"""Generate scene narration. Credential is read without echo and never persisted."""
import getpass,json,urllib.request,urllib.error,subprocess
from pathlib import Path
root=Path(__file__).resolve().parent
out=root/'public/audio/voice';out.mkdir(parents=True,exist_ok=True)
segments=[
(.35,4.7,'电脑上的面试，手机上的思路。'),
(5.3,11.7,'先在电脑安装并打开面试稳助手，完成权限设置。'),
(12.3,19.7,'手机登录同一账号，打开面试网页，输入电脑连接码。'),
(20.3,28.7,'开始面试，电脑接收声音，手机查看实时对话。需要回答时，点一下快答。'),
(29.3,35.7,'结合本场资料，先看简短思路，再展开详细回答。'),
(36.2,40.7,'也可以用平板，换一块大屏查看。'),
(41.15,44.8,'习惯电脑操作，就直接在电脑上看。'),
(45.2,48.8,'面试稳。电脑运行，在哪看，由你选择。')]
key=getpass.getpass('MiniMax credential (hidden): ').replace('\\_','_').strip()
records=[]
for i,(start,end,line) in enumerate(segments,1):
 path=out/f'voice-{i:02}.mp3'
 payload={'model':'speech-2.8-hd','text':line,'stream':False,'language_boost':'Chinese','voice_setting':{'voice_id':'male-qn-jingying','speed':1.02,'vol':1,'pitch':-1,'emotion':'calm'},'audio_setting':{'sample_rate':44100,'bitrate':128000,'format':'mp3','channel':1}}
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
