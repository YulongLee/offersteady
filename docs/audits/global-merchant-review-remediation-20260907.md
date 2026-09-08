# OfferSteady 商户审核整改：开发与验收记录

日期：2026-09-07。本记录保留当时的本地验收结果。**随后已按用户明确授权，于 20:48 左右部署国际站，生产验收通过**，详见[发布记录](../releases/global-review-20260907.1.md)。下文“未部署”和线上旧内容描述均为部署前基线，不是当前生产状态。

本次依据用户附件实施，最终邮箱选择为 **contact@oneshowailab.com**。没有改成 support@offersteady.com。按 openspec-apply-change 流程执行 `remediate-global-merchant-review`，只处理 Global 公开页面，不修改中国站、后端、数据库、登录、面试、Companion、ASR、RAG、AI、支付接口或生产环境配置。

## 1–2. 文件清单与改动

| 文件 | 本次内容 |
| --- | --- |
| [public-review-pages.json](../../apps/web-global/src/public-review-pages.json) | 统一产品定位、付款状态说明、实际套餐计费及权益生效时间；完善 Terms 15 项、Privacy、Refund、About、Contact；保留实际经营主体及支持邮箱。 |
| [public-review-pages.ts](../../apps/web-global/src/public-review-pages.ts) | 为共享文案、计费方式、访问期限和日期增加类型。 |
| [App.tsx](../../apps/web-global/src/App.tsx) | 仅公开首页 Hero、套餐展示、付款状态、Footer 经营主体及首页 metadata 文案调整；核心业务处理未改。 |
| [PublicReviewPage.tsx](../../apps/web-global/src/PublicReviewPage.tsx) | 公开页面显示计费方式、权益起算时间、政策生效日期和经营主体；四个付费按钮仍 disabled。 |
| [LegalPage.tsx](../../apps/web-global/src/LegalPage.tsx) | 旧入口复用同一份政策，移除重复的开发版政策正文；保留旧隐私选择控件及请求逻辑。 |
| [styles.css](../../apps/web-global/src/styles.css) | 套餐披露、长按钮换行样式；仅公开页面品牌锁定区在超窄屏换行，解决 320px 横向溢出。 |
| [index.html](../../apps/web-global/index.html) | 静态 Hero/套餐、结构化 Offer 信息、metadata、可见经营主体和完整 Footer。 |
| [guide.html](../../apps/web-global/guide.html) | 清除未参与生产构建的旧模板中的过期付款句子；没有重新开放用户手册路由。 |
| [generate-review-pages.mjs](../../apps/web-global/scripts/generate-review-pages.mjs) | 首页 Hero/套餐及 Offer schema 读取共享目录；生成独立页面、Footer、政策日期和 GEO 信息；静态付费控件使用真正 disabled 按钮。 |
| [verify-merchant-review-pages.mjs](../../apps/web-global/scripts/verify-merchant-review-pages.mjs) | 验证经营主体、日期、计费/起算时间、disabled 控件和旧词禁入；继续验证独立 metadata、canonical、社交卡片、JSON-LD、sitemap/robots。 |
| [check-review-http.mjs](../../apps/web-global/scripts/check-review-http.mjs) | 新增只读 curl 检查，默认验证本地新构建；`--baseline` 模式读取线上现状而不冒充已更新。 |
| [global-product.test.tsx](../../apps/web-global/src/global-product.test.tsx) | 更新 Hero/按钮断言；仅允许要求展示的注册主体中文，其余英文页面继续检查中文泄漏；点击禁用按钮不得发起请求。 |
| [public-commercial-disclosures.test.tsx](../../apps/web-global/src/public-commercial-disclosures.test.tsx) | 新增 11 项回归用例，覆盖价格、计费、7 个页面经营主体/邮箱/导航、条款完整性、退款和隐私披露。 |
| [OpenSpec 变更](../../openspec/changes/remediate-global-merchant-review/proposal.md) | proposal、design、spec、tasks 记录范围、验收与风险。 |

生成器同步更新 15 个公开页面的 `index.html`：pricing、terms、privacy、refund-policy、contact、about、security、features、features/ai-interview-assistant、features/realtime-interview、features/screenshot-answer、features/interview-review、guides、interview-questions、download。其他功能页正文没有批量重写，主要同步公共 Footer。

