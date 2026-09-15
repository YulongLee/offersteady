import { privacySections, termsSections, updatedAt } from "./src/legal-content";

const escape = (text: string) => text.replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;");
export function legalStaticHtml(homepage: string, kind: "terms" | "privacy") {
  const title = kind === "terms" ? "用户协议" : "隐私政策";
  const description = kind === "terms" ? "阅读面试稳AI助手用户协议，了解服务范围、账号安全、AI建议使用规则、积分会员支付、用户内容权利及客服联系方式。" : "阅读面试稳AI助手隐私政策，了解账号、简历、JD、转录与截图等信息的处理目的、保存与安全措施、第三方处理及你的控制权利。";
  const sections = kind === "terms" ? termsSections : privacySections;
  const canonical = `https://mianshiwen.cn/${kind}`;
  const body = `<main class="seo-prerender"><nav aria-label="公开导航"><a href="/">返回首页</a><a href="/pricing">价格</a><a href="/contact">联系我们</a><a href="/terms">用户协议</a><a href="/privacy">隐私政策</a><a href="/login">登录或注册</a></nav><h1>${title}</h1><p>更新时间：${updatedAt}</p>${sections.map(([heading, paragraphs]) => `<section><h2>${escape(heading)}</h2>${paragraphs.map(text => `<p>${escape(text)}</p>`).join("")}</section>`).join("")}${kind === "privacy" ? '<aside><h2>推广归因控制</h2><p>页面交互功能加载后可退出非必要推广归因；也可通过上述客服渠道联系我们。</p></aside>' : ""}</main>`;
  if (!homepage.includes('<div id="root">')) throw new Error("Missing public entry root");
  return homepage
    .replace(/<title>[\s\S]*?<\/title>/, `<title>${title} - 面试稳AI助手</title>`)
    .replace(/<meta\s+name="description"\s+content="[^"]*"\s*\/>/, `<meta name="description" content="${description}" />`)
    .replace(/<link rel="canonical" href="[^"]*"\s*\/>/, `<link rel="canonical" href="${canonical}" />`)
    .replace(/(<meta property="og:url" content=")[^"]*/, `$1${canonical}`)
    .replace(/(<meta (?:property="og:title"|name="twitter:title") content=")[^"]*/g, `$1${title} - 面试稳AI助手`)
    .replace(/(<meta (?:property="og:description"|name="twitter:description") content=")[^"]*/g, `$1${description}`)
    .replace(/<script type="application\/ld\+json">[\s\S]*?<\/script>/g, "")
    .replace(/<div id="root">[\s\S]*<\/div>/, `<div id="root">${body}</div>`);
}
