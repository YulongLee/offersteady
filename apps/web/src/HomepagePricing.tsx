import { useState } from "react";
import { CheckIcon, ArrowRightIcon } from "@phosphor-icons/react";
import type { WebAppState } from "./domain";

export function HomepagePricing({ billing }: { readonly billing: WebAppState["billing"] }) {
  const passes = billing.catalog.filter(item => item.kind === "time_pass" && item.published
    && Number.isFinite(item.priceCents) && item.priceCents > 0
    && Number.isFinite(item.durationDays) && (item.durationDays ?? 0) > 0)
    .sort((a, b) => (a.durationDays ?? 0) - (b.durationDays ?? 0));
  const [selectedId, setSelectedId] = useState<string>();
  // Resolve selection against the current catalogue, never a stale snapshot.
  const selected = passes.find(pass => pass.id === selectedId) ?? passes[0];
  return <section id="pricing-value" className="public-section cn-pricing-section">
    <div className="section-intro"><span className="kicker">清楚的价格，适合自己的节奏</span><h2>按需使用，或安心准备一段时间。</h2><p>积分按功能消耗，会员按有效期使用。先了解，再决定。</p></div>
    <div className="cn-pricing-layout" aria-label="积分与会员区别">
      <aside className="cn-flexible-plan">
        <span className="kicker">偶尔使用</span><h3>积分，灵活一点。</h3><p>按实际使用的功能消耗积分，适合先体验或不定期使用。</p>
        <dl className="cn-rate-list"><div><dt>回答建议</dt><dd>{billing.rates.answerPoints} <span>点起</span></dd></div><div><dt>截图回答</dt><dd>{billing.rates.screenshotAnswerPoints} <span>点起</span></dd></div><div><dt>知识材料</dt><dd>{billing.rates.knowledgeIndexMinimumPoints} <span>点起</span></dd></div></dl>
        <small>具体消耗在使用前查看报价。</small><a className="text-link" href="/pricing">查看积分包与计费规则 <ArrowRightIcon size={16} aria-hidden="true" /></a>
      </aside>
      <div className="cn-membership-plan">
        <div className="cn-membership-heading"><div><span className="kicker">连续准备</span><h3>会员，按你的时间来。</h3></div><a href="/guide#billing">有效期说明 ↗</a></div>
        {selected ? <>
          <div className="cn-duration-options" role="group" aria-label="按天会员套餐">
            {passes.map(pass => <button type="button" key={pass.id} aria-label={`${pass.durationDays} 天 ¥${(pass.priceCents / 100).toFixed(2)}`} aria-pressed={selected.id === pass.id} aria-controls="cn-selected-membership" onClick={() => setSelectedId(pass.id)}><strong>{pass.durationDays} 天</strong><span>¥{(pass.priceCents / 100).toFixed(2)}</span></button>)}
          </div>
          <div id="cn-selected-membership" className="cn-selected-membership" role="region" aria-label="当前会员权益" aria-live="polite" aria-atomic="true">
            <div className="cn-member-price"><div><span>{selected.displayName}</span><p><strong>¥{(selected.priceCents / 100).toFixed(2)}</strong><span> / {selected.durationDays} 天</span></p></div><span className="cn-duration-caption">有效期 {selected.durationDays} 天</span></div>
            <ul className="cn-member-benefits"><li><CheckIcon size={18} aria-hidden="true" />回答与截图回答不限次</li><li><CheckIcon size={18} aria-hidden="true" />{(selected.knowledgeIndexAllowance ?? 0) > 0 ? `含 ${selected.knowledgeIndexAllowance} 份知识材料额度` : "知识材料按实际用量另行计费"}</li></ul>
          </div>
          <a className="button primary cn-member-action" href="/pricing">查看完整套餐与权益 <ArrowRightIcon size={18} aria-hidden="true" /></a>
        </> : <p className="cn-catalog-unavailable">当前暂无可展示的会员套餐，请前往积分与会员页面查看。</p>}
        <p className="cn-member-limits">仅限本人正常使用，仍受并发及防滥用限制；知识材料按套餐额度或积分计费。</p>
      </div>
    </div>
    <div className="cn-purchase-note"><p>支付确认后，权益发放至当前账号；可在「积分与会员」查看订单和有效期。知识材料超出额度仍需积分。</p><a href="/contact">订单与退款咨询 ↗</a></div>
  </section>;
}
