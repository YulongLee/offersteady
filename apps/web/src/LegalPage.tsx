import { useState } from "react";
import { Link } from "react-router-dom";

import { routes } from "./routes";

type LegalKind = "terms" | "privacy";

import { updatedAt, termsSections, privacySections } from "./legal-content";

function PromotionPrivacyControl() {
  const [status, setStatus] = useState("");
  const optOut = async () => {
    setStatus("正在保存设置…");
    try {
      const response = await fetch("/api/v1/promotion/opt-out", { method: "POST", credentials: "include" });
      if (!response.ok) throw new Error("request failed");
      window.sessionStorage?.removeItem("offersteady.promotion.qualification_event");
      setStatus("已退出非必要推广归因。本设备上的推广标识已清除，不影响产品功能。");
    } catch {
      setStatus("暂时无法保存设置，请稍后重试或联系客服。");
    }
  };
  return <aside className="legal-review-note"><strong>推广归因控制</strong><p>如不希望本浏览器使用第一方匿名标识关联推广效果，可随时退出。</p><button type="button" className="button secondary" onClick={() => void optOut()}>退出推广归因</button>{status ? <p role="status">{status}</p> : null}</aside>;
}

export function LegalPage({ kind }: { readonly kind: LegalKind }) {
  const terms = kind === "terms";
  const title = terms ? "用户协议" : "隐私政策";
  const sections = terms ? termsSections : privacySections;

  return (
    <main className="legal-page">
      <header className="legal-hero"><span className="kicker">LEGAL & TRUST</span><h1>{title}</h1><p>更新时间：{updatedAt}</p><p>{terms ? "请在注册、购买或使用面试稳AI助手前阅读本协议。" : "本政策说明面试稳AI助手当前如何处理和保护与你有关的信息。"}</p></header>
      <article className="legal-document">
        {sections.map(([heading, paragraphs]) => <section key={heading}><h2>{heading}</h2>{paragraphs.map(paragraph => <p key={paragraph}>{paragraph}</p>)}</section>)}
        {!terms ? <PromotionPrivacyControl /> : null}
        <aside className="legal-review-note"><strong>相关文件</strong><p>{terms ? <>个人信息处理详情请查看<Link to={routes.privacy}>隐私政策</Link>。</> : <>服务使用规则请查看<Link to={routes.terms}>用户协议</Link>。</>}</p></aside>
      </article>
      <nav className="legal-actions" aria-label="法律文件导航"><Link to={routes.landing}>返回首页</Link><Link to={routes.login}>登录或注册</Link></nav>
    </main>
  );
}