同时生成 `public/sitemap.xml`、`public/llms.txt`、`public/llms-full.txt`、`public/public-facts.json` 和构建产物。`robots.txt` 保持现有规则，没有修改 Nginx。未添加依赖、虚构评价、人物、认证图标或英文注册公司名；既有用户提供的反馈和视频未重写，本次未验证其来源或逐帧/音轨审计。

## 3. Home 最终关键文案

标题：

> AI Interview Assistance, Grounded in Your Experience

产品描述：

> OfferSteady helps job seekers prepare for and navigate interviews with real-time transcription, contextual AI guidance, resume and job-description based assistance, and interview preparation tools.

使用边界：

> AI-generated guidance is designed to support your interview preparation and communication. Always verify responses based on your real experience and follow your interview organiser's policies regarding AI assistance.

销售内容：

> Digital access to interview assistance tools, delivered to your account.

首页结构、产品视频、下载、功能、对比、既有反馈与套餐的位置保留，没有改成另一套视觉设计。

## 4. Pricing 最终套餐与支付状态

价格来自当日生产只读 `/api/v1/global-commerce/catalogue`，与本地 catalogue v2 迁移/权益代码核对，未改价。

| 套餐 | 价格/期限 | 计费 | 权益 |
| --- | --- | --- | --- |
| Free | $0 | 一次性免费额度 | 15 分钟 Copilot、3 次 Screen Assist；不含 Resume/JD、知识库、Written Exam 模式，不按月补充。 |
| Interview Day Pass | $9.99 / 24 hours | 一次性，不续费 | 180 分钟 Copilot、无限 Screen Assist、Resume/JD、Written Exam 模式；不含知识库。 |
| Pro Weekly | $49.99 / 7 days | 一次性，不续费 | 无限 Copilot/Screen Assist、Resume/JD、知识资料、Written Exam 和会话复盘。 |
| Pro Monthly | $99.99/month | 月度订阅，取消前自动续费 | 同上，在已支付账期内有效。 |
| Job Hunt | $199.99 / 90 days | 一次性，不续费 | 同 Pro 完整权益，90 天有效。 |

权益交付到购买账号；从支付机构确认的付款时间起算，不从第一次面试开始。月订阅以支付确认及该账期结束时间为准。无限使用不代表取消技术限制、账号限制或正常使用规则。价格以美元展示，最终税费及总额须在授权付款前展示。

Free：`Start Free` 指向 `/login`。

四个付费按钮：`Checkout requires provider approval`，全部禁用，没有链接到假支付页。

支付说明：

> Online checkout is temporarily unavailable. Live payments require payment provider merchant approval and completed production configuration. No payment is taken through the disabled controls on this site.

实测 readiness 是 Test、ready=false、product_mappings_missing。已有测试配置不等于生产收款开通，因此文案没有声称审核已通过、正在等待一个必然的通过结果，或只差一项审核。

## 5. Terms 关键条款

覆盖用户要求的 15 个主题：Service Description、Eligibility、Account Responsibility、AI-generated Content、Acceptable Use、Interview Rules and Third-party Policies、Paid Services、Billing、Refunds、Intellectual Property、Privacy、Limitation of Liability、Termination、Governing Terms、Contact Information。

- 明确卖的是数字软件访问权限，不是招聘/就业中介或就业结果。
- AI 可能出错，用户必须核验并依据真实经历回答。
- 必须遵循组织方录音、截图、保密、AI 与评测规则；禁止辅助的场景不得启用对应功能。
- 禁止冒名、虚构资历、违反保密、规避评测安全措施及欺诈。
- 说明一次性购买/月自动续费、支付确认起算、取消续费与退款的区别。
- 用户保留其依法拥有的上传内容权利；只授权为所选服务必要的处理。
- 说明中断、延迟和 AI 误差限制，不保证招聘结果。
- 保留不得排除的法定责任、消费者权利和救济，没有虚构仲裁地、注册英文名或一律免责条款。

这属于基于现有实现的政策草案，不是法律合规认证；正式发布前仍应由经营者确认，必要时法律审核。

## 6. Privacy 涉及的数据和实现依据

已披露账号邮箱/认证数据、简历、JD、其他上传文档、解析文本/检索向量、实时转录/音频衍生文字、问题及生成答案、用户触发的截图/识别结果、设备/浏览器/请求信息、使用与性能指标、支持请求、支付订单/客户/订阅/金额/退款状态等元数据。

