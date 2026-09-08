# 面试稳官网宣传片设计 Spec

状态：共同创作已确认制作  
日期：2026-09-03

## 产品简报

- 用途：官网横版产品展示。
- 受众：处于真实面试现场、需要辅助整理思路的中文求职者。
- 核心承诺：现场听懂问题，结合用户自己的简历、目标 JD 与知识库组织回答建议。
- 必须展示：实时聆听、个人资料汇聚、结构化回答与来源、截图题、灵活选择、面试复盘。
- 品牌主张：面试就选面试稳。价格稳，回答稳，面试更稳。
- 价值边界：产品辅助用户组织回答，不替用户虚构经历或隐蔽代答；用户触发、来源可核对。

## 需求到执行决策

| 已确认需求 | 项目/用户依据 | 执行决定 |
|---|---|---|
| 官网产品展示 | 用户确认官网投放 | 60 秒横版，信息完整、静音可读 |
| 现场辅助优先 | 用户明确倾向面试现场辅助 | 前 36 秒持续围绕听题、资料与回答展开 |
| 不展示具体金额 | 用户明确要求 | 价格截图在采集态替换为“成本价使用” |
| 灵活选择 | 官网已有按点与按天产品结构 | 只呈现按次、按天与按节奏选择的概念 |
| 无配音 | 用户确认宣传片不用配音 | tech-house BGM + 电影系 SFX；字幕独立叙事 |
| 数据安全 | 项目规范与产品隐私边界 | 使用真实 UI 与合成内容，不采集账户、客户、简历或会话数据 |

## 视觉方向

用户确认采用 **A「稳态控制台」为主体 + C「三重稳」作为结构与收尾**。

- Styleframe：[styleframe-guided.html](./styleframe-guided.html)
- 对比图：[out/styleframes/guided-styleframes.png](./out/styleframes/guided-styleframes.png)
- 背景：`#070b12` / `#080c13`
- 表面：`#0d141f` / `#121c29`
- 正文：`#f5f8fb`
- 次级文字：`#a9b5c4`
- 品牌强调：`#56e6b1` / `#a8f5d9`
- 字体：Inter / 系统无衬线；英文 kicker 使用 SFMono / Menlo。
- 材质：深色工作台、细网格、低透明玻璃、克制薄荷绿体积光。
- 相机：正视优先，缓慢稳定推进；禁手持抖动。
- 文字：叙事字幕 60px 档，辅助文字不低于 32px。
- 动效性格：专业信赖与平静关怀之间；基础入场 21–32f，无装饰性回弹；只有落地隐喻允许轻过冲。

## 功能到镜头映射

| 功能 | 首选镜头卡 / 变体 | 准确 demo |
|---|---|---|
| 品牌主张 | `lead-word-zoom-assemble · lead-word-zoom-assemble` | `demos/typography/lead-word-zoom-assemble/LeadWordZoomAssemble.tsx` |
| 实时听懂问题 | `voice-waveform-live · voice-waveform-live` | `demos/interaction/voice-waveform-live/VoiceWaveformLive.tsx` |
| 个人信息汇聚 | `bezier-source-converge-merge · bezier-source-converge-merge` | `demos/ui-entrance/bezier-source-converge-merge/BezierSourceConvergeMerge.tsx` |
| 组织回答 | `ai-stream-response · ai-stream-response` | `demos/interaction/ai-stream-response/StreamResponse.tsx` |
| 截图题 | `scanline-annotate-focus · scanline-annotate-focus` | `demos/effects/scanline-annotate-focus/ScanlineAnnotateFocus.tsx` |
| 灵活选择 | `picker-carousel-feature-cycle · picker-carousel-feature-cycle` | `demos/interaction/picker-carousel-feature-cycle/PickerCarouselFeatureCycle.tsx` |
| 面试复盘 | `timeline-travel · timeline-travel` | `demos/data/timeline-travel/TimelineTravel.tsx` |
| 三重稳收尾 | `value-stagger-gradient · value-stagger-gradient` | `demos/ui-entrance/value-stagger-gradient/ValueStaggerGradient.tsx` |

