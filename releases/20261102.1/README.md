# 代码封版 20261102.1

标签 `release-20261102.1`，分支 `codex/release-20261102-1`。本次保存当前研发代码、两服已验收的公开运行文件与发布记录，继承国服 `release-cn-20261101.1`，国际服公开基线来自独立 `release-global-20261022.1`。助手版本保持 **1.3.6**。

| 内容 | 状态 | 精确恢复来源 |
| --- | --- | --- |
| 国服助手三平台1.3.6 | 已上线 | [正式清单及验收](../../docs/releases/companion-1.3.6-cn-20261102.md)；根目录Desktop包含后续Global文案适配，正式包以各自签名/hash为准 |
| 国服Backend | 业务镜像未重启，仅热更新助手清单 | `cn/backend-runtime.tar.gz`，232份文件，包含当前136清单 |
| 国服资料worker/Web | 未变 | 本仓库已有 `releases/cn-20261101.1/` 的196/366份文件包 |
| 国际服Backend/worker/Web | 性能与助手下载已更新；worker保持 | `global/` 的303/267/251份独立组件文件包 |
| 国服笔试网页及Backend截图查询配套 | **仅本地开发、自测，未部署国服** | 当前 `apps/web`、`apps/backend/app/modules/screenshot_answer.py`；不能把当前整仓构建当作线上等价版本 |

国际服保留原时间会员、收费、Creem、模型、语言及功能开关，见[实际发布记录](../../docs/releases/global-performance-companion-1.3.6-20261102.md)。国服保留模拟面试、笔试多屏、简历优化、SEO和状态/控制读取优化；本次Git封版不部署、不重启、不变更用户数据或账务。

`manifest.json` 绑定本次所有源码及公开证明、六组件完整清单和归档。运行文件按各自实际发布清单逐字封存：国服源码从前一固定Git基线恢复后仅带入已发布清单，国际服按实际候选303项名单取文件；不把忽略目录整包入库，也不以国服源码替代Global。原始生产配置、镜像层、凭据、用户资料、原始日志与安装包二进制不进入Git。正式安装包继续使用两服已验证的官方下载。

## 离线核验及恢复

在本标签检出目录执行，验证不访问网络、Docker或生产环境：

```bash
python3 -B releases/20261102.1/tools/verify_snapshot.py
python3 -B releases/20261102.1/tools/restore_snapshot.py --component global-backend --output ../offersteady-global-restored-20261102
```

输出目录必须不存在，父级不得是符号链接。组件可选 `cn-backend`、`cn-material-worker`、`cn-web`、`global-backend`、`global-material-worker`、`global-web`。工具只还原对应公开文件，不生成私有环境、不发布服务。Web恢复的是精确静态文件，Nginx配置分别见已有国服封版及本目录 `global/nginx.conf`。

Global原13份合成回归源码、所需历史代码/公开清单和评测样本一并保存。安装当前Backend测试依赖后，用相应Python环境执行：

```bash
python -B releases/20261102.1/tools/run_global_regressions.py
python -m pytest -q releases/20261102.1/tools/test_snapshot_tools.py
```

回归入口先完整核验封版，再在临时目录还原Global源码及测试所需的原相对布局，拒绝真实网络，排除4项专用PostgreSQL案例；不读取本地生产配置。本次从封存包实际还原后重跑Global业务204项通过、4项专用PostgreSQL案例排除；离线验证/恢复工具32项合成安全测试通过，四个OpenSpec变更strict通过，见[封版校验记录](verification.json)。此前Desktop401项等结果见正式发布记录，实体设备和长期P95限制仍保留。

未来开发从此不可变标签新建分支；发布仍须重新核对目标实际镜像、完整输入、有效配置和在线工作门禁。当前Global执行过的16份公开控制器输入保存在 `global/release-payload/`，仅用于来源证明，**不是新的部署授权**。精确生产回退使用已保存的固定镜像和服务器私有冻结配置，按对应发布记录重新检查归属及门禁；离线源文件恢复不能替代这些条件。