- 第三方支付处理付款；OfferSteady 不直接保存完整银行卡信息。
- 原始音频默认不存储，不等于转录文字及生成结果不留存。
- 浏览器认证/偏好/会话存储及条件触发的推广归因如实披露，没有宣称完全无 Cookie/无统计。
- 删除先标记再排队清理，可重试；没有写成立即从所有副本永久擦除。
- 描述服务、安全、争议及法律所需留存，不虚构已经核准的生产固定天数。
- 按类别说明基础设施、解析、语音、AI、邮件、支付等服务商；不虚构认证、统一数据驻留地区或供应商绝不训练的保证。
- 提供查阅、更正、删除、导出及适用法律下其他权利的支持渠道。

核对过的代码包括 `authentication_service.py` 的密码哈希、`document_service.py` 的删除标记/队列、`material_deletion.py` 和 worker 的存储清理、实时转录仓库留存设置、截图任务清理、`promotion-attribution.ts`、`global_checkout_service.py` 的支付事件/权益处理。未更改这些实现，也没有将真实用户资料写入测试夹具。

## 7. Refund 最终规则

生效日期：September 7, 2026。

- 保留原公开规则：首次购买后 14 个自然日内可申请；**不是 14 天无条件退款**。用户尚未另行确认更改该期限，因此没有静默缩减已有申请权利。
- 根据套餐类型、实际使用、订单及问题情况和适用消费者法律审查。
- 可审查重复/错误扣款、购买权限未交付、无法解决的实质技术问题；对续费错误等可联系支持，不机械限制在初次购买窗口。
- 发送账号邮箱、订单信息、申请原因至 contact@oneshowailab.com。
- 保留 3 个工作日内回复的目标；不是退款必然到账时限。
- 批准后经支付机构退回原支付方式；银行/支付机构决定到账时间，相应权益可能调整或撤销。
- 取消月订阅只停止后续续费，不自动退还历史扣款。
- 不承诺仅因没有拿到工作就退款；强制性消费者权利优先。

## 8. 最终主体与联系信息

- Product：OfferSteady
- Operator：杭州临平知界智能技术工作室（个体工商户）
- Location：Hangzhou, China
- Website：https://offersteady.com
- Support：contact@oneshowailab.com
- OneShow AI Lab 作为品牌，与注册经营主体区分。

首页及公开页面 Footer 可见经营主体，不只存在于 JSON-LD。About/Contact/Terms/Privacy/Refund 支持邮箱一致。

## 9–10. 旧文案和关键词检查

对国际站源码、生成脚本和最终 `dist` 文本/HTML/JSON/JS/XML 执行大小写不敏感搜索；中国站、历史需求文档与第三方依赖不是本次可删除的文案。

| 关键词 | 最终生产构建可发布文件 | 源码/脚本残留性质 |
| --- | --- | --- |
| coming soon | 0 | 测试或旧词阻断检查 |
| checkout is not active | 0 | 测试或旧词阻断检查 |
| paid checkout | 0 | 测试或旧词阻断检查 |
| cheat | 0 | 禁用宣传词检查 |
| undetectable | 0 | 测试或禁用宣传词检查 |
| guaranteed offer | 0 | 禁用宣传词检查 |
| secretly | 0 | 禁用宣传词检查 |
| bypass | 0 | 测试或禁用宣传词检查 |

保留检测规则本身，不能为了“搜索零命中”删除保护性测试。未宣称视频音轨、截图里所有文字也已完成机器全文审计。

**线上目前仍是旧内容**：基线 curl 中首页上述三类旧支付短语合计 10 次，Pricing 14 次，Terms 2 次，Refund 2 次（含结构化数据的重复计数）。本地新构建为 0；未部署不能报告线上已清除。

## 11. HTTP、SEO 和审核路径

| URL | 生产基线 curl | 本地新构建 curl | 新构建独立正文/metadata |
| --- | --- | --- | --- |
| / | 成功获取过 200；后续一次下载超时 | 200 | 新 Hero、套餐、经营主体 |
| /pricing | 200 | 200 | 五个实际套餐、计费/起算、禁用按钮 |
| /terms | 200 | 200 | 15 项条款 |
| /privacy | 200 | 200 | 真实数据类别与处理说明 |
| /refund-policy | 200 | 200 | 独立退款政策 |
| /about | 200 | 200 | 产品、经营主体、所在地、支持邮箱 |
| /contact | 一次连接超时，重试 200 | 200 | 联系方式和经营主体 |
| /security | 200 | 200 | 安全实践及边界 |
| /robots.txt | 200 | 200 | sitemap 正确，无公开政策屏蔽 |
| /sitemap.xml | 200 | 200 | 16 条 canonical URL；新构建日期 2026-09-07 |

