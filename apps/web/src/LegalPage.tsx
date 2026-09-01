import { useState } from "react";
import { Link } from "react-router-dom";

import { routes } from "./routes";

type LegalKind = "terms" | "privacy";

const updatedAt = "2026 年 9 月 1 日";

const termsSections = [
  ["一、服务说明", [
    "面试稳AI助手提供面试准备、资料整理、实时问题理解、回答建议、截图题辅助和面试复盘等功能。具体可用能力以页面和客户端实际展示为准。",
    "AI 生成内容仅供参考，不构成录用保证、职业建议或标准答案。你应核对内容并始终基于本人真实经历作答。",
  ]],
  ["二、账号与安全", [
    "你可以使用手机号验证码登录或注册。请妥善保管验证码和已登录设备，不得转让账号、冒用他人身份或绕过访问控制。",
    "发现账号异常时，请及时退出其他设备并通过页面公布的客服渠道联系我们。",
  ]],
  ["三、使用规则", [
    "你应遵守适用法律、面试组织方规则及录音、录屏和信息保密要求，并在需要时取得相关参与者同意。",
    "不得利用本服务侵犯他人隐私、知识产权或商业秘密，不得上传恶意内容、攻击服务、批量滥用接口，或将 AI 建议包装成虚假的个人经历。",
  ]],
  ["四、积分、会员与支付", [
    "积分消耗、会员期限、知识材料额度和商品价格以购买或使用前页面展示及服务端确认为准。权益仅在支付渠道通知通过验签或服务端主动查单确认后到账。",
    "退款或订单争议将结合适用法律、商品实际使用情况和支付渠道规则处理。遇到未到账请勿重复付款，可通过客服提供脱敏订单信息查询。",
  ]],
  ["五、知识产权与用户内容", [
    "你保留对合法上传的简历、JD、知识材料和其他用户内容依法享有的权利，并授权本服务在提供所选功能所必需的范围内处理这些内容。",
    "面试稳的程序、界面、品牌和服务内容受相关法律保护。未经允许不得复制、反向工程或用于建立竞争性服务，但法律明确允许的情形除外。",
  ]],
  ["六、服务变更与责任边界", [
    "我们会尽力维护服务安全与稳定，但网络、设备权限、第三方模型、语音识别、支付或云服务可能造成延迟、中断或结果偏差。页面不会对尚未验证的能力作保证。",
    "我们可能为安全、合规或产品改进调整功能。对涉及你权益的重要变更，将通过页面提示或其他合理方式说明。",
  ]],
  ["七、终止与联系", [
    "你可以停止使用服务，并通过产品内入口管理或删除现有资料和会话记录。严重违反本协议或危害服务安全时，我们可能限制相关账号或操作。",
    "如对本协议有疑问，请通过客服微信 mianshiwen-cn 或邮箱 contact@oneshowailab.com 联系。",
  ]],
] as const;

const privacySections = [
  ["一、我们处理的信息", [
    "账号信息：手机号、验证码校验记录、登录会话和必要的安全审计信息。验证码仅用于账号识别和登录校验。",
    "用户资料：你主动上传或填写的简历、职位 JD、知识材料及其解析文本、索引状态和版本信息。",
    "面试处理数据：手动问题、实时转录、生成建议、经你触发的截图及截图识别结果。原始音频默认不保存，音频帧仅用于当前转写链路。",
    "设备与运行信息：桌面助手设备标识、连接码、系统与版本、权限和采集健康状态、错误码及必要的性能指标。诊断不应保存原始音频或截图内容。",
    "交易信息：商品、金额、订单状态、支付渠道标识和权益到账记录。银行卡、支付密码等由支付机构处理，面试稳不保存支付密码。",
    "推广归因信息：当你通过面试稳生成的推广链接访问时，我们可能使用第一方随机匿名标识记录推广渠道、活动、内容链接、访问时间、站内目标、来源网站域名、设备大类和过滤状态。我们不为推广归因采集设备指纹、原始 IP、完整浏览器标识或面试内容。",
  ]],
  ["二、处理目的", [
    "我们处理上述信息，用于完成账号登录、资料管理、文档解析与检索、面试辅助、截图回答、积分和会员结算、故障排查、安全防护及履行法定义务。",
    "不会仅因你打开网页就自动开始收音或截图。麦克风、系统音频和屏幕权限由桌面助手在对应功能需要时申请或使用。",
  ]],
  ["三、第三方处理", [
    "为提供所选功能，必要内容可能发送给云存储、文档解析、语音识别、大模型推理、短信和支付等服务提供方。我们仅在实现功能所需范围内传输，并通过服务端保存访问凭证。",
    "第三方的具体处理还受其服务规则约束。我们不会把服务端 API 密钥存放在 Web 或桌面客户端。",
  ]],
  ["四、保存与安全", [
    "原始音频默认不保存。资料、转录、截图、回答和订单记录按照当前产品功能、账号管理和法定义务保留；目前没有向你承诺统一的自动删除期限。",
    "我们采用访问控制、传输加密、凭证隔离和最小化日志等措施保护信息，但任何网络系统都无法保证绝对安全。",
    "推广匿名标识计划保留 90 天，原始推广触点计划保留 180 天，获客归因窗口为注册前 30 天；不识别个人的渠道聚合结果可为经营分析长期保留。",
  ]],
  ["五、你的控制", [
    "你可以在资料库和面试复盘等现有入口查看、管理或删除相应资料、截图和会话记录。服务端未确认删除成功时，页面不会宣称已删除。",
    "如果现有入口无法完成你的请求，可通过客服提交访问、更正、删除或账号相关问题。为保护账号安全，我们可能需要核验必要身份信息。",
    "你可以退出非必要的推广归因。退出后推广链接、注册、下载、面试和支付仍可正常使用；系统会删除本浏览器的推广标识，后续最多保留不可跨会话关联的聚合访问计数。",
  ]],
  ["六、未成年人和规则边界", [
    "本服务主要面向具有相应民事行为能力的求职者。未成年人应在监护人指导下使用，并避免提交非必要的敏感个人信息。",
    "请遵守面试组织方规则和所在地关于录音、录屏及个人信息处理的要求，并在需要时取得参与者同意。",
  ]],
  ["七、更新与联系", [
    "数据流程、服务能力、运营主体或主要服务提供方发生重要变化时，我们会及时更新本政策并标注更新时间；涉及你权益的重要变化将通过页面提示或其他合理方式告知。",
    "隐私问题可通过客服微信 mianshiwen-cn 或邮箱 contact@oneshowailab.com 联系。请勿通过客服渠道发送密码、验证码或完整身份证件。",
  ]],
] as const;

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
