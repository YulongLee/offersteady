import { FormEvent, useEffect, useMemo, useState } from "react";

import { adminApi, isAdminAuthenticationError } from "./api";

type Row = Record<string, unknown>;
type Tab = "overview" | "links" | "campaigns" | "channels" | "funnel";
type Range = "today" | "yesterday" | "7d" | "30d" | "90d";
type Model = "first_touch" | "last_non_direct_touch";

const tabs: { id: Tab; label: string }[] = [
  { id: "overview", label: "推广总览" },
  { id: "links", label: "推广链接" },
  { id: "campaigns", label: "营销活动" },
  { id: "channels", label: "渠道分析" },
  { id: "funnel", label: "转化漏斗" },
];

const metricLabels: Record<string, string> = {
  uniqueVisitors: "有效访客", registrations: "注册用户", activatedUsers: "首次使用",
  payingUsers: "付费用户", paidOrders: "支付订单", revenueCents: "推广贡献实收",
  costCents: "推广成本", cacCents: "获客成本（CAC）", roas: "广告投入产出（ROAS）", roi: "投资回报率（ROI）",
};

const fieldLabels: Record<string, string> = {
  dimensionName: "名称", code: "渠道编码", name: "名称", contentName: "内容名称", channelName: "渠道",
  campaignName: "营销活动", destinationPath: "目标页面", publicUrl: "推广链接", status: "状态",
  isSystem: "系统渠道", sortOrder: "排序", objective: "推广目标", budgetCents: "计划预算",
  actualCostCents: "实际成本", channelCount: "渠道数", linkCount: "链接数", startsAtMs: "开始时间",
  endsAtMs: "结束时间", createdAtMs: "创建时间", updatedAtMs: "更新时间", costCoverage: "成本覆盖",
  qualifiedVisits: "有效访问次数", downloads: "实际下载", orders: "下单数",
  registrationRate: "注册转化率", activationRate: "首次使用转化率", paymentRate: "付费转化率",
  ...metricLabels,
};

const stateLabels: Record<string, string> = {
  active: "已启用", inactive: "已停用", draft: "草稿", paused: "已暂停", ended: "已结束",
  current: "数据已更新", delayed: "数据延迟", partial: "数据不完整", observing: "观察中", mature: "观察完成",
  healthy: "正常", unavailable: "暂不可用", disabled: "未启用", completed: "已完成", failed: "失败",
  missing: "成本未录入", complete: "完整", true: "是", false: "否",
  first_touch: "首次触点", last_non_direct_touch: "末次非直接触点",
};

const formatValue = (key: string, value: unknown) => {
  if (value === null || value === undefined) return ["costCents", "cacCents", "roas", "roi"].includes(key) ? "成本未录入" : "—";
  if (key.endsWith("Cents")) return `¥${(Number(value) / 100).toLocaleString("zh-CN", { minimumFractionDigits: 2 })}`;
  if (key === "roas") return `${Number(value).toFixed(2)}×`;
  if (key === "roi") return `${(Number(value) * 100).toFixed(1)}%`;
  return Number(value).toLocaleString("zh-CN");
};

const formatTableValue = (key: string, value: unknown) => {
  if (value === null || value === undefined || value === "") return "—";
  if (key.endsWith("AtMs")) return new Date(Number(value)).toLocaleString("zh-CN");
  if (key.endsWith("Cents") || ["roas", "roi"].includes(key)) return formatValue(key, value);
  if (key.endsWith("Rate")) return `${(Number(value) * 100).toFixed(1)}%`;
  const localized = stateLabels[String(value)];
  if (localized) return localized;
  if (typeof value === "number") return value.toLocaleString("zh-CN");
  return String(value);
};

const Table = ({ rows, empty }: { rows: Row[]; empty: string }) => {
  if (!rows.length) return <div className="promotion-empty">{empty}</div>;
  const keys = Object.keys(rows[0]!).filter(key => !/Id$/.test(key) && !key.endsWith("ByUserId")).slice(0, 10);
  return <div className="table-wrap"><table><thead><tr>{keys.map(key => <th key={key}>{fieldLabels[key] ?? "指标"}</th>)}</tr></thead><tbody>{rows.map((row, index) => <tr key={String(row.linkId ?? row.campaignId ?? row.channelId ?? row.dimensionId ?? index)}>{keys.map(key => <td key={key}>{formatTableValue(key, row[key])}</td>)}</tr>)}</tbody></table></div>;
};