本地 HTTP 检查不执行 JavaScript，逐页验证 title、description、canonical、H1、第一段独立正文、邮箱、主体和旧文案；Pricing 额外验证所有价格、计费及起算时间。静态验证覆盖全部 16 条可索引 URL、JSON-LD 和社交 metadata。

只读检查现有 Nginx，公开政策路径使用各自 `/$public_page/index.html`，不存在此次检查所见的统一首页 fallback。本次没有登录服务器切换版本或更改 CDN/Nginx。两次公网超时不能仅凭该结果定位为服务器故障；不报告稳定性问题已解决。

审核员按 Home → Pricing → About → Contact → Terms → Privacy → Refund 可看到：真实经营者、服务对象、软件服务内容、实际价格/权益、数字交付时间、退款流程、联系渠道、数据处理和支付暂不可用的两个前提。使用条款明确禁止欺诈和违背组织方要求，未隐瞒实际实时语音/截图功能。

## 12. 验证结果

- `npm test --workspace @offersteady/web-global`：**9 个文件、83 项测试通过**。
- `npm run typecheck --workspace @offersteady/web-global`：通过。
- `npm run test:copy --workspace @offersteady/web-global`：通过，648 条显式英文文案检查。
- 生产参数本地 build：通过；初次无参数运行被正常的生产参数 guard 拦截，补齐后成功。
- `npm run test:merchant-review --workspace @offersteady/web-global`：通过，16 条可索引 URL。
- `node apps/web-global/scripts/check-review-http.mjs`：10 个本地 HTTP 路径全部通过。
- `openspec validate remediate-global-merchant-review --strict`：通过。
- 项目未配置独立 `lint` 命令，**没有声称 lint 已通过**。
- Headless Chrome：1440、390、320px 首页和 Pricing 检查；5 张套餐卡均无内部溢出，4 个付费按钮禁用；320px 各政策正文无溢出；修复公开品牌换行后全页宽度与视口一致。截图是本地开发预览，不是生产截图。
- 保留既有 Vite 主包 >500kB 警告。新主包 gzip 164.59kB，上一反馈版发布记录为 161.67kB，约增加 2.92kB。没有新增运行时网络请求、依赖或后台任务；没有声称实际用户端性能提升或零开销。

复现构建：

```sh
VITE_APP_ENV=production VITE_API_BASE_URL=/ VITE_PUBLIC_APP_VERSION=global-review-remediation-20260907.local VITE_GLOBAL_COMMERCE_ENABLED=true VITE_GLOBAL_COMMERCE_PROVIDER=creem npm run build --workspace @offersteady/web-global
```

这里是本地构建参数，不是修改线上支付配置。界面禁用状态和真实支付链路未启用。

预览：[首页手机](../../design/previews/global-review-remediation/home-390.png)、[首页超窄屏](../../design/previews/global-review-remediation/home-320.png)、[Pricing 桌面](../../design/previews/global-review-remediation/pricing-1440.png)、[Pricing 手机](../../design/previews/global-review-remediation/pricing-390.png)。

## 发布前仍需经营者处理

1. 确认本次政策及现有 14 天申请窗口、3 个工作日回复目标可执行；必要时法律审核。
2. Creem Business Details 与网站的注册主体、网址、支持邮箱保持一致。保持最终选定 contact@oneshowailab.com；网站改动不意味着支付方一定接受这个邮箱域名。
3. 先确认 Business Verification 是可补充材料的状态还是最终拒绝。Creem 官方区分 Changes requested 和 Rejected，后者对该 store 的审核为最终结果；整改页面本身不能承诺恢复申请或保证批准。参见 [Creem Account Reviews](https://docs.creem.io/merchant-of-record/account-reviews/account-reviews)。
4. 保留现有反馈的真实原始记录和展示授权；本次没有新增反馈或验证其真实性，没有添加“认证评价”标签。
5. 部署仍是下一步：本次没有部署授权扩展、生产容器重启或真实支付测试。部署后必须重新运行生产 curl 检查（不带 `--baseline`）再声明生产整改完成。
