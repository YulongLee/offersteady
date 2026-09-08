import React from 'react';
import {AbsoluteFill, Audio, Sequence, spring, staticFile, useCurrentFrame} from 'remotion';

const C={bg:'#07111f',panel:'#101f31',line:'rgba(255,255,255,.12)',text:'#f4f8fb',muted:'#9fb0c2',mint:'#63e6be',cyan:'#62d8ff',yellow:'#ffd166',orange:'#ff9f43',purple:'#b8a1ff',red:'#ff6b7a'};
const rows=[
  {name:'夯爆了',c:C.mint},{name:'夯',c:'#62d98f'},{name:'顶级',c:C.yellow},{name:'人上人',c:C.orange},{name:'NPC',c:C.purple},{name:'拉完了',c:C.red},
];
const items=[
  {name:'价格算不明白',price:'只写点数',row:5,start:5},
  {name:'慧答AI',price:'¥19 ≈ 20–50分钟',row:4,start:155},
  {name:'面试猪',price:'¥29 / 60分钟',row:3,start:335},
  {name:'KickEdu',price:'¥29 / 2小时',row:2,start:505},
  {name:'面灵AI',price:'¥69 / 周不限量',row:1,start:590},
  {name:'FuOffer',price:'¥25.9 / 天',row:0,start:700},
  {name:'面试稳',price:'¥29.9 / 天',row:0,start:800,hero:true},
];

const Intro=()=>{const f=useCurrentFrame();const s=spring({frame:f,fps:30,config:{damping:12,stiffness:150}});return <AbsoluteFill style={{alignItems:'center',justifyContent:'center',padding:70}}>
  <div style={{fontSize:42,color:C.muted,letterSpacing:10,marginBottom:26}}>国产 AI 面试助手</div>
  <div style={{fontSize:126,fontWeight:950,letterSpacing:-8,transform:`scale(${.72+.28*s})`,opacity:s,color:C.text}}>夯拉评估</div>
  <div style={{marginTop:38,padding:'18px 30px',border:`1px solid ${C.line}`,borderRadius:999,color:C.mint,fontSize:34}}>最低套餐 · 用量规则 · 定价透明度</div>
</AbsoluteFill>};

const Board=()=>{const f=useCurrentFrame();return <AbsoluteFill style={{padding:'120px 54px 150px'}}>
  <div style={{display:'flex',alignItems:'flex-end',justifyContent:'space-between',marginBottom:28}}><div><div style={{fontSize:30,color:C.mint,fontWeight:800,letterSpacing:3}}>2026 国产工具价格横评</div><div style={{fontSize:62,fontWeight:950}}>谁夯，谁拉？</div></div><div style={{fontSize:32,color:C.muted,textAlign:'right'}}>临时一场成本<br/>+ 用量规则</div></div>
  <div style={{display:'grid',gap:12}}>{rows.map((r,i)=><div key={r.name} style={{height:205,display:'grid',gridTemplateColumns:'210px 1fr',borderRadius:28,overflow:'hidden',background:'rgba(255,255,255,.045)',border:`1px solid ${C.line}`}}>
    <div style={{background:r.c,color:'#07111f',display:'flex',alignItems:'center',justifyContent:'center',fontWeight:950,fontSize:i===0?48:42}}>{r.name}</div>
    <div style={{position:'relative',display:'flex',alignItems:'center',gap:12,padding:'18px 22px'}}>{items.filter(x=>x.row===i).map((x,j)=>{const local=f-x.start;const p=spring({frame:local,fps:30,config:{damping:13,stiffness:165,mass:.7}});const hero=x.hero;return <div key={x.name} style={{width:i===0?(hero?430:280):(i===2?310:440),padding:hero?'24px 24px':'19px 22px',borderRadius:24,background:hero?'linear-gradient(135deg,#dcfff4,#7df0ce)':'#f7fbff',color:'#07111f',boxShadow:hero?'0 18px 55px rgba(99,230,190,.35)':'0 12px 30px rgba(0,0,0,.22)',opacity:Math.max(0,p),transform:`translateX(${(1-p)*500}px) rotate(${(1-p)*7}deg) scale(${.88+.12*p})`}}>
      <div style={{fontSize:hero?42:38,fontWeight:950,whiteSpace:'nowrap'}}>{x.name}</div><div style={{fontSize:32,fontWeight:750,marginTop:5,color:'#274358'}}>{x.price}</div>
    </div>})}</div>
  </div>)}</div>
  <div style={{position:'absolute',left:54,right:54,bottom:42,color:'#9aabba',fontSize:32,textAlign:'center'}}>2026-09-08 官方价格页/结算页｜以付款页为准</div>
</AbsoluteFill>};

