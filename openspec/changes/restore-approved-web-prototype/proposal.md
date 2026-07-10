## Why

当前项目仍处于产品原型验证阶段，Web 原型本身就是最重要的产品资产之一。最近在推进后端与统一文档服务时，原型层的资料页表现和交互被连带改动，因此需要明确建立一次“恢复已批准原型表现”的变更，避免后续工程实现继续侵入原型层。

## What Changes

- 恢复 Web 原型中已批准的页面表现、文案和交互节奏，不因后端联调或服务抽象改变原型体验
- 明确区分“原型层 UI/交互”和“后端能力接入层”，要求后端升级不得默认改动原型页面行为
- 收敛资料页、上传适配层和相关说明文案中的误改，恢复到用户已确认的原型方案
- 为未来联调建立约束：如需接入新后端能力，应优先通过兼容适配器保持原型表现不变

## Capabilities

### New Capabilities
- `web-prototype-integrity`: 定义已批准 Web 原型在工程推进过程中必须保持的页面表现和交互完整性

### Modified Capabilities
- None

## Impact

- Affected frontend: `apps/web` 中的资料页、上传适配层和相关状态提示
- Affected workflow: 后续所有后端联调与服务接入都需要尊重原型层稳定性
- Affected implementation boundaries: 服务端能力可以继续演进，但默认不得驱动产品原型表现变化
