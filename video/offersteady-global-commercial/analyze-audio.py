import json
from pathlib import Path
import numpy as np,librosa
from scipy.signal import butter,sosfilt,find_peaks
p=Path(__file__).resolve().parent
x,sr=librosa.load('/tmp/offersteady-video-reference/bgm.wav',sr=None)
tempo,beats=librosa.beat.beat_track(y=x,sr=sr,tightness=400,units='time',hop_length=256)
T,t0=np.polyfit(np.arange(len(beats)),beats,1)
hits={}
for name,lo,hi in [('kick',40,160),('snare',150,3000),('hihat',6000,10000)]:
 y=sosfilt(butter(4,[lo,hi],btype='band',fs=sr,output='sos'),x)
 hop=110
 env=np.sqrt(np.mean(y[:len(y)//hop*hop].reshape(-1,hop)**2,axis=1))
 peaks,_=find_peaks(env,distance=int(.25*sr/hop),prominence=np.max(env)*.08)
 hits[name]=[{'t':float(v*hop/sr),'s':float(env[v])} for v in peaks]
result={'bpm':float(60/T),'T':float(T),'t0':float(t0),'beats':beats.tolist(),'residualMax':float(np.max(np.abs(beats-(t0+np.arange(len(beats))*T)))),'hits':hits}
(p/'reference/beat-data.json').write_text(json.dumps(result,indent=2))
print(json.dumps({k:v for k,v in result.items() if k not in ['beats','hits']}));print('kick first',hits['kick'][:12])
