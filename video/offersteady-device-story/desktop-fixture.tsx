import React from 'react';
import {createRoot} from 'react-dom/client';
import {CompanionApp} from '../../apps/desktop/src/renderer/CompanionApp';
import '../../apps/desktop/src/renderer/styles.css';
window.offersteady = {
getDesktopConfig:async()=>({appVersion:'1.2.14',platform:'macos',architecture:'arm64',platformVersion:'15',protocolVersion:'1',captureRuntime:'electron-single-owner',webWorkspaceUrl:'http://127.0.0.1:5189/app',apiBaseUrl:'http://127.0.0.1:9',realtimeEndpointing:{mode:'commercial-adaptive'}}),
getPairingIdentity:async()=>({deviceId:'synthetic-desktop',manualCode:'628391',displayName:'演示电脑'}),
getNativeRuntimeHealth:async()=>({available:true,ready:true,microphonePermission:'granted',screenPermission:'granted'}),
requestMicrophoneAccess:async()=>true,requestScreenCaptureAccess:async()=>true,publishCaptureState:()=>{},
apiRequest:async(req)=>({ok:true,status:200,statusText:'OK',headers:{'Content-Type':'application/json'},bodyText:JSON.stringify({data:req.url.includes('active-connection')||req.url.includes('pairing-status')?{state:'registered',manualCode:'628391',registered:true,bound:false}:req.url.includes('/binding')?null:{deviceId:'synthetic-desktop',manualCode:'628391'}})})
} as any;
createRoot(document.getElementById('root')!).render(<CompanionApp/>);