所有卡名和 style-key 已由 `gallery/api/library.json` 校验。适配只替换品牌 token、真实产品截图、合成内容与构图；保留配方的动作语法、缓动关系、停顿与命门参数。

## 最终分镜与帧级时间轴

| # | 时间 / 帧 | 功能信息 | 镜头卡与主动作 | 素材 | 字幕 / SFX | 验收帧 |
|---|---|---|---|---|---|---|
| 1 | 00:00–00:05.5 / 0–164 | 品牌定位 | `lead-word-zoom-assemble`；品牌词先占满再组成主张 | 品牌图标与 tokens | 面试就选面试稳。/ riser、soft impact | 52 / 136 |
| 2 | 00:05.5–00:13 / 165–389 | 实时聆听 | `voice-waveform-live`；说—停—说—提交 | `live-full.png` | 现场听懂问题，跟上面试节奏。/ submit pop | 236 / 356 |
| 3 | 00:13–00:20 / 390–599 | 资料汇聚 | `bezier-source-converge-merge`；三路沿真实曲线汇聚 | 真实 UI + 合成资料标签 | 回答有依据，表达才更像你。/ data whoosh | 456 / 566 |
| 4 | 00:20–00:29 / 600–869 | 组织回答 | `ai-stream-response`；摘要先到，证据随后，完成态静止 | `live-answer-workspace.png` | 关键点先到，回答逻辑随后补齐。/ row ticks | 684 / 824 |
| 5 | 00:29–00:36 / 870–1079 | 截图题 | `scanline-annotate-focus`；先扫到，再框选标注 | 真实工作台 + 合成技术题 | 截图题，也能快速抓住重点。/ scan、focus | 936 / 1044 |
| 6 | 00:36–00:43 / 1080–1289 | 灵活选择 | `picker-carousel-feature-cycle`；内容穿过固定焦点并吸附 | `landing-pricing-full.png`（金额脱敏） | 成本价使用。按次、按天，灵活选择。/ snap | 1152 / 1260 |
| 7 | 00:43–00:48 / 1290–1439 | 复盘 | `timeline-travel`；沿问题—回答—建议横移，急停至“复盘完成”状态卡 | 真实复盘切片 + 元素级完成态 | 结束以后，关键节点随时回看。/ whoosh、impact | 1342 / 1410 |
| 8 | 00:48–01:00 / 1440–1799 | 三重稳 | `value-stagger-gradient`；状态柱铺开、中心脉冲、价值落定 | 品牌图标与三个价值卡 | 价格稳。回答稳。面试更稳。/ riser→impact→sparkle | 1538 / 1738 |

总时长 1800f，30fps。转场包含在相邻镜头预算内。开场主体动作超过 3 秒；最终品牌主张静止超过 1 秒；批量动效均保留至少 0.5 秒终态。

## 素材与数据口径

- 真实页面最终素材以 1920×1080 viewport、2× device scale 采集。
- `public/textures/layout.json` 保存页面高度与元素 bbox。
- `capture-product.mjs` 为可重跑的 capture-only fixture；价格区在截图时把金额替换为“成本价使用”，不修改业务页面。
- 所有面试题、简历信息、JD、知识库条目、回答和复盘内容均为合成示例。
- 不读取生产环境、登录态、真实音频、个人信息或密钥。

## 制作放行

- 2026-09-03：用户逐项确认产品简报、执行决策、视觉方向、功能映射与完整分镜。
- 2026-09-03：用户明确回复“确认制作”，进入最终素材采集、实现、声音设计与终检。
- 2026-09-03：应用户追加要求，新增 MiniMax 中文旁白版；保留原无旁白两版不变。旁白采用 `speech-2.8-hd` / `male-qn-jingying`，分镜级钉帧，完整台词见 `voiceover-script.md`。