export function PromotionCenter({ permissions, onAuthenticationExpired }: { permissions: string[]; onAuthenticationExpired: (message: string) => void }) {
  const [tab, setTab] = useState<Tab>("overview");
  const [range, setRange] = useState<Range>("30d");
  const [model, setModel] = useState<Model>("last_non_direct_touch");
  const [channelSort, setChannelSort] = useState("uniqueVisitors");
  const [linkFilter, setLinkFilter] = useState("");
  const [data, setData] = useState<Row>({});
  const [channels, setChannels] = useState<Row[]>([]);
  const [campaigns, setCampaigns] = useState<Row[]>([]);
  const [links, setLinks] = useState<Row[]>([]);
  const [costs, setCosts] = useState<Row[]>([]);
  const [campaignReport, setCampaignReport] = useState<Row | null>(null);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");
  const [failed, setFailed] = useState(false);
  const [channelDraft, setChannelDraft] = useState({ code: "", name: "" });
  const [campaignDraft, setCampaignDraft] = useState({ name: "", objective: "", budgetYuan: "", startsOn: "", endsOn: "" });
  const [linkDraft, setLinkDraft] = useState({ contentName: "", channelId: "", campaignId: "", destinationPath: "/" });
  const [costDraft, setCostDraft] = useState({ scopeType: "campaign", scopeId: "", costDate: new Date().toISOString().slice(0, 10), amountYuan: "", reason: "" });
  const [reversalDraft, setReversalDraft] = useState({ costEntryId: "", reason: "" });
  const canManage = permissions.includes("promotion.manage");
  const canManageCost = permissions.includes("promotion.cost.manage");

  const handleError = (error: unknown) => {
    const text = error instanceof Error ? error.message : "推广数据暂时不可用";
    setMessage(text);
    setFailed(true);
    if (isAdminAuthenticationError(error)) onAuthenticationExpired(text);
  };

  const loadDimensions = async () => {
    const [nextChannels, nextCampaigns, nextLinks] = await Promise.all([
      adminApi.promotionChannels(), adminApi.promotionCampaigns(), adminApi.promotionLinks(),
    ]);
    setChannels(nextChannels.items);
    setCampaigns(nextCampaigns.items);
    setLinks(nextLinks.items);
  };

  const load = async () => {
    setLoading(true);
    setMessage("");
    setFailed(false);
    try {
      if (tab === "overview") {
        const [overview, trends, funnel, topChannels, topCampaigns, topLinks, health] = await Promise.all([
          adminApi.promotionOverview(range, model), adminApi.promotionTrends(range === "today" || range === "yesterday" ? "7d" : range, model),
          adminApi.promotionFunnel(range, model), adminApi.promotionReport("channel", range, model),
          adminApi.promotionReport("campaign", range, model), adminApi.promotionReport("link", range, model),
          adminApi.promotionHealth(),
        ]);
        setData({ ...overview, trend: trends.items, funnel, topChannels: topChannels.items.slice(0, 5), topCampaigns: topCampaigns.items.slice(0, 5), topLinks: topLinks.items.slice(0, 5), health });
        if (canManageCost) {
          await loadDimensions();
          setCosts((await adminApi.promotionCosts()).items);
        }
      }
      if (tab === "funnel") setData(await adminApi.promotionFunnel(range, model));
      if (tab === "channels") {
        const report = await adminApi.promotionReport("channel", range, model);
        setData(report);
        await loadDimensions();
      }
      if (tab === "campaigns" || tab === "links") await loadDimensions();
    } catch (error) { handleError(error); }
    finally { setLoading(false); }
  };

  useEffect(() => { void load(); }, [tab, range, model]);

  const createChannel = async (event: FormEvent) => {
    event.preventDefault();
    try {
      await adminApi.createPromotionChannel({ ...channelDraft, sortOrder: channels.length });
      setChannelDraft({ code: "", name: "" }); setMessage("渠道已创建并写入审计记录。"); await loadDimensions();
    } catch (error) { handleError(error); }
  };
  const createCampaign = async (event: FormEvent) => {
    event.preventDefault();
    try {
      await adminApi.createPromotionCampaign({ name: campaignDraft.name, objective: campaignDraft.objective, status: "draft", startsAtMs: campaignDraft.startsOn ? new Date(`${campaignDraft.startsOn}T00:00:00+08:00`).getTime() : null, endsAtMs: campaignDraft.endsOn ? new Date(`${campaignDraft.endsOn}T23:59:59+08:00`).getTime() : null, budgetCents: campaignDraft.budgetYuan ? Math.round(Number(campaignDraft.budgetYuan) * 100) : null, notes: "" });
      setCampaignDraft({ name: "", objective: "", budgetYuan: "", startsOn: "", endsOn: "" }); setMessage("营销活动已创建。"); await loadDimensions();
    } catch (error) { handleError(error); }
  };
  const createLink = async (event: FormEvent) => {
    event.preventDefault();
    try {
      const created = await adminApi.createPromotionLink({ contentName: linkDraft.contentName, channelId: linkDraft.channelId, campaignId: linkDraft.campaignId || null, destinationPath: linkDraft.destinationPath, startsAtMs: null, endsAtMs: null });
      setLinkDraft(current => ({ ...current, contentName: "" })); setMessage(`推广链接已创建：${String(created.publicUrl ?? "")}`); await loadDimensions();
    } catch (error) { handleError(error); }
  };
  const addCost = async (event: FormEvent) => {
    event.preventDefault();
    try {
      await adminApi.addPromotionCost({ scopeType: costDraft.scopeType, scopeId: costDraft.scopeId, costDate: costDraft.costDate, amountCents: Math.round(Number(costDraft.amountYuan) * 100), currency: "CNY", reason: costDraft.reason });
      setCostDraft(current => ({ ...current, amountYuan: "", reason: "" })); setMessage("成本已追加；历史金额未被覆盖。"); await load();
    } catch (error) { handleError(error); }
  };
  const reverseCost = async (event: FormEvent) => {
    event.preventDefault();
    try {
      await adminApi.reversePromotionCost(reversalDraft.costEntryId, reversalDraft.reason);
      setReversalDraft({ costEntryId: "", reason: "" }); setMessage("成本冲正已追加，原始记录保持不变。"); setCosts((await adminApi.promotionCosts()).items); await load();
    } catch (error) { handleError(error); }
  };
  const changeLinkStatus = async (row: Row) => {
    try {
      const nextStatus = row.status === "active" ? "inactive" : "active";
      await adminApi.updatePromotionLink(String(row.linkId), {
        contentName: row.contentName, channelId: row.channelId, campaignId: row.campaignId ?? null,
        destinationPath: row.destinationPath, startsAtMs: row.startsAtMs ?? null, endsAtMs: row.endsAtMs ?? null,
        status: nextStatus, reason: nextStatus === "active" ? "重新启用推广链接" : "暂停推广链接",
      });
      setMessage(nextStatus === "active" ? "链接已启用。" : "链接已停用，历史数据保留。"); await loadDimensions();
    } catch (error) { handleError(error); }
  };
  const cloneLink = async (row: Row) => {
    try {
      await adminApi.clonePromotionLink(String(row.linkId), { reason: "复制推广链接用于新的内容归属" });
      setMessage("已生成独立副本，原链接和历史归因未变更。"); await loadDimensions();
    } catch (error) { handleError(error); }
  };
  const changeCampaignStatus = async (row: Row) => {
    try {
      const status = row.status === "active" ? "paused" : "active";
      await adminApi.updatePromotionCampaign(String(row.campaignId), {
        name: row.name, objective: row.objective ?? "", status, startsAtMs: row.startsAtMs ?? null,
        endsAtMs: row.endsAtMs ?? null, budgetCents: row.budgetCents ?? null, notes: row.notes ?? "",
        reason: status === "active" ? "启用营销活动" : "暂停营销活动",
      });
      setMessage(status === "active" ? "活动已启用。" : "活动已暂停。"); await loadDimensions();
    } catch (error) { handleError(error); }
  };
  const openCampaignReport = async (row: Row) => {
    try { setCampaignReport(await adminApi.promotionCampaignReport(String(row.campaignId), range, model)); }
    catch (error) { handleError(error); }
  };

  const overview = (data.metrics ?? {}) as Row;
  const metadata = (data.metadata ?? {}) as Row;
  const reportRows = ((data.items ?? []) as Row[]);
  const stages = ((data.stages ?? []) as Row[]);
  const overviewFunnel = ((data.funnel ?? {}) as Row);
  const trendRows = ((data.trend ?? []) as Row[]);
  const channelRows = useMemo(() => {
    const byId = new Map(reportRows.map(row => [String(row.dimensionId), row]));
    return channels.map(row => byId.get(String(row.channelId)) ?? { dimensionId: row.channelId, dimensionName: row.name, uniqueVisitors: 0, registrations: 0, activatedUsers: 0, payingUsers: 0, revenueCents: 0, costCents: null, roas: null })
      .sort((left, right) => Number(right[channelSort] ?? -1) - Number(left[channelSort] ?? -1));
  }, [channels, reportRows, channelSort]);
  const costScopes = useMemo(() => costDraft.scopeType === "channel" ? channels : costDraft.scopeType === "campaign" ? campaigns : links, [costDraft.scopeType, channels, campaigns, links]);
  const filteredLinks = useMemo(() => {
    const query = linkFilter.trim().toLowerCase();
    if (!query) return links;
    return links.filter(row => [row.contentName, row.channelName, row.campaignName, row.publicUrl].some(value => String(value ?? "").toLowerCase().includes(query)));
  }, [links, linkFilter]);

  return <section className="promotion-center">
    <div className="promotion-toolbar">
      <div className="promotion-tabs" role="tablist" aria-label="推广中心功能">{tabs.map(item => <button key={item.id} role="tab" aria-selected={tab === item.id} className={tab === item.id ? "active" : ""} onClick={() => setTab(item.id)}>{item.label}</button>)}</div>
      <div className="promotion-filters"><select aria-label="统计周期" value={range} onChange={event => setRange(event.target.value as Range)}><option value="today">今天</option><option value="yesterday">昨天</option><option value="7d">7 天</option><option value="30d">30 天</option><option value="90d">90 天</option></select><select aria-label="归因模型" value={model} onChange={event => setModel(event.target.value as Model)}><option value="last_non_direct_touch">末次非直接触点</option><option value="first_touch">首次触点</option></select></div>
    </div>
    {message ? <div className={`promotion-message${failed ? " error" : ""}`} role={failed ? "alert" : "status"}><span>{message}</span>{failed ? <button type="button" onClick={() => void load()}>重试</button> : null}</div> : null}
    {loading ? <div className="loading">正在读取推广数据…</div> : null}
    {!loading && tab === "overview" ? <>
      <div className="promotion-kpis">{Object.keys(metricLabels).map(key => <article key={key}><small>{metricLabels[key]}</small><strong>{formatValue(key, overview[key])}</strong></article>)}</div>
      <div className="promotion-coverage"><span>数据时区：{String(metadata.timezone ?? "Asia/Shanghai")}</span><span>归因模型：{stateLabels[String(metadata.attributionModel ?? model)] ?? "—"}</span><span>数据状态：{stateLabels[String(metadata.freshness ?? "")] ?? "—"}</span><span>人群观察：{stateLabels[String(metadata.cohortState ?? "")] ?? "—"}</span></div>
      {data.health ? <div className="promotion-health">{(() => { const health = data.health as Row; const queue = (health.queue ?? {}) as Row; const run = (health.latestRun ?? {}) as Row; return <><span>分析任务：{stateLabels[String(run.status ?? "")] ?? "尚未运行"}</span><span>事件队列：{stateLabels[String(queue.state ?? "")] ?? "—"} / 待处理 {String(queue.pending ?? 0)}</span><span>未送达事件：{String(queue.dropped ?? 0)}</span><span>快照：{health.snapshotFreshAtMs ? new Date(Number(health.snapshotFreshAtMs)).toLocaleString("zh-CN") : "尚未生成"}</span><span>未匹配身份：{String(health.unmatchedIdentities ?? 0)}</span><span>核对异常：{String(run.mismatchCount ?? 0)}</span></>; })()}</div> : null}
      <div className="promotion-overview-grid"><article><h3>转化趋势</h3>{trendRows.length ? trendRows.map(row => { const metrics = (row.metricsJson ?? {}) as Row; return <div className="promotion-trend-row" key={String(row.bucketDate)}><span>{String(row.bucketDate)}</span><i style={{ width: `${Math.min(100, Number(metrics.uniqueVisitors ?? 0) * 4)}%` }} /><b>{Number(metrics.uniqueVisitors ?? 0)} UV</b></div>; }) : <p>日快照尚未生成；今天的数据已在上方实时展示。</p>}</article><article><h3>紧凑漏斗</h3>{((overviewFunnel.stages ?? []) as Row[]).map(stage => <div className="promotion-mini-funnel" key={String(stage.key)}><span>{String(stage.label)}</span><b>{Number(stage.count ?? 0).toLocaleString("zh-CN")}</b><small>{stage.cumulativeRate == null ? "—" : `${(Number(stage.cumulativeRate) * 100).toFixed(1)}%`}</small></div>)}</article></div>
      <div className="promotion-top-grid"><article><h3>Top 渠道</h3><Table rows={(data.topChannels ?? []) as Row[]} empty="暂无渠道数据" /></article><article><h3>Top 活动</h3><Table rows={(data.topCampaigns ?? []) as Row[]} empty="暂无活动数据" /></article><article><h3>Top 链接</h3><Table rows={(data.topLinks ?? []) as Row[]} empty="暂无链接数据" /></article></div>
      {canManageCost ? <form className="promotion-form cost" onSubmit={addCost}><h3>追加推广成本</h3><select value={costDraft.scopeType} onChange={event => setCostDraft(current => ({ ...current, scopeType: event.target.value, scopeId: "" }))}><option value="campaign">活动</option><option value="channel">渠道</option><option value="link">链接</option></select><select required value={costDraft.scopeId} onChange={event => setCostDraft(current => ({ ...current, scopeId: event.target.value }))}><option value="">选择归属</option>{costScopes.map(row => <option key={String(row.channelId ?? row.campaignId ?? row.linkId)} value={String(row.channelId ?? row.campaignId ?? row.linkId)}>{String(row.name ?? row.contentName)}</option>)}</select><input type="date" value={costDraft.costDate} onChange={event => setCostDraft(current => ({ ...current, costDate: event.target.value }))} /><input required type="number" min="0.01" step="0.01" placeholder="成本（元）" value={costDraft.amountYuan} onChange={event => setCostDraft(current => ({ ...current, amountYuan: event.target.value }))} /><input required minLength={3} placeholder="录入原因" value={costDraft.reason} onChange={event => setCostDraft(current => ({ ...current, reason: event.target.value }))} /><button className="primary">追加成本</button></form> : null}
      {canManageCost && costs.some(row => Number(row.amountCents) > 0 && !row.reversalOfEntryId) ? <form className="promotion-form" onSubmit={reverseCost}><h3>冲正成本</h3><select required value={reversalDraft.costEntryId} onChange={event => setReversalDraft(current => ({ ...current, costEntryId: event.target.value }))}><option value="">选择原始成本记录</option>{costs.filter(row => Number(row.amountCents) > 0 && !row.reversalOfEntryId).map(row => <option key={String(row.costEntryId)} value={String(row.costEntryId)}>{String(row.costDate)} · ¥{(Number(row.amountCents) / 100).toFixed(2)} · {String(row.reason)}</option>)}</select><input required minLength={3} placeholder="冲正原因" value={reversalDraft.reason} onChange={event => setReversalDraft(current => ({ ...current, reason: event.target.value }))} /><button className="secondary">追加冲正</button></form> : null}
    </> : null}
    {!loading && tab === "links" ? <><div className="promotion-link-filter"><label>筛选推广链接<input type="search" value={linkFilter} onChange={event => setLinkFilter(event.target.value)} placeholder="搜索内容、渠道、活动或链接" /></label><span>{filteredLinks.length} / {links.length}</span></div><div className="promotion-link-list">{filteredLinks.length ? filteredLinks.map(row => <article key={String(row.linkId)}><div><strong>{String(row.contentName)}</strong><small>{String(row.channelName)} · {String(row.campaignName ?? "未归属活动")} · 目标 {String(row.destinationPath)}</small><code>{String(row.publicUrl)}</code></div><span className={`status-badge ${row.status === "active" ? "active" : "inactive"}`}>{row.status === "active" ? "启用" : "停用"}</span><div className="promotion-row-actions"><button onClick={() => void navigator.clipboard?.writeText(String(row.publicUrl)).then(() => setMessage("链接已复制。"))}>复制</button><button onClick={() => window.open(`${String(row.publicUrl)}?preview=1`, "_blank", "noopener,noreferrer")}>无计数预览</button>{canManage ? <><button onClick={() => void cloneLink(row)}>克隆</button><button onClick={() => void changeLinkStatus(row)}>{row.status === "active" ? "停用" : "启用"}</button></> : null}</div></article>) : <div className="promotion-empty">{links.length ? "没有符合筛选条件的链接。" : "还没有推广链接。先创建渠道，再为每篇内容生成独立链接。"}</div>}</div>{canManage ? <form className="promotion-form" onSubmit={createLink}><h3>创建专属推广链接</h3><input required placeholder="内容名称，例如：牛客后端秋招经验帖" value={linkDraft.contentName} onChange={event => setLinkDraft(current => ({ ...current, contentName: event.target.value }))} /><select required value={linkDraft.channelId} onChange={event => setLinkDraft(current => ({ ...current, channelId: event.target.value }))}><option value="">选择渠道</option>{channels.filter(row => !row.isSystem && row.status === "active").map(row => <option key={String(row.channelId)} value={String(row.channelId)}>{String(row.name)}</option>)}</select><select value={linkDraft.campaignId} onChange={event => setLinkDraft(current => ({ ...current, campaignId: event.target.value }))}><option value="">不归属活动</option>{campaigns.map(row => <option key={String(row.campaignId)} value={String(row.campaignId)}>{String(row.name)}</option>)}</select><input required pattern="/.*" placeholder="站内目标路径" value={linkDraft.destinationPath} onChange={event => setLinkDraft(current => ({ ...current, destinationPath: event.target.value }))} /><button className="primary">生成链接</button></form> : null}</> : null}
    {!loading && tab === "campaigns" ? <><div className="promotion-campaign-grid">{campaigns.length ? campaigns.map(row => <article key={String(row.campaignId)}><div><small>{String(row.status)}</small><strong>{String(row.name)}</strong><p>{String(row.objective || "未填写推广目标")}</p></div><dl><div><dt>周期</dt><dd>{row.startsAtMs ? new Date(Number(row.startsAtMs)).toLocaleDateString("zh-CN") : "不限"} — {row.endsAtMs ? new Date(Number(row.endsAtMs)).toLocaleDateString("zh-CN") : "不限"}</dd></div><div><dt>预算</dt><dd>{row.budgetCents == null ? "未录入" : formatValue("budgetCents", row.budgetCents)}</dd></div><div><dt>实际成本</dt><dd>{formatValue("actualCostCents", row.actualCostCents)}</dd></div><div><dt>渠道 / 链接</dt><dd>{String(row.channelCount)} / {String(row.linkCount)}</dd></div></dl><div className="promotion-row-actions"><button onClick={() => void openCampaignReport(row)}>查看效果</button>{canManage ? <button onClick={() => void changeCampaignStatus(row)}>{row.status === "active" ? "暂停" : "启用"}</button> : null}</div></article>) : <div className="promotion-empty">还没有营销活动。</div>}</div>{campaignReport ? <section className="promotion-campaign-detail"><button aria-label="关闭活动详情" onClick={() => setCampaignReport(null)}>×</button><h3>{String(((campaignReport.campaign ?? {}) as Row).name)} · 效果详情</h3><div className="promotion-kpis">{["uniqueVisitors","registrations","activatedUsers","payingUsers","revenueCents","costCents","roas","roi"].map(key => <article key={key}><small>{metricLabels[key] ?? key}</small><strong>{formatValue(key, ((campaignReport.metrics ?? {}) as Row)?.[key])}</strong></article>)}</div><h4>渠道与链接构成</h4><Table rows={((((campaignReport.campaign ?? {}) as Row).links ?? []) as Row[])} empty="活动下还没有推广链接" /><h4>活动漏斗</h4><div className="promotion-funnel">{((campaignReport.funnel ?? []) as Row[]).map((stage, index) => <article key={String(stage.key)}><div><small>{index + 1}</small><strong>{String(stage.label)}</strong></div><b>{String(stage.count)}</b><span>阶段 {stage.stageRate == null ? "—" : `${(Number(stage.stageRate) * 100).toFixed(1)}%`}</span><span>累计 {stage.cumulativeRate == null ? "—" : `${(Number(stage.cumulativeRate) * 100).toFixed(1)}%`}</span><em>流失 {String(stage.dropOff)}</em></article>)}</div></section> : null}{canManage ? <form className="promotion-form" onSubmit={createCampaign}><h3>新建营销活动</h3><input required placeholder="活动名称" value={campaignDraft.name} onChange={event => setCampaignDraft(current => ({ ...current, name: event.target.value }))} /><input placeholder="推广目标" value={campaignDraft.objective} onChange={event => setCampaignDraft(current => ({ ...current, objective: event.target.value }))} /><input type="date" aria-label="活动开始日期" value={campaignDraft.startsOn} onChange={event => setCampaignDraft(current => ({ ...current, startsOn: event.target.value }))} /><input type="date" aria-label="活动结束日期" value={campaignDraft.endsOn} onChange={event => setCampaignDraft(current => ({ ...current, endsOn: event.target.value }))} /><input type="number" min="0" step="0.01" placeholder="计划预算（元，可选）" value={campaignDraft.budgetYuan} onChange={event => setCampaignDraft(current => ({ ...current, budgetYuan: event.target.value }))} /><button className="primary">保存为草稿</button></form> : null}</> : null}
    {!loading && tab === "channels" ? <><div className="promotion-sort"><label>排序指标<select value={channelSort} onChange={event => setChannelSort(event.target.value)}><option value="uniqueVisitors">有效 UV</option><option value="registrations">注册</option><option value="payingUsers">付费用户</option><option value="revenueCents">实收</option><option value="roas">ROAS</option></select></label></div><Table rows={channelRows} empty="当前周期没有有效推广访问。" /><h3 className="promotion-subtitle">渠道配置</h3><Table rows={channels} empty="还没有渠道。" />{canManage ? <form className="promotion-form" onSubmit={createChannel}><h3>新建渠道</h3><input required pattern="[a-z][a-z0-9_-]+" placeholder="渠道编码，例如 nowcoder" value={channelDraft.code} onChange={event => setChannelDraft(current => ({ ...current, code: event.target.value }))} /><input required placeholder="渠道名称，例如 牛客" value={channelDraft.name} onChange={event => setChannelDraft(current => ({ ...current, name: event.target.value }))} /><button className="primary">创建渠道</button></form> : null}</> : null}
    {!loading && tab === "funnel" ? <><div className="promotion-funnel-note"><strong>{data.cohortState === "mature" ? "观察窗口已成熟" : "观察中"}</strong><p>以所选期间首次有效推广访问的人群为 Cohort；每个阶段按人去重，阶段转化以上一阶段为分母，累计转化以有效 UV 为分母。最近人群仍在 30 天观察窗口内时，不把当前流失视为最终结果。</p></div>{stages.length ? <div className="promotion-funnel">{stages.map((stage, index) => <article key={String(stage.key)}><div><small>{index + 1}</small><strong>{String(stage.label)}</strong></div><b>{Number(stage.count ?? 0).toLocaleString("zh-CN")}</b><span>阶段转化 {stage.stageRate == null ? "—" : `${(Number(stage.stageRate) * 100).toFixed(1)}%`}</span><span>累计转化 {stage.cumulativeRate == null ? "—" : `${(Number(stage.cumulativeRate) * 100).toFixed(1)}%`}</span><em>流失 {Number(stage.dropOff ?? 0).toLocaleString("zh-CN")}</em></article>)}</div> : <div className="promotion-empty">当前范围还没有有效推广访问，漏斗不会把缺失数据绘制成 0。</div>}</> : null}
  </section>;
}
