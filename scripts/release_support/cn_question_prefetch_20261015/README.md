# 国服问题预取发布支持：2026-10-15

归档本轮已发布的活动门禁、只读候选核对及发布控制器合成测试，供 Git 克隆后复核。11 份来源文件保持原始字节；测试路径无需修改。

- `active_work_gate.py`、候选 probe、配置摘要和发布控制器测试来自 `artifacts/cn-question-prefetch-20261015/release/`。
- `extra_idle_gate.py` 及其测试来自 `artifacts/cn-mock-flat-billing-20261015/`。
- `legacy-gates/` 保存本轮发布前下载并核对的三份既有门禁。

在仓库根目录、已安装 Backend 开发依赖的 Python 环境执行：

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=apps/backend .venv/bin/python -m pytest -p no:cacheprovider scripts/release_support/cn_question_prefetch_20261015 -q
```

归档后按上述命令验证：**158 项通过**。这些测试只验证合成门禁和发布控制流程。

三个测试文件使用合成数据替换外部服务；发布控制器测试从同一仓库读取 [release_cn_question_prefetch.py](../../release_cn_question_prefetch.py)。

实际发布仍须核对目标组件正在运行的 Image、完整源码与配置。`probe-expectations.json` 固定本轮候选的 app、Prompt、路由及受保护方法哈希；新版本须重新审核对应清单。

`candidate-probe.py` 须与匹配候选镜像及该清单共同使用，并提供从目标环境核对得到的 `--expected-config-sha`。`config-digest.py` 只打印指定配置字段的摘要。probe 使用隔离网络和只读容器，拒绝网络、数据库连接、写文件、子进程及线程启动，不进入应用生命周期。

本轮门禁组合为 `legacy-gates/` 三份门禁、`extra_idle_gate.py` 和 `active_work_gate.py`。生产执行由已批准发布流程统一核对版本、私有环境与活动工作。

## 来源文件 SHA-256

| 文件 | SHA-256 |
| --- | --- |
| [active_work_gate.py](active_work_gate.py) | `da76085bc835282ce70e13fbc442ae503b9134902f26c136db07524459db382d` |
| [extra_idle_gate.py](extra_idle_gate.py) | `9adfaeb79a25a56a2e041eb68d882281fbcc7efae1f5b34426917f10d93babfb` |
| [legacy-gates/idle_gate.py](legacy-gates/idle_gate.py) | `e5423b9dbf693b45060d400e3bf0578282da928ad71a22dc5abd477d087835ea` |
| [legacy-gates/check-idle.py](legacy-gates/check-idle.py) | `5ab1d802f432c9a77f89421935088f9bc86717593c896f48f636d994c19fb934` |
| [legacy-gates/readiness-idle.py](legacy-gates/readiness-idle.py) | `20f6c034e25028b9ab763660d37dcd7aa46ee4f6ea798080ddd4dafc0538ad5a` |
| [candidate-probe.py](candidate-probe.py) | `1d0286e59a06f093551dde931d35659fa6d259ac220f460b0d6749cd04d16252` |
| [config-digest.py](config-digest.py) | `d681c735b6e4195b2847d838af6ad57b06dfc6ebe636214f91abd7c5e13f6631` |
| [probe-expectations.json](probe-expectations.json) | `e77ae111261a22feda8943eb4568b66c2bec11ab7c3e56f6bb6317cdb487f4da` |
| [test_active_work_gate.py](test_active_work_gate.py) | `1edca74d5b17d149ca246ca1fcdadd2da60123571cf47c418983ebef4ab521f9` |
| [test_extra_idle_gate.py](test_extra_idle_gate.py) | `64c5ad34ba7834c65817a073ef5e199296cbd598ca21e99166cc0cacd55ccc59` |
| [test_release_cutover.py](test_release_cutover.py) | `7797ae75c4658c004a229cc564a98ac3175aea3658eccdda49045bb088219e15` |
