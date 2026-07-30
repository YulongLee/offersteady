## ADDED Requirements

### Requirement: 管理入口与用户端隔离
系统 SHALL 通过独立后台构建物和 `/api/v1/admin/*` 命名空间提供管理能力，并 SHALL NOT 改变现有用户端路由、页面和公开 API 契约。

#### Scenario: 后台功能默认关闭
- **WHEN** 生产环境未明确启用管理功能
- **THEN** 管理页面和管理 API 不可用，且用户端网站、API、面试和桌面助手继续正常工作

#### Scenario: 普通用户访问管理 API
- **WHEN** 仅持有有效普通用户会话的用户访问管理 API
- **THEN** 系统拒绝访问且不因用户名或手机号赋予管理权限

### Requirement: 显式管理员身份
系统 SHALL 使用独立管理员授权记录关联真实用户 ID，并 SHALL 维护管理员角色、状态和授权版本。

#### Scenario: 名为 admin 的普通账号
- **WHEN** 用户名为 `admin` 但不存在有效管理员授权
- **THEN** 系统将其视为普通用户并拒绝管理访问

#### Scenario: 管理授权被停用
- **WHEN** 管理员授权被停用或授权版本提升
- **THEN** 该管理员现有管理会话失效

### Requirement: 管理员 MFA 与会话安全
系统 SHALL 在签发管理会话前验证账号身份和 TOTP MFA，并 SHALL 对高风险动作要求近期 MFA 证明。

#### Scenario: 缺少 MFA
- **WHEN** 已登录用户未完成有效 MFA 验证
- **THEN** 系统不签发管理会话

#### Scenario: 高风险操作的验证已过期
- **WHEN** 管理员执行财务调整或管理员授权操作且近期 MFA 已过期
- **THEN** 系统要求重新验证并在验证成功前拒绝操作

### Requirement: 拒绝优先的最小权限
系统 SHALL 按动作权限执行 RBAC，未明确授权的操作 SHALL 被拒绝。

#### Scenario: 客服尝试调整积分
- **WHEN** 仅拥有用户查询权限的客服角色请求调整积分
- **THEN** 系统拒绝请求并生成拒绝审计事件

#### Scenario: 财务角色执行允许的对账
- **WHEN** 具备 `payments.reconcile` 权限的管理员提交有效对账重试
- **THEN** 系统允许进入受控业务命令

### Requirement: 首位超级管理员离线引导
系统 SHALL 仅通过服务器侧受控命令创建首位超级管理员，公共 API SHALL NOT 提供自助提升为超级管理员的能力。

#### Scenario: 尝试通过公共接口授予超级管理员
- **WHEN** 客户端请求通过公共或管理 API 自助创建首位超级管理员
- **THEN** 系统拒绝请求
