import subprocess,json
from pathlib import Path
import numpy as np
from scipy.signal import correlate
p=Path(__file__).resolve().parent
file=p/'out/audio-probe.mp4'
def read(f):return np.frombuffer(subprocess.check_output(['ffmpeg','-v','error','-i',str(f),'-f','f32le','-ac','1','-ar','48000','-']),dtype=np.float32)
y=read(file);results=[]
for target,src in [(30,'click-camera.mp3'),(120,'impact-deep-whoosh.mp3')]:
 x=read(p/'public/audio'/src)[:int(.9*48000)]
 start=int((target/60-.15)*48000);z=y[start:int((target/60+1.1)*48000)]
 corr=correlate(z,x,mode='valid',method='fft');idx=int(np.argmax(corr));actual=(start+idx)/48000*60
 results.append({'source':src,'scheduledFrame':target,'actualStartFrame':actual,'offsetFrames':actual-target})
print(json.dumps(results,indent=2));(p/'reference/output-offset-probe.json').write_text(json.dumps({'pipeline':'Remotion 4.0.484 / 60fps / AAC 48kHz / MP4 / Chrome Headless Shell','date':'2026-09-07','probes':results,'offsetFrames':float(np.mean([r['offsetFrames'] for r in results]))},indent=2))
