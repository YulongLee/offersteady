# 国服设备状态减负：本地候选 2026-11-02

> 后续状态：用户于2026-11-03授权发布；本候选已完成[国服Backend上线与独立验收](cn-device-status-20261103.1.md)。以下保留昨日本地开发和测试记录。

状态：**本地开发、自测与独立审查完成，未部署。** 用户要求晚上有时间再更新；本记录不构成自动发布指令。没有生产重启、真实会话变更、助手更新或 Git 提交/推送。

本轮仅处理国服 Backend 的设备状态上报，移除该路径不必要的资料读取和主事件循环阻塞，并增加分段观测。网页、助手 1.3.6、普通/笔试/模拟面试能力、收费、模型、Prompt、检索/预取、worker、数据库 schema/索引及依赖保持，连接池仍关闭。

## 已完成的改动

CN `device-status` 将绑定解析及状态发布作为一次工作交给既有有界控制执行器。原认证依赖保持，未提供手动码时先按原合同解析登录用户；Global 继续原分支。不增加线程池、不调整线程数、队列限制或轮询频率。工作失败不重放，取消后已启动的工作仍可能完成一次，沿用原执行器合同。

CN 专用服务入口复用已有五字段 `get_control_state`，替换两次完整会话读取。仍保留两次独立权威检查：绑定时检查 preparing/live、绑定状态、generation 和心跳；最终发布检查 owner/存在性。绑定查找 fallback、404/403/410、原 payload 过滤和 `_save_event` 退休保护均保留；并发刚结束的会话不新增状态门禁。没有跨请求权限缓存。其它采集授权、绑定查询和资料感知业务保持原完整读取。

每 20 次 CN 状态工作采样一次，私有日志前缀为 `cn_device_status_timing`，只含固定字段及数值：排队/工作总时长、DB 获取/执行/取数、绑定仓库操作与事件保存。连接获取只包围连接上下文进入，不包含 cursor、SQL 或事务退出。线程作用域显式安装、清理；采样器、计时器或日志失败不改变业务结果，采样对象构造失败也隔离继承上下文。

样本不含认证、HTTP 网络或浏览器呈现；仓库计时包含其序列化开销，不能当纯 Redis 网络耗时。相位可能嵌套，不应简单相加。日志无用户、会话、设备或请求标识，无 SQL/参数、凭据、原 payload 或异常文字。

## 实际基线与候选

来源为 [release-20261102.1 的实际 CN 运行归档](../../releases/20261102.1/README.md)，实际 Backend 镜像 `sha256:c62df7ddbb92627de83c7c2733574c862678b120a11d051b346b9d13abfcf58a`。封存 232 输入中包含当天热更新的助手下载清单。根目录尚未上线的笔试 `screenshot_answer.py` 配套已明确排除。

最终本地候选在 `artifacts/cn-device-status-local-20261102/candidate-final/`。只替换三个原文件、新增一个文件，共 233 输入；229 份非目标文件内容与权限保持。改动文件为 realtime 路由、realtime service、PG session repository 与新计时模块。完整 Schema 与封存实际 **203 条 API 定义完全一致**，同一合成环境的 **344 项 Settings 逐值指纹一致**，池为 false；未读取或修改生产私有环境。157 份有效 Python 编译通过。运行 Schema 探针没有进入应用 lifespan，网络请求和线程启动均为 0。

[本地组装工具](../../scripts/build_cn_device_status_candidate.py) 校验封存归档、清单、来源及输入，再按固定四文件允许列表输出到新目录并读回 SHA；不调用 Docker、SSH、Git 或网络。测试产生的候选目录缓存已清除，最终目录只含 233 输入及一份本地候选清单。

## 自测结果

- 最终独立候选回归：**497 通过、60 跳过、0 失败**。覆盖本轮新增 92 项，以及鉴权、控制/心跳/状态读取、资源回收、实时协议、截图、笔试收费、模拟面试权限/截止/清理、账务及机器码绑定到状态可见的原合成链路。
- 补充一次全新隔离的 localhost PostgreSQL：**30 通过、0 跳过**，其中 2 项为前述跳过的真实 PG 控制投影测试，28 项为计时重复回归。仅合成库、临时内存数据，不接触现存数据库；自己创建的临时容器已删除。该补充验证已有投影的 SQL/事务及当前状态可见性，不代表整个设备状态功能的真实生产端到端测试。
- 独立审查重新运行 **92 项新增回归全部通过**，重核全部 233 SHA、229 非目标内容/权限、完整 Schema 及 Settings；9 项授权/采集/事件方法与过滤表达式的 AST 对照保持。
- 固定 12 份合成资料的同一合法状态上报：完整会话读取 **2→0**，资料读取 **24→0**；保留 **2 次轻量权威校验、1 次事件保存**。故意缺失的合成源资料触发旧版会话写入 2 次，新版为 0；不能解释为每次生产请求原本都会写 2 次。
- 慢同步仓库阻塞期间其它协程可推进；绑定替换/过期、generation、owner、心跳、删除、并发最终检查、Global/旧请求、错误与取消不重放、日志隐私和观测故障隔离均有回归。

尚未执行的独立用例为 58 项：57 项需要其它专用数据库配置，1 项仅适用于 Global。本轮没有生产压测、真实模型、真实面试、付款或物理音频设备测试。已存在的 Starlette/httpx 测试客户端弃用提示保留。首次候选回归有一条相对迁移路径因测试工作目录错误而失败，修正工作目录后原断言通过，未修改产品或弱化测试；原结果保留。

本地减负计数和兼容性检查不能换算线上整体 P95 降幅，也不能证明数据库是唯一瓶颈。后续若上线，需用正常流量中的相位样本区分建连、SQL、仓库和调度，再决定连接池或检索是否进入下一轮。

## 验证重放与后续

本轮分支为 `codex/cn-device-status-read-20261102`，起点 `75d87e6d196e5bf3edc228aac7feafaa963a7c4d`，未提交。直接复跑新增测试可在项目根目录执行：

```bash
PYTHONPATH=apps/backend /Users/liyulong/liyulong/1_projects/offersteady/.venv/bin/python -B -m pytest apps/backend/tests/test_cn_device_status_route.py apps/backend/tests/test_cn_device_status_service.py apps/backend/tests/test_cn_device_status_timing.py apps/backend/tests/test_cn_device_status_candidate.py -q
npx openspec validate lighten-cn-device-status-processing --strict
```

实际候选测试通过专用 import guard 确保从 `candidate-final` 导入，并阻止真实网络、清空远程测试 opt-in。完整选择、执行器、日志、JUnit、独立探针与真实 PG 验证材料位于 `artifacts/cn-device-status-local-20261102/`；[脱敏最终汇总](cn-device-status-local-20261102.1/verification.json)、[最终四文件清单](cn-device-status-local-20261102.1/delta-manifest.json)、[独立审查](cn-device-status-local-20261102.1/independent-review.json) 随文档保存。

晚间用户另行指示部署后，必须重新核对实际运行镜像、完整输入、下载热清单及私有配置，检查所有用户工作门禁，等待无进行中的面试，再准备固定镜像和回退。不得全量复制根目录 Backend、混入待发笔试配套或自动重放旧控制器。

需求与场景见 [OpenSpec 变更](../../openspec/changes/lighten-cn-device-status-processing/proposal.md)。