const Evidence=()=>{const f=useCurrentFrame();const p=spring({frame:f,fps:30,config:{damping:16,stiffness:110}});return <AbsoluteFill style={{padding:'125px 70px 150px'}}>
 <div style={{fontSize:32,color:C.mint,fontWeight:850,letterSpacing:3}}>面试稳为什么也进“夯爆了”</div><div style={{fontSize:66,fontWeight:950,marginTop:14}}>不是最低价<br/>是不用边面试边算账</div>
 <div style={{marginTop:80,borderRadius:42,background:'linear-gradient(145deg,#effff9,#9df4d8)',color:C.bg,padding:'52px 48px',boxShadow:'0 30px 100px rgba(99,230,190,.25)',transform:`translateY(${(1-p)*80}px) scale(${.94+.06*p})`,opacity:p}}>
  <div style={{display:'flex',justifyContent:'space-between',alignItems:'end',paddingBottom:36,borderBottom:'2px solid rgba(7,17,31,.14)'}}><div><div style={{fontSize:34,fontWeight:900}}>面试稳 · 日卡</div><div style={{fontSize:32,color:'#31566a',marginTop:8}}>购买后 1 天内使用</div></div><div style={{fontSize:92,fontWeight:950,letterSpacing:-5}}>¥29.9</div></div>
  {[['实时回答','不限次'],['截图回答','不限次'],['按分钟扣费','不需要'],['边面试边算点数','不需要']].map((x,i)=><div key={x[0]} style={{display:'flex',justifyContent:'space-between',fontSize:34,fontWeight:850,padding:'30px 4px',borderBottom:i<3?'1px solid rgba(7,17,31,.1)':'none'}}><span>{x[0]}</span><span style={{color:'#087a5b'}}>{x[1]}</span></div>)}
 </div>
 <div style={{marginTop:55,padding:'26px 30px',borderRadius:26,background:'rgba(255,255,255,.065)',border:`1px solid ${C.line}`,fontSize:34,lineHeight:1.55,color:C.muted}}>FuOffer 的 ¥25.9/天比面试稳低 4 元。<br/><b style={{color:C.text}}>面试稳的优势是：套餐规则同样直接。</b></div>
 <div style={{fontSize:32,color:C.muted,marginTop:30,textAlign:'center'}}>2026-09-08 官方价格页/结算页 · 以付款页为准</div>
</AbsoluteFill>};

const Outro=()=>{const f=useCurrentFrame();const p=spring({frame:f,fps:30,config:{damping:12,stiffness:120}});return <AbsoluteFill style={{alignItems:'center',justifyContent:'center',textAlign:'center',padding:60}}><div style={{fontSize:32,color:C.mint,fontWeight:800,letterSpacing:6}}>面试稳 OFFERSTEADY</div><div style={{fontSize:114,fontWeight:950,marginTop:25,transform:`scale(${.8+.2*p})`}}>夯爆了</div><div style={{fontSize:38,color:C.muted,marginTop:25,lineHeight:1.5}}>¥29.9 / 天<br/>回答与截图不限次</div><div style={{fontSize:34,marginTop:55,padding:'20px 34px',borderRadius:999,background:C.mint,color:C.bg,fontWeight:900}}>mianshiwen.cn</div></AbsoluteFill>};

export const HanglaVideo:React.FC<{bgm:boolean}>=({bgm})=>{return <AbsoluteFill style={{background:`radial-gradient(circle at 80% 10%,rgba(27,126,117,.25),transparent 30%),${C.bg}`,color:C.text,fontFamily:'PingFang SC, Microsoft YaHei, sans-serif'}}>
 {bgm&&<Audio src={staticFile('audio/bgm.mp3')} volume={0.055} startFrom={150}/>}<Audio src={staticFile('audio/voice.mp3')} volume={1.35}/>
 <Sequence from={0} durationInFrames={145}><Intro/></Sequence><Sequence from={145} durationInFrames={905}><Board/></Sequence><Sequence from={1050} durationInFrames={180}><Evidence/></Sequence><Sequence from={1230} durationInFrames={120}><Outro/></Sequence>
 <Sequence from={2} durationInFrames={55}><Audio src={staticFile('audio/impact-deep-whoosh.mp3')} volume={.55}/></Sequence>
 {[150,300,480,650,735,845].map((at,i)=><Sequence key={at} from={at} durationInFrames={40}><Audio src={staticFile(i%2?'audio/transition-soft.mp3':'audio/whoosh-fast.mp3')} volume={.28}/></Sequence>)}
 <Sequence from={945} durationInFrames={55}><Audio src={staticFile('audio/impact-deep-whoosh.mp3')} volume={.62}/></Sequence>
 <Sequence from={1050} durationInFrames={42}><Audio src={staticFile('audio/whoosh-big.mp3')} volume={.35}/></Sequence>
 <Sequence from={1228} durationInFrames={75}><Audio src={staticFile('audio/sparkle.mp3')} volume={.5}/></Sequence>
 </AbsoluteFill>};
