import json,subprocess
from pathlib import Path
p=Path(__file__).resolve().parent
rows=json.loads((p/'voiceover.json').read_text());out=p/'out';qa=out/'qa';qa.mkdir(exist_ok=True)
def run(args): subprocess.run(args,check=True)
for r in rows:
 source=p/r['file'];trim=source.with_suffix('.wav')
 run(['ffmpeg','-v','error','-y','-i',str(source),'-af','silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.05,areverse,silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.12,areverse','-ar','48000',str(trim)])
 duration=float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','default=nw=1:nk=1',str(trim)]))
 r['trimDuration']=duration;r['tempo']=max(1,duration/(r['end']-r['start']-.08));r['duration']=duration/r['tempo']
 if r['tempo']>1.3: raise RuntimeError(f'Segment {r["id"]} needs rewrite, tempo {r["tempo"]}')
import wave
pcm=bytearray(49*48000*2)
for r in rows:
 source=(p/r['file']).with_suffix('.wav');norm=source.with_name(source.stem+'-normalized.wav')
 run(['ffmpeg','-v','error','-y','-i',str(source),'-af',f'atempo={r["tempo"]},loudnorm=I=-18:TP=-2:LRA=7,aresample=48000,asetpts=N/SR/TB','-ar','48000','-ac','1','-c:a','pcm_s16le',str(norm)])
 with wave.open(str(norm),'rb') as w: chunk=w.readframes(w.getnframes())
 actual=len(chunk)/96000
 if actual>r['end']-r['start']: raise RuntimeError('Narration overflow')
 r['duration']=actual
 start=round(r['start']*48000)*2
 pcm[start:start+len(chunk)]=chunk
with wave.open(str(out/'offersteady-device-story-narration.wav'),'wb') as w:
 w.setnchannels(1);w.setsampwidth(2);w.setframerate(48000);w.writeframes(pcm)
# Duck the existing music smoothly beneath narration, keeping original video stream intact.
run(['ffmpeg','-v','error','-y','-i',str(out/'offersteady-device-story.mp4'),'-i',str(out/'offersteady-device-story-narration.wav'),'-filter_complex','[1:a]asplit=2[sc][voice];[0:a]volume=0.75[music];[music][sc]sidechaincompress=threshold=0.025:ratio=8:attack=80:release=450:makeup=1[duck];[duck][voice]amix=inputs=2:normalize=0,alimiter=limit=0.891:level=false,atrim=duration=49[mix]','-map','0:v:0','-map','[mix]','-c:v','copy','-c:a','aac','-b:a','192k','-ar','48000','-movflags','+faststart',str(out/'offersteady-device-story-voice.mp4')])
(p/'voiceover-timing.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2))
print(json.dumps([{'id':r['id'],'start':r['start'],'duration':round(r['duration'],3),'tempo':round(r['tempo'],3),'end':round(r['start']+r['duration'],3)} for r in rows],indent=2))
