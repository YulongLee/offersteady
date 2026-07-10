## 1. Diagnose local access failure

- [x] 1.1 复现“本地网页原型访问不了”的具体表现，并区分是服务未启动、访问地址错误、脚本依赖未满足还是页面真实异常
- [x] 1.2 确认当前本地访问链路所依赖的命令、端口、预览方式和最小环境前提

## 2. Restore local access path

- [x] 2.1 修复阻断本地访问的前端启动、访问入口、预览链路或页面运行问题
- [x] 2.2 在不改变已批准原型体验的前提下，补齐必要的本地访问说明和诊断提示

## 3. Verify and hand off

- [x] 3.1 重新验证首页、登录、面试首页、资料页、准备页、实时页、积分页和使用说明页都可本地访问
- [x] 3.2 运行本地相关检查并记录验证结果
- [x] 3.3 运行 `openspec validate fix-local-web-prototype-access --strict`
