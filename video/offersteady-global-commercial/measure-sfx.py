from pathlib import Path
import subprocess,json
import numpy as np
p=Path(__file__).resolve().parent
out={}
for f in (p/'public/audio').glob('*.mp3'):
 if 'bgm' in f.name: continue
 y=np.frombuffer(subprocess.check_output(['ffmpeg','-v','error','-i',str(f),'-f','f32le','-ac','1','-ar','48000','-']),dtype=np.float32)
 n=240;env=np.mean(y[:len(y)//n*n].reshape(-1,n)**2,axis=1);peak=int(np.argmax(env))*n/48000
 out[f.name]={'duration':len(y)/48000,'peakSec':peak,'peakFrame':peak*60,'maxDb':float(20*np.log10(np.max(np.abs(y))+1e-9))}
(p/'reference/sfx-measurements.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
