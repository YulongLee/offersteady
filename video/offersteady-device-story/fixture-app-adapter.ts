import {fixtureAdapter, syntheticState} from '../../apps/web/src/test-state';
syntheticState.account.displayName = '演示用户';
syntheticState.speaker.pendingQuestion = null;
syntheticState.speaker.transcripts = syntheticState.speaker.transcripts.slice(0,2);
syntheticState.questions = syntheticState.questions.slice(0,1);
const q = syntheticState.questions[0];
q.advice.outline = ['我负责过一个跨端工作台项目，主要解决页面加载慢、交互卡顿的问题。'];
q.advice.detail = `简单回答
我负责过一个跨端工作台项目，主要解决页面加载慢、交互卡顿的问题。

---

详细回答
**项目背景**
工作台模块逐渐增多，首屏资源和长列表成为主要瓶颈。

**我的行动**
通过性能监控定位问题，结合路由拆包、按需加载和列表虚拟化逐步优化。

**方案取舍**
优先解决高频路径，并通过灰度验证与监控反馈控制改动风险。`;
q.advice.provenance.fixedSourceCount = 2;
q.advice.provenance.retrievedSourceCount = 1;
q.advice.provenance.usedSources.forEach((s, i) => {s.contextRole = i === 2 ? 'retrieved' : 'fixed';});
if (location.search.includes('capture=screenshot')) {
q.text = '设计一个高并发秒杀系统，如何避免超卖？';
q.input = 'screenshot';
q.advice.detail = `简单回答
用限流削峰、原子扣减和异步下单分层处理，保证库存不被重复扣减。

---

详细回答
**流量入口**
网关限流与资格校验，先拦截无效请求。

**库存一致性**
Redis 原子预扣库存，订单幂等落库，失败补偿回补。

**稳定性保障**
通过消息队列削峰，结合监控与降级保护核心链路。`;
q.advice.provenance.usedSources = [];
q.advice.provenance.fixedSourceCount=0;
q.advice.provenance.retrievedSourceCount=0;
}
export const runtimeConfig = {apiBaseUrl: 'http://127.0.0.1:9',appEnvironment:'capture'};
export const interviewAppAdapter = fixtureAdapter;
