## Why

当前产品原型已经明确支持“截图回答”这个核心场景，但服务端还没有一条正式的 Screenshot Answer Service 去承接图片上传、视觉模型调用、回答流和历史记录。现在需要建立独立截图回答链路，让系统能对笔试题、系统设计图、题目截图等内容快速生成可读答案，同时继续复用 Session、Retrieval 和 Prompt 资产。

## What Changes

- 新增统一 Screenshot Answer Service，负责从截图输入生成 AI 回答。
- 建立截图上传、图片预处理、Vision API、Prompt Builder、Streaming Answer 和历史记录的统一服务边界。
- 支持一场会话内上传多张截图，并在一次截图回答任务中按顺序组织多图上下文。
- 支持 Resume、JD、Knowledge 自动增强，让截图回答可以结合本场资料和检索依据。
- 建立 Screenshot Chat API、会话级截图回答历史、使用记录和流式输出契约。
- 保持当前产品原型交互不变：截图仍通过面试中的截图回答入口发起，不新增额外页面流程。

## Capabilities

### New Capabilities
- `screenshot-answer-service`: 定义截图上传、视觉理解、会话增强、流式回答和截图回答历史能力

### Modified Capabilities
- None.

## Impact

- Affected code: `apps/backend` 的 screenshot-answer 模块、图片上传适配、vision gateway、prompt builder、streaming 和会话级历史记录
- APIs: 新增 Screenshot Upload / Screenshot Answer API、多图回答输入结构、流式输出和历史查询接口
- Dependencies: Interview Session Service、Knowledge Retrieval Service、Vision provider adapter、Prompt assets、token usage and history storage
- AI assets: 新增截图回答 Prompt Template、Vision 输入组织规则与 `ai/evals/` 样例
- Product behavior: 不改变前端原型截图交互，只提供正式后端能力
