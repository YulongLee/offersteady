import subprocess,json
from pathlib import Path
import numpy as np
from scipy.signal import correlate
p=Path(__file__).resolve().parent
out=p/'out'
def read(f):return np.frombuffer(subprocess.check_output(['ffmpeg','-v','error','-i',str(f),'-f','f32le','-ac','1','-ar','48000','-']),dtype=np.float32)
files=['offersteady-commercial.mp4','offersteady-commercial-nobgm.mp4','web/offersteady-web.mp4','web/offersteady-web-720.mp4']
results={}
for name in files:
 f=out/name
 data=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(f)]))
 check=subprocess.run(['ffmpeg','-v','error','-i',str(f),'-f','null','-'],capture_output=True)
 results[name]={'bytes':f.stat().st_size,'streams':[{k:s[k] for k in ['codec_type','codec_name','width','height','r_frame_rate','duration','nb_frames','pix_fmt','sample_rate'] if k in s} for s in data['streams']], 'decodeExit':check.returncode,'decodeErrors':check.stderr.decode()}
y=read(out/files[1]);m=json.loads((p/'reference/sfx-measurements.json').read_text());sync=[]
for target,src in [(55,'transition-soft.mp3'),(165,'whoosh-fast.mp3'),(312,'transition-soft.mp3'),(380,'whoosh-fast.mp3'),(828,'click-camera.mp3'),(960,'transition-soft.mp3'),(1270,'whoosh-fast.mp3'),(1460,'click-camera.mp3'),(1535,'transition-soft.mp3'),(1905,'riser-rise.mp3'),(1950,'impact-deep-whoosh.mp3'),(2026,'shimmer-sparkle-sweep.mp3')]:
 peak=m[src]['peakFrame'];scheduled=max(0,round(target-peak-2.56))
 x=read(p/'public/audio'/src)[:int(.3*48000 if src=='click-camera.mp3' else (1.7*48000 if src=='riser-rise.mp3' else .9*48000))]
 # Match source waveform within a tight region around declared start; fade-in is retained in rendered track.
 start=max(0,int((scheduled/60-.1)*48000));z=y[start:int((scheduled/60+len(x)/48000+.13)*48000)]
 c=correlate(z,x,mode='valid',method='fft');actual=(start+int(np.argmax(c)))/48000*60
 sync.append({'targetFrame':target,'source':src,'scheduledStart':scheduled,'matchedStart':round(actual,3),'matchedPeak':round(actual+peak,3),'peakErrorFrames':round(actual+peak-target,3)})
results['sfxSync']=sync
z=read(out/files[0]);results['monoAnalysisSignalPeakDbFS']=float(20*np.log10(max(abs(z))));results['monoAnalysisSamplesAtOrOverFullScale']=int(np.sum(abs(z)>=1))
(out/'qa/delivery-checks.json').write_text(json.dumps(results,ensure_ascii=False,indent=2));print(json.dumps(results,ensure_ascii=False,indent=2))
