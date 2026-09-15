import { Suspense, useEffect, useMemo, useRef, useState, type FormEvent, type ReactNode } from "react";
import { BrowserRouter, Link, NavLink, Navigate, Outlet, Route, Routes, useLocation, useNavigate, useParams } from "react-router-dom";
import type { ContextLibrarySource } from "@offersteady/protocol";
import { BriefcaseIcon, CaretDownIcon, ChartLineUpIcon, ChatCircleTextIcon, ClipboardTextIcon, CodeIcon, GraduationCapIcon, IdentificationCardIcon, PaletteIcon, ScanIcon, UserFocusIcon } from "@phosphor-icons/react";
import type { PartnerProgramState, ProgrammingLanguage, SessionMode, SessionStatus, WebAppState } from "./domain";
import { runAdapterOperation } from "./api-client";
import { interviewAppAdapter } from "./app-adapter";
import { routes } from "./routes";
import { ContextPicker } from "./ContextPicker";
import { contextLevel, managedLibrarySources, selectionValidity } from "./context-selection";
import { assetUrl } from "./assets";
import { interviewPlatforms } from "./platform-brands";
import { LivePage, preloadLivePage, BillingPage, DownloadCenter, GuidePage, LegalPage, LibraryManager } from "./route-components";
import { resetTransientInterviewState } from "./live-workspace";
import { authClient } from "./auth-client";
import { materialUploadAdapter, saveMaterialDownload } from "./material-upload-adapter";
import { applyAppearancePreferences, persistAppearancePreferences, readAppearancePreferences, type AppearancePreferences } from "./appearance-preferences";
import { officialSocialContacts } from "./social-contacts";
import { companionUpdate, type CompanionUpdate } from "./platform";
import "./styles.css";
import "./homepage-commercial.css";
import { HomepageDownloads } from "./HomepageDownloads";
import { HomepageProductPreview } from "./HomepageProductPreview";
import { HomepagePricing } from "./HomepagePricing";
import type { PublicStartupSnapshot } from "./public-startup";
import { PrototypeContext, usePrototype } from "./app-context";


function PrototypeProvider({ children, initialAuthenticated, initialState, publicStartup }: { readonly children: ReactNode; readonly initialAuthenticated?: boolean | undefined; readonly initialState?: WebAppState | undefined; readonly publicStartup?: PublicStartupSnapshot | undefined }) {
  const { pathname } = useLocation();
  const [authenticated, setAuthenticatedState] = useState(() => initialAuthenticated ?? Boolean(authClient.readStoredSession()));
  const [state, setState] = useState<WebAppState | null>(() => initialState ? structuredClone(initialState) : null);
  const [loadError, setLoadError] = useState("");
  const [loadAttempt, setLoadAttempt] = useState(0);
  const automaticRetryCount = useRef(0);

  useEffect(() => {
    if (!initialAuthenticated || !initialState?.account) return;
    if (authClient.readStoredSession()) return;
    const storedAccount = authClient.readStoredAccount();
    if (storedAccount?.id === initialState.account.id) return;
    authClient.bootstrapPrototypeIdentity(initialState.account);
  }, [initialAuthenticated, initialState]);

  useEffect(() => {
    if (initialState) return;
    const controller = new AbortController();
    const existing = authClient.readStoredSession();
    const initialize = async () => {
      if (existing) {
        try {
          await authClient.restore(controller.signal);
          setAuthenticatedState(true);
          return interviewAppAdapter.loadState(controller.signal);
        } catch (error) {
          if (controller.signal.aborted) throw error;
          authClient.clear();
          setAuthenticatedState(false);
          return interviewAppAdapter.loadState(controller.signal, { auth: false });
        }
      } else {
        setAuthenticatedState(false);
      }
      return interviewAppAdapter.loadState(controller.signal, { auth: false });
    };
    void initialize()
      .then(next => {
        setState(next);
        setLoadError("");
      })
      .catch(error => {
        if (controller.signal.aborted) return;
        setLoadError(error instanceof Error ? error.message : "后端页面状态加载失败");
      });
    return () => controller.abort();
  }, [initialState, loadAttempt]);

  useEffect(() => {
    if (initialState || state || !loadError) return;
    const delayMs = Math.min(10_000, 1_500 * 2 ** automaticRetryCount.current);
    automaticRetryCount.current += 1;
    const timer = window.setTimeout(() => {
      setLoadError("");
      setLoadAttempt(value => value + 1);
    }, delayMs);
    return () => window.clearTimeout(timer);
  }, [initialState, loadError, state]);

  const retryInitialLoad = () => {
    automaticRetryCount.current = 0;
    setLoadError("");
    setLoadAttempt(value => value + 1);
  };

  const setAuthenticated = (value: boolean) => {
    setAuthenticatedState(value);
  };

  const logout = async () => {
    await authClient.logout();
    setAuthenticated(false);
    try { setState(await interviewAppAdapter.loadState()); } catch { setState(current => current); }
  };

  if (!state && publicStartup?.pathname === pathname && /^\/(?:guide|terms|privacy)?\/?$/.test(pathname)) {
    return <><div data-public-startup dangerouslySetInnerHTML={{ __html: publicStartup.html }} />{loadError ? <aside className="seo-prerender" role="status"><p>实时信息暂时未加载，产品介绍和公开页面仍可浏览。</p><button type="button" onClick={retryInitialLoad}>重新加载实时信息</button></aside> : null}</>;
  }
  if (!state && !loadError) return <RouteLoadingPage />;
  if (!state && loadError) return <IntegrationModeErrorPage message={loadError} onRetry={retryInitialLoad} />;

  if (!state) return <RouteLoadingPage />;
  return <PrototypeContext.Provider value={{ authenticated, setAuthenticated, state, setState: setState as React.Dispatch<React.SetStateAction<WebAppState>>, logout }}>{children}</PrototypeContext.Provider>;
}

const Logo = () => <span className="logo-lockup"><img src={assetUrl("brand.app-icon")} width="44" height="44" decoding="async" alt="" /><strong>面试稳AI助手</strong></span>;

function PublicLayout() {
  const { authenticated } = usePrototype();
  const { pathname } = useLocation();
  return (
    <div className={pathname === routes.landing ? "public-shell cn-home-shell" : "public-shell"}>
      <header className="public-nav">
        <Link to={routes.landing} aria-label="面试稳AI助手首页"><Logo /></Link>
        {pathname !== routes.landing && <Link className="button ghost partner-nav-entry" to={routes.partnerProgram}>合作伙伴计划</Link>}
        <nav aria-label="公开导航"><a href="/features">产品功能</a><a href="/#product-tour">使用演示</a><a href="/pricing">价格</a><a href="/download">下载</a>{pathname === routes.landing && <Link className="partner-nav-entry" to={routes.partnerProgram}>合作伙伴计划</Link>}<Link className="button ghost" to={authenticated ? routes.app : routes.login}>{authenticated ? "进入应用" : "登录"}</Link></nav>
      </header>
      <Outlet />
    </div>
  );
}

function LandingPage() {
  const { state } = usePrototype();
  const [partnerProgramEnabled, setPartnerProgramEnabled] = useState(false);
  useEffect(() => {
    const controller = new AbortController();
    void interviewAppAdapter.getPartnerProgramConfig(controller.signal)
      .then(config => setPartnerProgramEnabled(config.enabled))
      .catch(() => setPartnerProgramEnabled(false));
    return () => controller.abort();
  }, []);
  const paymentChannelsLabel = state.billing.availablePaymentChannels.length ? state.billing.availablePaymentChannels.map(channel => channel === "wechat" ? "微信支付" : "支付宝").join("、") : "当前未开启在线支付渠道";
  return <main className="cn-commercial-home">
    <section className="landing-hero">
      <div><span className="kicker">面试稳 · AI 面试助手</span><h1>AI 面试助手，<br /><em>让你的经历更好表达。</em></h1>
        <p>面试稳是一款面向求职者的AI面试助手。结合你的简历与目标岗位，整理更贴合自己的回答思路。</p>
        <div className="hero-actions"><Link className="button primary large" to={routes.login}>免费使用 <span>→</span></Link><a className="text-link" href="#product-tour">看看怎么用 ↗</a></div>
        <HomepageDownloads manifest={state.releaseManifest} />
        <p className="cn-hero-note">AI 建议仅供参考，请以真实经历作答，并遵守面试规则。</p>
      </div>
      <HomepageProductPreview />
    </section>
    <section id="core-capabilities" className="public-section"><div className="section-intro"><span className="kicker">围绕你的面试</span><h2>从听清问题，到讲清自己</h2><p>把问题、资料和回答思路放在一起，表达更有条理。</p></div>
      <div className="cn-benefits">
        <article><ChatCircleTextIcon size={28} aria-hidden="true" /><h3>跟上每一个问题</h3><p>实时转写面试官与自己的声音，减少来回整理，把注意力留给交流。</p></article>
        <article><IdentificationCardIcon size={28} aria-hidden="true" /><h3>回答更贴合你的经历</h3><p>按场选择简历、JD 和知识材料，围绕自己的项目与目标岗位组织回答。</p></article>
        <article><ScanIcon size={28} aria-hidden="true" /><h3>截图题，也有思路</h3><p>通过电脑助手截取题目，查看识别与生成进度，无需手动重新输入。</p></article>
        <article><ClipboardTextIcon size={28} aria-hidden="true" /><h3>让下一场准备更充分</h3><p>回看问题、回答建议与资料来源，整理需要补充的经历和表达。</p></article>
      </div>
    </section>
    <section id="product-tour" className="public-section cn-tour-section">
      <div className="cn-tour-layout">
        <div className="section-intro"><span className="kicker">从准备到开始</span><h2>三步，把工具用起来。</h2><div className="cn-tour-steps" aria-label="开始使用的三个步骤"><div><span>01</span><div><h3>准备简历与岗位资料</h3><p>添加简历、JD，按需选择知识材料。</p></div></div><div><span>02</span><div><h3>连接电脑助手</h3><p>检查连接、声音与采集权限。</p></div></div><div><span>03</span><div><h3>获取建议，自己表达</h3><p>用语音、输入或截图提问，核对后组织回答。</p></div></div></div><Link className="text-link" to={routes.publicGuide}>打开使用手册 ↗</Link></div>
        <div className="cn-tutorial-media"><div className="landing-film-frame"><video aria-label="面试稳工具使用教程" controls muted playsInline preload="none" poster="/media/device-story-poster-20260907.jpg"><source src="/media/device-story-voice-20260907.mp4" type="video/mp4" /></video></div><span className="cn-tour-caption">真实操作演示 · 内容为合成示例</span></div>
      </div>
      <details className="cn-film-details"><summary>也可以先看产品概览<CaretDownIcon size={18} aria-hidden="true" /></summary><div className="landing-film-frame"><video aria-label="面试稳产品宣传片" controls muted playsInline preload="none" poster="/media/offersteady-commercial-poster.jpg"><source src="/media/offersteady-commercial.web.mp4" type="video/mp4" /></video></div></details>
    </section>
    <HomepagePricing billing={state.billing} />
    <section id="more-scenarios" className="public-section cn-more-scenarios"><div className="section-intro"><span className="kicker">不同岗位，同样认真准备</span><h2>找到与你相关的面试场景。</h2></div><div className="cn-scenario-paths"><a href="/features/ai-interview-assistant"><CodeIcon size={24} aria-hidden="true" /><h3>程序员与技术岗位</h3><p>项目追问、技术原理与系统设计。</p><span>查看技术面试场景 ↗</span></a><a href="/features/realtime-interview"><ChatCircleTextIcon size={24} aria-hidden="true" /><h3>业务追问与现场表达</h3><p>听清问题，结合资料组织思路。</p><span>了解实时辅助 ↗</span></a><a href="/guides"><GraduationCapIcon size={24} aria-hidden="true" /><h3>首次面试与转岗准备</h3><p>梳理经历，让表达贴近目标岗位。</p><span>浏览面试指南 ↗</span></a></div><details><summary>更多岗位与常见使用平台</summary>
      <section id="platform-compatibility" className="public-section platform-compatibility" aria-labelledby="platform-compatibility-title">
        <div className="platform-compatibility-intro"><span className="kicker">PLATFORM COMPATIBILITY</span><h2 id="platform-compatibility-title">适配常见远程面试与在线笔试平台</h2><p>电脑伴随助手通过你明确授权的系统音频、麦克风和截图能力工作，无需安装平台插件。</p></div>
        <ul className="platform-grid" aria-label="常见使用平台">{interviewPlatforms.map(platform => <li className={`platform-card brand-${platform.slug}`} data-brand-source={platform.sourcePage} key={platform.name}><span className={`platform-brand platform-brand-${platform.presentation}`}><img src={platform.logoUrl} width="180" height="48" alt={`${platform.name} 品牌标识`} loading="lazy" decoding="async" referrerPolicy="no-referrer" onError={event => { event.currentTarget.hidden = true; }} /><span className={platform.presentation === "wordmark" ? "sr-only" : "platform-brand-copy"}><strong>{platform.name}</strong>{platform.secondaryLabel ? <small>{platform.secondaryLabel}</small> : null}</span></span></li>)}</ul>
      </section>

      <section id="user-scenarios" className="public-section user-scenarios" aria-labelledby="user-scenarios-title">
        <div className="user-scenarios-intro"><span className="kicker">ROLE-BASED WORKFLOWS</span><h2 id="user-scenarios-title">覆盖多种岗位与面试场景</h2><p>按岗位查看面试稳如何结合简历、JD、知识库、实时语音和截图回答，帮助你更快组织真实经历与专业表达。</p></div>
        <div className="user-scenarios-grid">
          <article className="user-scenario-card"><header><span className="user-scenario-icon" aria-hidden="true"><BriefcaseIcon size={25} weight="duotone" /></span><div><h3>产品经理 · 社招面试</h3><span>业务追问与项目复盘</span></div></header><div className="scenario-focus"><span>典型困扰</span><strong>项目讲得很长，却没有突出自己的决策</strong></div><p>如果遇到连续追问，可以结合已选择的简历和目标岗位 JD，按“目标—判断—行动—结果”整理回答思路，把重点拉回自己的真实贡献。</p><footer className="scenario-capabilities" aria-label="使用能力"><span>简历与 JD</span><span>实时回答</span><span>资料来源</span></footer></article>
          <article className="user-scenario-card"><header><span className="user-scenario-icon" aria-hidden="true"><CodeIcon size={25} weight="duotone" /></span><div><h3>后端工程师 · 技术面</h3><span>系统设计与深度追问</span></div></header><div className="scenario-focus"><span>典型困扰</span><strong>系统设计有思路，但容量与取舍容易讲散</strong></div><p>可以把准备过的架构材料加入知识库，让回答建议围绕题目整理容量、可靠性与技术取舍，同时保留自己项目的真实边界，不照搬模板。</p><footer className="scenario-capabilities" aria-label="使用能力"><span>知识库</span><span>实时回答</span><span>面试复盘</span></footer></article>
          <article className="user-scenario-card"><header><span className="user-scenario-icon" aria-hidden="true"><ChartLineUpIcon size={25} weight="duotone" /></span><div><h3>数据分析师 · 案例面</h3><span>图表、SQL 与业务分析</span></div></header><div className="scenario-focus"><span>典型困扰</span><strong>截图题信息密集，一时找不到分析入口</strong></div><p>遇到图表或 SQL 截图题时，可以通过伴随助手发起截图回答，在网页查看上传、识别和生成状态，再结合岗位要求组织分析路径与结论。</p><footer className="scenario-capabilities" aria-label="使用能力"><span>截图回答</span><span>JD 上下文</span><span>状态追踪</span></footer></article>
          <article className="user-scenario-card"><header><span className="user-scenario-icon" aria-hidden="true"><GraduationCapIcon size={25} weight="duotone" /></span><div><h3>应届毕业生 · 首次面试</h3><span>自我介绍与行为问题</span></div></header><div className="scenario-focus"><span>典型困扰</span><strong>经历不多，回答行为问题时容易紧张空白</strong></div><p>可以使用简历中的课程、实习和项目作为可核对素材，按背景、行动和收获组织表达；内容始终以真实经历为准，不为了完整而虚构。</p><footer className="scenario-capabilities" aria-label="使用能力"><span>简历上下文</span><span>回答建议</span><span>问题记录</span></footer></article>
          <article className="user-scenario-card"><header><span className="user-scenario-icon" aria-hidden="true"><PaletteIcon size={25} weight="duotone" /></span><div><h3>设计岗位 · 作品集面试</h3><span>方案说明与协作追问</span></div></header><div className="scenario-focus"><span>典型困扰</span><strong>作品集很完整，但方案取舍没有讲清楚</strong></div><p>可以把作品集要点整理为知识材料，围绕用户问题、方案选择和协作过程组织回答；结束后根据问题记录检查哪些案例还需要补充证据。</p><footer className="scenario-capabilities" aria-label="使用能力"><span>知识材料</span><span>实时回答</span><span>面试复盘</span></footer></article>
          <article className="user-scenario-card"><header><span className="user-scenario-icon" aria-hidden="true"><UserFocusIcon size={25} weight="duotone" /></span><div><h3>跨行业求职者 · 转岗面试</h3><span>能力迁移与岗位匹配</span></div></header><div className="scenario-focus"><span>典型困扰</span><strong>原行业经历丰富，却很难对应目标岗位</strong></div><p>可以为每个岗位单独选择简历版本和 JD，把原行业经历整理为可迁移能力；再查看回答实际引用的资料，判断表达是否贴近目标岗位。</p><footer className="scenario-capabilities" aria-label="使用能力"><span>多版本简历</span><span>JD 上下文</span><span>来源核对</span></footer></article>
        </div>
      </section>

    </details></section>
    <section id="product-facts" className="public-section" aria-label="产品信息与常见问题">
        <div className="public-faq" aria-labelledby="public-faq-title">
          <div className="public-faq-intro"><span className="kicker">开始前，你可能想知道</span><h2 id="public-faq-title">常见问题</h2><p>关于使用、费用和隐私的说明。</p><a className="text-link" href="/guide">查看完整使用手册 ↗</a></div>
          <div className="public-faq-list">
            <details><summary><span>面试稳是什么？</span><CaretDownIcon size={18} aria-hidden="true" /></summary><div><p>面试稳是一款面向求职者的AI面试助手，通过语音、手动输入或截图整理问题，结合本场选择的简历、JD 和知识资料提供回答建议。</p></div></details>
            <details><summary><span>AI 面试助手如何工作？</span><CaretDownIcon size={18} aria-hidden="true" /></summary><div><p>先准备资料并连接电脑助手，再选择本场上下文。系统识别或接收问题、生成回答建议，最后由你核对事实并用自己的语言表达。了解<a href="/features/realtime-interview">实时面试辅助流程</a>，或查看<a href="/features/ai-interview-assistant">程序员与技术岗位场景</a>。</p></div></details>
            <details><summary><span>面试稳如何收费？</span><CaretDownIcon size={18} aria-hidden="true" /></summary><div><p>提供积分包和按天会员，适合不同使用频率。无需登录即可查看<a href="/pricing">当前套餐价格、有效期与计费边界</a>，购买通过账户内的积分与会员页面完成。</p></div></details>
            <details><summary><span>面试稳AI助手适合哪些岗位？</span><CaretDownIcon size={18} aria-hidden="true" /></summary><div><p>适用于需要结构化表达、专业追问或截图题辅助的求职场景，例如产品、技术、数据、设计、运营等岗位。建议质量取决于问题识别、你选择的简历与 JD 以及真实资料完整度，不能保证面试或录用结果。</p></div></details>
            <details><summary><span>面试稳可以免费使用吗？</span><CaretDownIcon size={18} aria-hidden="true" /></summary><div><p>可以先免费使用。具体可用权益和后续使用方式以登录后的“积分与会员”页面实时显示为准；需要高频使用时也可以选择按天会员。</p></div></details>
            <details><summary><span>支持哪些问题输入方式？</span><CaretDownIcon size={18} aria-hidden="true" /></summary><div><p>支持电脑伴随助手授权后的语音输入、网页手动输入和截图题回答。设备收音不可用时仍可切换到手动输入；截图任务会显示上传、识别和生成状态。</p></div></details>
            <details><summary><span>支持哪些设备平台？</span><CaretDownIcon size={18} aria-hidden="true" /></summary><div><p>设备中心会按当前发布状态提供 macOS Apple Silicon、macOS Intel 和 Windows 版本；未完成签名或仍在预览的版本会明确提示。手机端可用于同步查看回答和会话状态。</p></div></details>
            <details><summary><span>支持哪些支付方式？</span><CaretDownIcon size={18} aria-hidden="true" /></summary><div><p>{paymentChannelsLabel}。实际可用方式以“积分与会员”页面的实时显示为准；支付成功以后端验签结果为准，返回支付页本身不代表权益已经到账。</p></div></details>
            <details><summary><span>使用面试稳会造成信息泄露吗？</span><CaretDownIcon size={18} aria-hidden="true" /></summary><div><p>产品默认不保存原始音频；简历、JD、知识材料、截图和会话记录提供管理或删除入口。请不要上传与求职无关的敏感信息，完整处理规则可查看<Link to={routes.privacy}>隐私政策</Link>。</p></div></details>
          </div>
        </div>

    </section>
    <section className="cn-closing"><div><span className="kicker">为下一场面试做好准备</span><h2>让准备过的经历，表达得更清楚。</h2><p>先体验，再决定适合自己的使用方式。</p></div><Link className="button primary large" to={routes.login}>免费使用 →</Link></section>
      {partnerProgramEnabled ? <section className="cn-partner-inline" aria-label="合作伙伴计划"><p>分享面试稳，获得 20% 推广佣金。</p><Link to={routes.partnerProgram}>了解合作伙伴计划 ↗</Link></section> : null}
      <footer className="public-footer">
        <div className="public-footer-main">
          <section className="footer-brand"><Logo /><p>面向求职者的 AI 面试辅助工具，从资料准备、现场表达建议到面试复盘，让每一次面试更有条理。</p><span>AI 输出仅供参考，请始终以真实经历作答。</span></section>
          <nav className="footer-column footer-primary-links" aria-label="页脚常用导航"><h2>常用入口</h2><a href="/features">产品功能</a><a href="/interview-questions">面试题与专题</a><a href="/guides">面试指南</a><Link to={routes.publicGuide}>使用手册</Link></nav>
          <section className="footer-contact"><h2>联系我们</h2><dl><div><dt>客服微信</dt><dd>{state.billing.support.wechatId || "暂未配置"}</dd></div><div><dt>联系邮箱</dt><dd>{state.billing.support.email ? <a href={`mailto:${state.billing.support.email}`}>{state.billing.support.email}</a> : "暂未配置"}</dd></div>{officialSocialContacts.map(contact => <div key={contact.id}><dt>{contact.label}</dt><dd>{contact.account}</dd></div>)}<div><dt>服务时间</dt><dd>{state.billing.support.serviceHours || "请通过邮箱留言"}</dd></div></dl><p>咨询订单时请提供订单号，请勿发送密码、验证码或完整身份资料。</p></section>
        </div>
        <details className="footer-more">
          <summary><span>查看更多资源</span><CaretDownIcon size={16} aria-hidden="true" /></summary>
          <div className="footer-more-grid">
            <nav className="footer-column" aria-label="页脚产品导航"><h2>产品</h2><a href="/features/ai-interview-assistant">AI 面试助手</a><a href="/features/realtime-interview">实时面试辅助</a><a href="/features/screenshot-answer">截图回答</a><a href="/features/interview-review">面试复盘</a><a href="/pricing">积分与会员</a><a href="/download">下载助手</a></nav>
            <nav className="footer-column" aria-label="页脚资源导航"><h2>更多内容</h2><Link to={`${routes.publicGuide}#desktop`}>下载安装说明</Link><a href="/guides/interview-preparation">面试准备清单</a><a href="/guides/star-interview-answer">STAR 回答结构</a><a href="/guides/audio-troubleshooting">收音问题排查</a><a href="/security">安全说明</a><a href="/about">关于产品</a><a href="/contact">联系我们</a><Link to={routes.terms}>用户协议</Link><Link to={routes.privacy}>隐私政策</Link></nav>
          </div>
        </details>
        <div className="public-footer-legal">
          <span>© 2026 面试稳AI助手 · OneShow AI Lab</span>
          <div className="public-footer-filings" aria-label="网站备案信息">
            <a href="https://beian.miit.gov.cn" target="_blank" rel="noreferrer">浙ICP备2026052190号-1</a>
            <a href="https://www.beian.gov.cn/portal/registerSystemInfo?recordcode=33010602014812" target="_blank" rel="noreferrer">浙公网安备33010602014812号</a>
          </div>
        </div>
      </footer>

  </main>;
}

function LoginPage() {
  const { authenticated, setAuthenticated, setState } = usePrototype();
  const navigate = useNavigate();
  const location = useLocation();
  const [phoneNumber, setPhoneNumber] = useState("");
  const [code, setCode] = useState("");
  const [challengeId, setChallengeId] = useState("");
  const [cooldown, setCooldown] = useState(0);
  const [busy, setBusy] = useState<"send" | "verify" | "">("");
  const [message, setMessage] = useState("");
  const destination = (location.state as { from?: string } | null)?.from ?? routes.app;
  const enter = () => { setAuthenticated(true); navigate(destination, { replace: true }); };
  const enterWithAccount = (account: WebAppState["account"]) => {
    setState(current => ({ ...current, account }));
    void interviewAppAdapter.loadState().then(next => setState(next)).catch(() => undefined);
    enter();
  };
  useEffect(() => {
    if (cooldown <= 0) return;
    const id = window.setTimeout(() => setCooldown(value => Math.max(0, value - 1)), 1000);
    return () => window.clearTimeout(id);
  }, [cooldown]);
  if (authenticated) return <Navigate to={destination} replace />;
  const sendCode = async (event: FormEvent) => {
    event.preventDefault();
    setBusy("send");
    setMessage("");
    try {
      const response = await authClient.sendSmsCode(phoneNumber);
      setChallengeId(response.challengeId);
      setCooldown(response.cooldownSeconds);
      setMessage(`验证码已发送至 ${response.maskedPhone}`);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "验证码发送失败");
    } finally {
      setBusy("");
    }
  };
  const verifyCode = async (event: FormEvent) => {
    event.preventDefault();
    if (!challengeId && !code.trim()) {
      setMessage("请先获取验证码");
      return;
    }
    setBusy("verify");
    setMessage("");
    try {
      const session = await authClient.verifySmsLogin({ phoneNumber, challengeId, code });
      enterWithAccount(session.account);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "登录失败，请稍后重试");
    } finally {
      setBusy("");
    }
  };
  return <main className="center-page"><section className="login-card"><Logo /><span className="prototype-badge">当前可免费使用</span><h1>开始你的面试准备</h1><p>使用手机号验证码完成登录或注册，同一个账号可以管理资料、积分和不同设备上的面试。</p><form className="sms-login-form" onSubmit={challengeId || code.trim() ? verifyCode : sendCode}><label><span>手机号</span><input value={phoneNumber} onChange={event => setPhoneNumber(event.target.value)} inputMode="tel" autoComplete="tel" placeholder="请输入手机号" /></label><label><span>验证码</span><input value={code} onChange={event => setCode(event.target.value)} inputMode="numeric" autoComplete="one-time-code" placeholder="请输入验证码" /></label><div className="sms-actions"><button className="button primary large full" type="submit" disabled={Boolean(busy)}>{busy === "verify" ? "登录中..." : challengeId || code.trim() ? "登录 / 注册" : busy === "send" ? "发送中..." : "获取验证码"}</button>{challengeId ? <button className="button ghost full" type="button" disabled={cooldown > 0 || Boolean(busy)} onClick={event => { void sendCode(event as unknown as FormEvent); }}>{cooldown > 0 ? `${cooldown}s 后重发` : "重新发送验证码"}</button> : null}</div></form>{message ? <p className="login-message">{message}</p> : null}<Link className="text-link login-back" to={routes.landing}>返回首页</Link><small className="login-legal-copy">登录即表示你同意<Link to={routes.terms}>用户协议</Link>与<Link to={routes.privacy}>隐私政策</Link>。验证码只用于账号识别和登录校验。</small></section></main>;
}

function ReferralLandingPage() {
  const { authenticated } = usePrototype();
  const { code = "" } = useParams();
  const navigate = useNavigate();
  const [status, setStatus] = useState<"loading" | "ready" | "invalid" | "disabled">("loading");
  const [rewards, setRewards] = useState<{ inviter: number; invitee: number } | null>(null);
  const [activating, setActivating] = useState(false);
  const [result, setResult] = useState("");
  useEffect(() => {
    const controller = new AbortController();
    void runAdapterOperation(signal => interviewAppAdapter.resolveReferral(code, signal), controller.signal).then(referral => {
      setRewards({
        inviter: referral.inviterRewardPoints ?? referral.rewardPoints ?? 0,
        invitee: referral.inviteeRewardPoints ?? referral.rewardPoints ?? 0,
      });
      setStatus(!referral.valid ? "invalid" : referral.enabled ? "ready" : "disabled");
    }).catch(() => setStatus("invalid"));
    return () => controller.abort();
  }, [code]);
  const activate = async () => {
    if (!authenticated) {
      navigate(routes.login, { state: { from: routes.invite(code) } });
      return;
    }
    setActivating(true); setResult("");
    try {
      const activation = await runAdapterOperation(signal => interviewAppAdapter.activateReferral(code, signal));
      setResult(activation.outcome === "activated" ? (activation.replayed ? "你已经激活过这个邀请，无需重复操作。" : `邀请已成功激活，你获得 ${activation.inviteeRewardPoints ?? rewards?.invitee ?? 0} 点，好友获得 ${activation.inviterRewardPoints ?? activation.rewardPoints ?? rewards?.inviter ?? 0} 点。`) : activation.outcome === "already-activated" ? "当前账号已经激活过其他邀请，每个账号只能激活一次。" : activation.outcome === "self-referral" ? "不能激活自己的邀请链接。" : activation.outcome === "disabled" ? "邀请活动目前已暂停。" : activation.outcome === "activation-window-expired" ? "邀请链接仅限新用户注册后 3 天内激活，你的激活期限已过。" : activation.outcome === "registration-time-unavailable" ? "暂时无法确认账号注册时间，请联系客服处理。" : "邀请链接无效或已撤销。");
    } catch (error) { setResult(error instanceof Error ? error.message : "激活失败，请稍后重试"); }
    finally { setActivating(false); }
  };
  return <main className="center-page referral-landing"><section className="referral-landing-card"><Logo /><span className="kicker">INVITATION</span><h1>好友邀请你体验面试稳</h1>{status === "loading" ? <p>正在安全校验邀请链接…</p> : status === "invalid" ? <><p>这个邀请链接无效或已撤销，没有创建任何邀请关系。</p><Link className="button primary full" to={routes.landing}>返回首页</Link></> : status === "disabled" ? <><p>邀请活动目前暂停，历史奖励不会受影响。你仍然可以免费使用产品。</p><Link className="button primary full" to={routes.login}>登录使用</Link></> : <><div className="referral-reward-preview"><strong>双方都有奖励</strong><span>你获得 {rewards?.invitee ?? 0} 点，分享链接的好友获得 {rewards?.inviter ?? 0} 点</span></div><p>仅限注册后 3 天内的新用户激活。每个账号只能激活一次，不能激活自己的链接。</p><button className="button primary full" disabled={activating} onClick={() => void activate()}>{activating ? "激活中…" : authenticated ? "确认激活邀请" : "登录并激活"}</button></>}{result ? <div className="referral-result" role="status">{result}<Link to={routes.billing}>查看积分与会员</Link></div> : null}<small>邀请关系只记录账号标识和奖励流水，不公开手机号或设备信息。</small></section></main>;
}

function ProtectedRoute() {
  const { authenticated } = usePrototype();
  const location = useLocation();
  return authenticated ? <Outlet /> : <Navigate to={routes.login} state={{ from: location.pathname }} replace />;
}

const USER_MANUAL_URL = "https://pwksrh0z1i6.feishu.cn/drive/folder/KFlcfWorslX2hmdyyByc2fLvngp?from=from_copylink";

const navItems = [
  { to: routes.app, label: "面试模式", icon: "◫", end: true },
  { to: routes.writtenExams, label: "笔试模式", icon: "◇" },
  { to: routes.library, label: "资料", icon: "◇" },
  { to: routes.billing, label: "积分与会员", icon: "点" },
  { to: routes.partnerProgram, label: "合作伙伴计划", icon: "◇" },
  { to: routes.guide, label: "使用说明", icon: "?" },
  { href: USER_MANUAL_URL, label: "用户手册", icon: "册" },
  { to: routes.devices, label: "设备", icon: "⌘" },
  { to: routes.settings, label: "设置", icon: "○" },
];

function WorkbenchNavigationItems({ mobile = false }: { readonly mobile?: boolean }) {
  return <>{navItems.map(item => "href" in item
    ? <a key={item.href} href={item.href} target="_blank" rel="noopener noreferrer" aria-label={item.label}><span aria-hidden="true">{item.icon}</span>{mobile ? <small>{item.label}</small> : item.label}</a>
    : <NavLink key={item.to} to={item.to} className={({ isActive }) => isActive ? "active" : ""} {...(item.end ? { end: true } : {})}><span aria-hidden="true">{item.icon}</span>{mobile ? <small>{item.label}</small> : item.label}</NavLink>)}</>;
}

function AccountMenu({ compact = false, dropUp = false }: { readonly compact?: boolean; readonly dropUp?: boolean }) {
  const { logout, state } = usePrototype();
  const navigate = useNavigate();
  const [busy, setBusy] = useState(false);
  const initials = state.account.displayName.slice(0, 2).toUpperCase();
  const leaveAccount = async () => {
    if (busy) return;
    setBusy(true);
    try {
      await logout();
      navigate(routes.login, { replace: true });
    } finally {
      setBusy(false);
    }
  };
  return <details className={`account-menu${compact ? " compact" : ""}${dropUp ? " drop-up" : ""}`}>
    <summary role="button" aria-label="账号菜单" aria-haspopup="menu"><i>{initials}</i>{compact ? null : <span>{state.account.displayName}<small>账号管理</small></span>}</summary>
    <div className="account-menu-popover">
      <div><small>当前账号</small><strong>{state.account.displayName}</strong></div>
      <button type="button" disabled={busy} onClick={() => void leaveAccount()}>切换账号</button>
      <button type="button" className="account-logout" disabled={busy} onClick={() => void leaveAccount()}>{busy ? "正在退出…" : "退出登录"}</button>
    </div>
  </details>;
}

function AppLayout() {
  return (
    <div className="app-shell">
      <aside className="app-sidebar"><Link to={routes.app}><Logo /></Link><nav aria-label="应用导航"><WorkbenchNavigationItems /></nav><div className="sidebar-foot"><span className="privacy-note">音频默认不保存</span><AccountMenu dropUp /></div></aside>
      <div className="app-content"><Outlet /></div>
      <nav className="mobile-nav" aria-label="移动端应用导航"><WorkbenchNavigationItems mobile /><AccountMenu compact dropUp /></nav>
    </div>
  );
}

function PageHeader({ eyebrow, title, detail, action }: { readonly eyebrow: string; readonly title: string; readonly detail?: string; readonly action?: ReactNode }) {
  return <header className="page-header"><div><span className="kicker">{eyebrow}</span><h1>{title}</h1>{detail ? <p>{detail}</p> : null}</div>{action}</header>;
}

export const interviewContinuationRoute = (interview: Pick<WebAppState["interviews"][number], "id" | "status">) => interview.status === "ended"
  ? routes.review(interview.id)
  : interview.status === "active" || interview.status === "paused" || interview.status === "error"
    ? routes.live(interview.id)
    : routes.prepare(interview.id);

const sessionHomeRoute = (mode?: SessionMode) => mode === "written" ? routes.writtenExams : routes.app;

const sessionStatusLabel: Record<SessionStatus, string> = { preparing: "准备中", ready: "待开始", active: "进行中", paused: "已暂停", ended: "已结束", error: "待恢复" };

function HomePage() {
  const { state, setState } = usePrototype();
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [deleteError, setDeleteError] = useState("");
  const recentInterviews = state.interviews.filter(item => item.sessionMode !== "written").slice(0, 5);
  const materialSources = state.librarySources.filter(source => source.status !== "deleted" && source.status !== "disabled");
  const readyMaterials = materialSources.filter(source => source.status === "ready" && source.syncStatus !== "missing_artifacts");
  const processingMaterials = materialSources.filter(source => source.status === "processing");
  const materialCount = (kind: "resume" | "jd" | "knowledge") => materialSources.filter(source => source.kind === kind).length;
  const readyMaterialCount = (kind: "resume" | "jd" | "knowledge") => readyMaterials.filter(source => source.kind === kind).length;
  const active = recentInterviews.find(item => item.status !== "ended");
  const hour = new Date().getHours(); const greeting = Number.isFinite(hour) ? hour < 5 ? "夜深了" : hour < 11 ? "早上好" : hour < 14 ? "中午好" : hour < 18 ? "下午好" : "晚上好" : "你好";
  const title = active ? "继续这场面试" : "准备好下一场面试了吗？";
  const deleteRecentInterview = async (interviewId: string) => {
    if (!window.confirm("确认删除这场面试？对应问题、回答与附件会一起删除。")) return;
    setDeleteError("");
    setDeletingId(interviewId);
    try {
      await runAdapterOperation(signal => interviewAppAdapter.deleteInterview(interviewId, signal));
      try {
        const next = await runAdapterOperation(signal => interviewAppAdapter.loadState(signal));
        setState(next);
      } catch {
        setState(current => ({ ...current, interviews: current.interviews.filter(item => item.id !== interviewId) }));
      }
    } catch (error) {
      setDeleteError(error instanceof Error ? error.message : "删除失败，请稍后重试。");
    } finally {
      setDeletingId(null);
    }
  };
  return <main className="app-page"><PageHeader eyebrow={`${greeting} · INTERVIEW HOME`} title={title} detail={active ? "资料、设备和面试状态都在这里，接着上次的进度继续。" : "创建面试并选择对应资料，让每个回答更贴近目标岗位。"} action={<Link className="button primary" to={routes.newInterview}>＋ 新建面试</Link>} />
    {active ? <section className="continue-card"><div><span className="live-chip"><i /> {sessionStatusLabel[active.status]}</span><h2>{active.title}</h2><p>{active.company} · {active.role}</p><div className="progress-line"><i style={{ width: `${active.readiness}%` }} /></div><small>准备完成 {active.readiness}% · 简历、JD 与知识库按本场选择</small></div><div className="continue-actions"><Link className="button primary" to={interviewContinuationRoute(active)}>继续面试</Link></div></section> : <EmptyState title="创建第一场面试" detail="用合成资料走完准备、现场和复盘流程。" action={<Link className="button primary" to={routes.newInterview}>开始创建</Link>} />}
    <section className="dashboard-grid"><div className="panel"><div className="panel-heading"><h2>最近面试</h2><span>{recentInterviews.length} / 5 场</span></div>{deleteError ? <div className="inline-error" role="alert">{deleteError}</div> : null}<div className="interview-list">{recentInterviews.map(item => <article key={item.id} className="recent-interview-row"><Link to={interviewContinuationRoute(item)}><span className={`status-icon ${item.status}`}>{item.status === "ended" ? "✓" : "↗"}</span><div><strong>{item.title}</strong><small>{item.updatedAt} · {sessionStatusLabel[item.status]}</small></div><span>→</span></Link><button type="button" disabled={deletingId === item.id} onClick={() => void deleteRecentInterview(item.id)}>{deletingId === item.id ? "删除中…" : "删除"}</button></article>)}</div></div><div className="panel readiness-panel"><div className="panel-heading"><h2>通用资料</h2><Link to={routes.library}>管理</Link></div><div className="readiness-ring"><strong>{readyMaterials.length}</strong><span>份已就绪</span></div><ul className="compact-list"><li><span>简历</span><b>{readyMaterialCount("resume")} / {materialCount("resume")} 份可用</b></li><li><span>职位 JD</span><b>{readyMaterialCount("jd")} / {materialCount("jd")} 份可用</b></li><li><span>知识材料</span><b>{readyMaterialCount("knowledge")} / {materialCount("knowledge")} 份可用</b></li></ul>{processingMaterials.length ? <small>{processingMaterials.length} 份资料正在后台处理中</small> : null}</div></section>
  </main>;
}

function WrittenExamHomePage() {
  const { state, setState } = usePrototype();
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [deleteError, setDeleteError] = useState("");
  const recentExams = state.interviews.filter(item => item.sessionMode === "written").slice(0, 5);
  const active = recentExams.find(item => item.status !== "ended");
  const deleteRecentExam = async (sessionId: string) => {
    if (!window.confirm("确认删除这场笔试？对应截图和回答记录会一起删除。")) return;
    setDeleteError("");
    setDeletingId(sessionId);
    try {
      await runAdapterOperation(signal => interviewAppAdapter.deleteInterview(sessionId, signal));
      try {
        setState(await runAdapterOperation(signal => interviewAppAdapter.loadState(signal)));
      } catch {
        setState(current => ({ ...current, interviews: current.interviews.filter(item => item.id !== sessionId) }));
      }
    } catch (error) {
      setDeleteError(error instanceof Error ? error.message : "删除失败，请稍后重试。");
    } finally {
      setDeletingId(null);
    }
  };
  return <main className="app-page"><PageHeader eyebrow="WRITTEN EXAM MODE" title={active ? "继续这场笔试" : "准备好下一场笔试了吗？"} detail="笔试模式仅使用截屏回答，不启用收音、实时转写或快答。" action={<Link className="button primary" to={routes.newWrittenExam}>＋ 新建笔试</Link>} />
    {active ? <section className="continue-card"><div><span className="live-chip"><i /> {sessionStatusLabel[active.status]}</span><h2>{active.title}</h2><p>{active.company} · {active.role}</p><div className="progress-line"><i style={{ width: `${active.readiness}%` }} /></div><small>仅使用截屏回答 · 不启用音频</small></div><div className="continue-actions"><Link className="button primary" to={interviewContinuationRoute(active)}>继续笔试</Link></div></section> : <EmptyState title="创建第一场笔试" detail="连接伴随助手后，通过截屏识别题目并生成回答。" action={<Link className="button primary" to={routes.newWrittenExam}>开始创建</Link>} />}
    <section className="dashboard-grid"><div className="panel"><div className="panel-heading"><h2>最近笔试</h2><span>{recentExams.length} / 5 场</span></div>{deleteError ? <div className="inline-error" role="alert">{deleteError}</div> : null}<div className="interview-list">{recentExams.map(item => <article key={item.id} className="recent-interview-row"><Link to={interviewContinuationRoute(item)}><span className={`status-icon ${item.status}`}>{item.status === "ended" ? "✓" : "↗"}</span><div><strong>{item.title}</strong><small>{item.updatedAt} · {sessionStatusLabel[item.status]}</small></div><span>→</span></Link><button type="button" disabled={deletingId === item.id} onClick={() => void deleteRecentExam(item.id)}>{deletingId === item.id ? "删除中…" : "删除"}</button></article>)}</div></div><div className="panel readiness-panel"><div className="panel-heading"><h2>笔试说明</h2><Link to={routes.billing}>收费说明</Link></div><ul className="compact-list"><li><span>进入笔试</span><b>30 积分 / 次</b></li><li><span>答题方式</span><b>仅截屏回答</b></li><li><span>音频采集</span><b>不启用</b></li></ul></div></section>
  </main>;
}

function EmptyState({ title, detail, action }: { readonly title: string; readonly detail: string; readonly action?: ReactNode }) { return <section className="empty-state"><span>◇</span><h2>{title}</h2><p>{detail}</p>{action}</section>; }

function NewInterviewPage() {
  const navigate = useNavigate();
  const { state, setState } = usePrototype();
  const [form, setForm] = useState(() => {
    const latest = state.interviews.find(item => item.sessionMode !== "written");
    return latest
      ? { title: latest.title, role: latest.role, company: latest.company ?? "" }
      : { title: "", role: "", company: "" };
  });
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (!form.title.trim() || !form.role.trim()) { setError("请填写面试名称和目标岗位"); return; }
    setError("");
    setSaving(true);
    try {
      const draft = await runAdapterOperation(signal => interviewAppAdapter.createDraft(form, signal));
      setState(current => {
        const reset = resetTransientInterviewState(current);
        return {
          ...reset,
          interviews: [draft, ...current.interviews.filter(item => item.id !== draft.id)].slice(0, 5),
          contextSelections: { ...current.contextSelections, [draft.id]: { sessionId: draft.id, resumeSourceId: null, jobDescriptionSourceId: null, knowledgeSourceIds: [], revision: 0, confirmedAtMs: null } },
        };
      });
      navigate(routes.prepare(draft.id), { state: { newlyCreatedInterview: true } });
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "创建面试失败，请稍后重试。");
    } finally {
      setSaving(false);
    }
  };
  return <main className="app-page narrow"><Link className="back-link" to={routes.app}>← 返回面试首页</Link><PageHeader eyebrow="NEW INTERVIEW" title="创建一场面试" detail="先给这场面试一个清晰目标，资料可以在下一步补充。" /><form className="form-panel" onSubmit={submit}><label>面试名称<input value={form.title} onChange={e => setForm({ ...form, title: e.target.value })} placeholder="例如：高级前端工程师一面" /></label><label>目标岗位<input value={form.role} onChange={e => setForm({ ...form, role: e.target.value })} placeholder="例如：高级前端工程师" /></label><label>公司（可选）<input value={form.company} onChange={e => setForm({ ...form, company: e.target.value })} placeholder="例如：示例科技" /></label>{error ? <div className="inline-error" role="alert">{error}</div> : null}<div className="form-actions"><Link className="button ghost" to={routes.app}>取消</Link><button className="button primary" type="submit" disabled={saving}>{saving ? "创建中…" : "保存并准备 →"}</button></div><small className="saved-note">草稿只在你确认提交后保存。</small></form></main>;
}

function NewWrittenExamPage() {
  const navigate = useNavigate();
  const { state, setState } = usePrototype();
  const latest = state.interviews.find(item => item.sessionMode === "written");
  const [form, setForm] = useState(() => latest ? { title: latest.title, role: latest.role, company: latest.company ?? "" } : { title: "", role: "", company: "" });
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (!form.title.trim() || !form.role.trim()) { setError("请填写笔试名称和目标岗位"); return; }
    setError("");
    setSaving(true);
    try {
      const draft = await runAdapterOperation(signal => interviewAppAdapter.createDraft({ ...form, sessionMode: "written" }, signal));
      setState(current => {
        const reset = resetTransientInterviewState(current);
        return {
          ...reset,
          interviews: [draft, ...current.interviews.filter(item => item.id !== draft.id)].slice(0, 5),
          contextSelections: { ...current.contextSelections, [draft.id]: { sessionId: draft.id, resumeSourceId: null, jobDescriptionSourceId: null, knowledgeSourceIds: [], revision: 0, confirmedAtMs: Date.now() } },
        };
      });
      navigate(routes.prepare(draft.id), { state: { newlyCreatedInterview: true } });
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "创建笔试失败，请稍后重试。");
    } finally {
      setSaving(false);
    }
  };
  return <main className="app-page narrow"><Link className="back-link" to={routes.writtenExams}>← 返回笔试模式</Link><PageHeader eyebrow="NEW WRITTEN EXAM" title="创建一场笔试" detail="笔试模式只使用截屏回答，不启用收音和实时转写。" /><form className="form-panel" onSubmit={submit}><label>笔试名称<input value={form.title} onChange={event => setForm({ ...form, title: event.target.value })} placeholder="例如：算法笔试" /></label><label>目标岗位<input value={form.role} onChange={event => setForm({ ...form, role: event.target.value })} placeholder="例如：算法工程师" /></label><label>公司（可选）<input value={form.company} onChange={event => setForm({ ...form, company: event.target.value })} placeholder="例如：示例科技" /></label>{error ? <div className="inline-error" role="alert">{error}</div> : null}<div className="form-actions"><Link className="button ghost" to={routes.writtenExams}>取消</Link><button className="button primary" type="submit" disabled={saving}>{saving ? "创建中…" : "保存并准备 →"}</button></div><small className="saved-note">成功进入笔试固定扣除 30 积分，每次截屏回答按现有规则计费。</small></form></main>;
}

function CompanionUpdateReminder({ update, onContinue }: { readonly update: CompanionUpdate; readonly onContinue: () => void }) {
  return <section className="companion-update-reminder" aria-label="伴随程序更新提醒">
    <span aria-hidden="true">↑</span>
    <div><strong>发现新版伴随程序 {update.release.version}</strong><small>当前版本 {update.currentVersion}，建议更新到与你设备匹配的最新版；本次也可以继续使用。</small></div>
    <div className="companion-update-actions"><a className="button primary" href={update.release.downloadUrl} download>立即下载</a><button className="button ghost" type="button" onClick={onContinue}>继续使用</button></div>
  </section>;
}

function PreparationPage() {
  useEffect(() => { void preloadLivePage(); }, []);
  const { id = "demo" } = useParams();
  const { state, setState } = usePrototype();
  const navigate = useNavigate();
  const location = useLocation();
  const newlyCreatedInterview = (location.state as { newlyCreatedInterview?: boolean } | null)?.newlyCreatedInterview === true;
  const [starting, setStarting] = useState(false);
  const [startError, setStartError] = useState("");
  const [materialConfirmError, setMaterialConfirmError] = useState("");
  const [confirmingMaterials, setConfirmingMaterials] = useState(false);
  const [machineCode, setMachineCode] = useState("");
  const [deviceBinding, setDeviceBinding] = useState<Awaited<ReturnType<typeof interviewAppAdapter.getDesktopDeviceBinding>> | null>(null);
  const [lastDevice, setLastDevice] = useState<Awaited<ReturnType<NonNullable<typeof interviewAppAdapter.getLastDesktopDevice>>> | null>(null);
  const [binding, setBinding] = useState(false);
  const [bindingError, setBindingError] = useState("");
  const [dismissedUpdateKey, setDismissedUpdateKey] = useState("");
  const [activeConflict, setActiveConflict] = useState<Awaited<ReturnType<typeof interviewAppAdapter.getActiveInterviewConflict>>["activeInterview"] | undefined>(undefined);
  const [conflictError, setConflictError] = useState("");
  const [resolvingConflict, setResolvingConflict] = useState(false);
  const [savingLanguage, setSavingLanguage] = useState(false);
  const [languageError, setLanguageError] = useState("");
  const [savingProgramming, setSavingProgramming] = useState(false);
  const [programmingError, setProgrammingError] = useState("");
  const interview = state.interviews.find(item => item.id === id);
  const interviewTitle = interview?.title ?? "本场面试";
  const isWritten = interview?.sessionMode === "written";
  const interviewLanguage = interview?.interviewLanguage ?? "zh-CN";
  const programmingRequired = interview?.programmingRequired ?? false;
  const programmingLanguage = interview?.programmingLanguage ?? "python";
  const selection = state.contextSelections[id] ?? state.contextSelections.demo!;
  const managedSources = managedLibrarySources(state.librarySources, state.account.id);
  const validity = selectionValidity(managedSources, selection);
  const level = contextLevel(selection);
  const selectionReady = isWritten || validity === "valid";
  const machineReady = Boolean(deviceBinding);
  const conflictResolved = activeConflict === null;
  const canStart = selectionReady && machineReady && conflictResolved;
  const availableUpdate = useMemo(
    () => deviceBinding ? companionUpdate(deviceBinding.capabilities, state.releaseManifest) : null,
    [deviceBinding, state.releaseManifest],
  );
  const updateKey = availableUpdate && deviceBinding ? `${deviceBinding.bindingId}:${availableUpdate.release.id}` : "";
  const visibleUpdate = availableUpdate && updateKey !== dismissedUpdateKey ? availableUpdate : null;
  const complete = isWritten ? Number(machineReady) : Number(selectionReady) + Number(machineReady);
  const inputDiagnostic = machineReady
      ? "伴随程序已连接，正在后台准备音频与实时识别"
      : state.preparation.device?.connected
      ? "本地端会继续检查收音、系统音频和问题检测"
      : "请输入桌面伴随程序中的 6 位机器码，绑定本场收音机器";
  const saveSelection = async (next: typeof selection) => {
    if (confirmingMaterials) return;
    setConfirmingMaterials(true);
    setMaterialConfirmError("");
    try {
      const confirmed = await runAdapterOperation(signal => interviewAppAdapter.confirmInterviewMaterials(next, signal));
      setState(current => ({
        ...current,
        contextSelections: { ...current.contextSelections, [id]: confirmed },
        interviews: current.interviews.map(item => item.id === id ? { ...item, readiness: confirmed.confirmedAtMs ? 100 : 0 } : item),
      }));
    } catch (error) {
      setMaterialConfirmError(error instanceof Error ? error.message : "确认本场资料失败，请稍后重试。");
    } finally {
      setConfirmingMaterials(false);
    }
  };
  const saveInterviewLanguage = async (nextLanguage: "zh-CN" | "en-US") => {
    if (savingLanguage || nextLanguage === interviewLanguage) return;
    setSavingLanguage(true);
    setLanguageError("");
    try {
      const updated = await runAdapterOperation(signal => interviewAppAdapter.updateInterviewLanguage(id, nextLanguage, signal));
      setState(current => ({
        ...current,
        interviews: current.interviews.map(item => item.id === id ? { ...item, ...updated } : item),
      }));
    } catch (error) {
      setLanguageError(error instanceof Error ? error.message : "面试语言保存失败，请重试。");
    } finally {
      setSavingLanguage(false);
    }
  };
  const saveInterviewProgramming = async (required: boolean, language: ProgrammingLanguage | null) => {
    if (savingProgramming) return;
    const normalizedLanguage = required ? language ?? "python" : null;
    if (required === programmingRequired && normalizedLanguage === (programmingRequired ? programmingLanguage : null)) return;
    setSavingProgramming(true);
    setProgrammingError("");
    try {
      const updated = await runAdapterOperation(signal => interviewAppAdapter.updateInterviewProgramming(id, required, normalizedLanguage, signal));
      setState(current => ({
        ...current,
        interviews: current.interviews.map(item => item.id === id ? { ...item, ...updated } : item),
      }));
    } catch (error) {
      setProgrammingError(error instanceof Error ? error.message : "编程设置保存失败，请重试。");
    } finally {
      setSavingProgramming(false);
    }
  };
  const downloadMaterial = async (source: ContextLibrarySource) => {
    setMaterialConfirmError("");
    try {
      const result = await runAdapterOperation(signal => materialUploadAdapter.downloadDocument(state.account.id, source.documentId ?? source.id, signal));
      saveMaterialDownload(result);
    } catch (error) {
      setMaterialConfirmError(error instanceof Error ? error.message : "资料下载失败，请稍后重试。");
    }
  };
  useEffect(() => {
    const controller = new AbortController();
    void Promise.all([
      runAdapterOperation(signal => interviewAppAdapter.getDesktopDeviceBinding(id, signal), controller.signal).catch(() => null),
      interviewAppAdapter.getLastDesktopDevice
        ? runAdapterOperation(signal => interviewAppAdapter.getLastDesktopDevice!(signal), controller.signal).catch(() => null)
        : Promise.resolve(null),
      runAdapterOperation(signal => interviewAppAdapter.getActiveInterviewConflict(id, signal), controller.signal),
    ]).then(([binding, recent, conflict]) => {
        setLastDevice(recent);
        setActiveConflict(conflict.activeInterview);
        setConflictError("");
        if (!binding) return;
        setDeviceBinding(binding);
        setMachineCode(binding.manualCode);
      })
      .catch(error => setConflictError(error instanceof Error ? error.message : "无法确认当前账号的面试状态，请稍后重试。"));
    return () => controller.abort();
  }, [id, newlyCreatedInterview]);
  useEffect(() => {
    if (!deviceBinding) return;
    let stopped = false;
    const heartbeat = async () => {
      try {
        await runAdapterOperation(signal => interviewAppAdapter.sendDesktopSessionHeartbeat({
          interviewId: id,
          bindingId: deviceBinding.bindingId,
          page: "preparation",
        }, signal));
      } catch {
        // Heartbeat is retried in the background; do not replace user-facing bind/start errors.
      }
    };
    void heartbeat();
    const timer = window.setInterval(() => void heartbeat(), 3000);
    return () => {
      stopped = true;
      window.clearInterval(timer);
    };
  }, [id, deviceBinding?.bindingId]);
  const connectDesktopDevice = async (reuseLastDevice = false) => {
    if (!conflictResolved) {
      setBindingError(activeConflict ? "请先处理正在进行中的面试。" : "正在确认账号的面试状态，请稍候。");
      return;
    }
    const code = machineCode.trim();
    if (!reuseLastDevice && !/^[0-9]{6}$/.test(code)) { setBindingError("请输入电脑伴随程序显示的 6 位机器码"); return; }
    setBinding(true); setBindingError("");
    try {
      const result = await runAdapterOperation(signal => interviewAppAdapter.bindDesktopDevice({
        interviewId: id,
        ...(reuseLastDevice ? { reuseLastDevice: true } : { manualCode: code }),
      }, signal));
      setDeviceBinding(result);
      setMachineCode(result.manualCode);
    } catch (error) {
      setBindingError(error instanceof Error ? error.message : "机器码验证失败，请确认电脑伴随程序已打开。");
    } finally {
      setBinding(false);
    }
  };
  const supersedePreviousInterview = async () => {
    if (!activeConflict || resolvingConflict) return;
    setResolvingConflict(true);
    setConflictError("");
    try {
      await runAdapterOperation(signal => interviewAppAdapter.supersedeActiveInterview({
        interviewId: id,
        expectedPreviousInterviewId: activeConflict.id,
      }, signal));
      setActiveConflict(null);
      setDeviceBinding(null);
      setBindingError("");
    } catch (error) {
      setConflictError(error instanceof Error ? error.message : "切换面试失败，请刷新后重试。");
      try {
        const refreshed = await runAdapterOperation(signal => interviewAppAdapter.getActiveInterviewConflict(id, signal));
        setActiveConflict(refreshed.activeInterview);
      } catch {
        // Preserve the visible conflict until the authoritative state can be loaded.
      }
    } finally {
      setResolvingConflict(false);
    }
  };
  const startInterview = async () => {
    if (!canStart || starting) return;
    setStarting(true); setStartError("");
    try {
      const started = await runAdapterOperation(signal => interviewAppAdapter.startInterviewSession(id, signal));
      setState(current => ({ ...current, interviews: current.interviews.map(item => item.id === id ? { ...item, ...started, status: "active" } : item) }));
      navigate(routes.live(id));
    } catch (error) {
      setStartError(error instanceof Error ? error.message : "开始面试失败，请稍后重试。");
    } finally {
      setStarting(false);
    }
  };
  if (isWritten) return <main className="app-page narrow written-preparation-page">
    <Link className="back-link" to={routes.writtenExams}>← 返回笔试模式</Link>
    <PageHeader eyebrow="WRITTEN EXAM" title={interviewTitle} detail="连接伴随助手后即可开始。" />
    <section className="panel written-preparation-card">
      <div className="panel-heading">
        <h2>连接伴随助手</h2>
        <span className={machineReady ? "written-connection-ready" : ""}>{machineReady ? "已连接" : "待连接"}</span>
      </div>
      {deviceBinding ? <div className="written-connected-device"><i>✓</i><span><strong>{deviceBinding.displayName}</strong><small>助手连接正常</small></span></div> : null}
      {activeConflict ? <div className="inline-error" role="alert">上一场会话仍在进行，请先结束上一场。<button className="button ghost" disabled={resolvingConflict} onClick={() => void supersedePreviousInterview()}>{resolvingConflict ? "正在切换…" : "结束上一场"}</button></div> : null}
      <div className="machine-code-panel written-machine-code-panel">
        <label><span>机器码</span><input inputMode="numeric" maxLength={6} value={machineCode} onChange={event => setMachineCode(event.target.value.replace(/\D/g, "").slice(0, 6))} placeholder="输入 6 位机器码" /></label>
        <button className="button ghost" disabled={!conflictResolved || binding || machineReady && machineCode === deviceBinding?.manualCode} onClick={() => void connectDesktopDevice(false)}>{binding ? "连接中…" : "验证连接"}</button>
        {lastDevice ? <button className="button primary" disabled={!conflictResolved || binding || !lastDevice.online || deviceBinding?.deviceId === lastDevice.deviceId} onClick={() => void connectDesktopDevice(true)}>{deviceBinding?.deviceId === lastDevice.deviceId ? "上次设备已连接" : "连接上次设备"}</button> : null}
        {bindingError ? <div className="inline-error" role="alert">{bindingError}</div> : null}
      </div>
      {visibleUpdate ? <CompanionUpdateReminder update={visibleUpdate} onContinue={() => setDismissedUpdateKey(updateKey)} /> : null}
      {startError ? <div className="inline-error written-start-error" role="alert">{startError}</div> : null}
      <div className="written-start-row">
        <small>开始时扣除 30 积分</small>
        <button className="button primary" disabled={!canStart || starting} onClick={() => void startInterview()}>{starting ? "正在进入…" : "开始笔试 →"}</button>
      </div>
    </section>
  </main>;
  return <main className="app-page"><Link className="back-link" to={routes.app}>← 返回面试首页</Link><PageHeader eyebrow="PREPARATION" title={interviewTitle} detail="资料与“面试资料”页面保持一致，为本场按需选择。" action={<div className="completion"><strong>{complete}/2</strong><span>{canStart ? "可进入" : "准备中"}</span></div>} />
    <div className="prepare-grid"><section className="panel"><fieldset className="interview-language-picker" disabled={savingLanguage}><legend>面试语言</legend><p>用于本场实时识别、问题判断和 AI 回答；开始面试后将锁定。</p><div><label className={interviewLanguage === "zh-CN" ? "selected" : ""}><input type="radio" name="interview-language" value="zh-CN" checked={interviewLanguage === "zh-CN"} onChange={() => void saveInterviewLanguage("zh-CN")} /><span><strong>中文面试</strong><small>沿用当前中文识别与回答链路</small></span></label><label className={interviewLanguage === "en-US" ? "selected" : ""}><input type="radio" name="interview-language" value="en-US" checked={interviewLanguage === "en-US"} onChange={() => void saveInterviewLanguage("en-US")} /><span><strong>English Interview</strong><small>English transcription and AI answers</small></span></label></div>{savingLanguage ? <small role="status">正在保存面试语言…</small> : null}{languageError ? <div className="inline-error" role="alert">{languageError}</div> : null}</fieldset><fieldset className="programming-preference" disabled={savingProgramming}><legend>编程设置</legend><div className="programming-toggle-row"><span><strong>需要编程</strong><small>开启后，代码题会统一使用你选择的编程语言</small></span><label className="switch-control"><input type="checkbox" role="switch" checked={programmingRequired} onChange={event => void saveInterviewProgramming(event.target.checked, event.target.checked ? programmingLanguage : null)} /><span aria-hidden="true" /></label></div>{programmingRequired ? <div className="programming-language-options" role="radiogroup" aria-label="编程语言">{([['python', 'Python'], ['java', 'Java'], ['cpp', 'C++'], ['javascript', 'JavaScript'], ['typescript', 'TypeScript'], ['go', 'Go']] as const).map(([value, label]) => <label key={value} className={programmingLanguage === value ? "selected" : ""}><input type="radio" name="programming-language" value={value} checked={programmingLanguage === value} onChange={() => void saveInterviewProgramming(true, value)} /><span>{label}</span></label>)}</div> : null}{savingProgramming ? <small role="status">正在保存编程设置…</small> : null}{programmingError ? <div className="inline-error" role="alert">{programmingError}</div> : null}</fieldset><ContextPicker sources={managedSources} selection={selection} onSave={saveSelection} onDownload={downloadMaterial} />{confirmingMaterials ? <div className="context-warning" role="status">正在提交后端校验并保存本场资料…</div> : null}{materialConfirmError ? <div className="context-warning" role="alert">{materialConfirmError}</div> : null}</section>
      <aside className="panel check-panel"><div className="panel-heading"><h2>开始前检查</h2><span>{canStart ? "可进入" : !selectionReady ? "待确认资料" : "待绑定机器"}</span></div><ul className="check-list"><li className={selectionReady ? "done" : ""}><i>{selectionReady ? "✓" : "1"}</i><div><strong>本场资料</strong><span>{validity === "unconfirmed" ? "请选择资料或确认不使用资料" : validity === "attention-required" ? "所选资料已失效，请处理" : level === "none" ? "已确认不使用个人资料" : level === "personalized" ? "简历与 JD 已选择" : "已确认使用部分资料"}</span></div></li><li className={machineReady ? "done" : ""}><i>{machineReady ? "✓" : "2"}</i><div><strong>收音机器</strong><span>{deviceBinding ? `${deviceBinding.displayName} 已连接，后台正在预热实时链路` : inputDiagnostic}</span></div></li></ul>
        <div className="machine-code-panel">
          <strong className="connection-choice-title">连接桌面助手</strong>
          <label><span>{newlyCreatedInterview ? "输入机器码连接本场" : "重新输入机器码"}</span><input inputMode="numeric" maxLength={6} value={machineCode} onChange={event => setMachineCode(event.target.value.replace(/\D/g, "").slice(0, 6))} placeholder="输入 6 位机器码" /></label>
          <button className="button ghost" disabled={!conflictResolved || binding || machineReady && machineCode === deviceBinding?.manualCode} onClick={() => void connectDesktopDevice(false)}>{binding ? "连接中…" : "验证并连接"}</button>
          <small>{deviceBinding ? `本场已连接：${deviceBinding.displayName}` : "输入助手显示的固定机器码，或直接连接当前账号上次使用的设备。"}</small>
          {bindingError ? <div className="inline-error" role="alert">{bindingError}</div> : null}
          {lastDevice ? <><div className="connection-divider"><span>或使用上次设备</span></div><div className={`last-device-choice ${lastDevice.online ? "online" : "offline"}`}><span><b>{lastDevice.displayName}</b><small>{lastDevice.online ? `设备在线 · ${lastDevice.maskedManualCode}` : "设备离线，请先打开助手"}</small></span><button className="button primary" disabled={!conflictResolved || binding || !lastDevice.online || deviceBinding?.deviceId === lastDevice.deviceId} onClick={() => void connectDesktopDevice(true)}>{deviceBinding?.deviceId === lastDevice.deviceId ? "已连接本场" : "一键连接上次设备"}</button></div></> : null}
        </div>
        {visibleUpdate ? <CompanionUpdateReminder update={visibleUpdate} onContinue={() => setDismissedUpdateKey(updateKey)} /> : null}
        <div className="device-mini"><span className="device-glyph">⌘</span><div><strong>{deviceBinding?.displayName ?? state.preparation.device?.displayName ?? "电脑伴随程序"}</strong><small>{deviceBinding ? "本场设备已连接；系统权限沿用助手首次授权结果" : "当前仅缺少本场设备连接，不代表助手系统权限失效"}</small></div><Link to={routes.devices}>管理</Link></div>
        <div className="privacy-confirm preparation-disclosure"><span><strong>本场数据说明</strong><small>已选资料和转录仅用于生成回答建议；原始音频默认不保存，会话记录可在复盘中删除。麦克风和屏幕权限只由桌面助手首次申请，网页不会再次申请。</small></span></div>
        <div className="points-mini"><strong>{state.billing.balance} 点</strong><span>回答 5 点 · 截图 15 点</span><Link to={routes.billing}>查看收费说明</Link><Link to={`${routes.guide}#quick-start`}>准备流程说明</Link></div>
        {startError ? <div className="inline-error" role="alert">{startError}</div> : null}<button className="button primary full" disabled={!canStart || starting} onClick={() => void startInterview()}>{starting ? "正在开始面试…" : "开始面试 →"}</button>{!selectionReady ? <small className="blocked-help">确认本场资料选择（可以为空）后继续。</small> : !machineReady ? <small className="blocked-help">请选择上次设备或输入机器码，为本场建立设备连接。</small> : level === "none" ? <small className="blocked-help context-disclosure">本场未使用个人资料。伴随程序会在后台准备音频，开始后直接切换到实时链路。</small> : <small className="blocked-help context-disclosure">伴随程序正在后台准备麦克风、电脑输出和识别服务；无需播放测试音或提前说话。</small>}
      </aside></div>
    {activeConflict ? <div className="sheet-backdrop" role="dialog" aria-modal="true" aria-labelledby="active-interview-conflict-title"><section className="sheet active-interview-conflict-sheet"><span className="conflict-kicker">单设备 · 单场面试</span><h2 id="active-interview-conflict-title">已有一场面试正在进行</h2><p>为避免旧页面和新页面同时占用语音链路，请先选择如何继续。</p><div className="active-interview-card"><span>进行中</span><strong>{activeConflict.title}</strong><small>结束上一场只会停止实时连接，历史记录和资料不会删除。</small></div>{conflictError ? <div className="inline-error" role="alert">{conflictError}</div> : null}<div className="sheet-actions conflict-actions"><button className="button primary" disabled={resolvingConflict} onClick={() => navigate(routes.live(activeConflict.id))}>继续上一场面试</button><button className="button ghost" disabled={resolvingConflict} onClick={() => void supersedePreviousInterview()}>{resolvingConflict ? "正在切换…" : "结束上一场，准备当前面试"}</button></div><Link className="conflict-return" to={routes.app}>暂不进入，返回面试首页</Link></section></div> : null}
  </main>;
}

function ReviewPage() {
  const { id = "review" } = useParams();
  const { state, setState } = usePrototype();
  const navigate = useNavigate();
  const [reviewStatus, setReviewStatus] = useState(state.review.status);
  const [deleteError, setDeleteError] = useState("");
  const [deletingShotId, setDeletingShotId] = useState<string | null>(null);
  const [deletingInterview, setDeletingInterview] = useState(false);
  const [reviewLoading, setReviewLoading] = useState(true);
  const [reviewLoadError, setReviewLoadError] = useState("");
  const [wordExportState, setWordExportState] = useState<"idle" | "generating" | "success" | "error">("idle");
  const interview = state.interviews.find(item => item.id === id);
  const isWritten = interview?.sessionMode === "written";
  useEffect(() => {
    const controller = new AbortController();
    setReviewLoading(true);
    setReviewLoadError("");
    void Promise.all([
      runAdapterOperation(signal => interviewAppAdapter.loadInterviewReview(id, signal), controller.signal),
      runAdapterOperation(signal => interviewAppAdapter.loadInterviewWorkspace(id, signal), controller.signal)
        .catch(error => {
          if (error instanceof DOMException && error.name === "AbortError") throw error;
          return null;
        }),
    ])
      .then(([review, workspace]) => {
        setState(current => ({
          ...current,
          review: { ...current.review, ...review, screenshots: current.review.screenshots },
          questions: workspace ? [...workspace.questions] : current.questions,
          activeAnswerTask: workspace ? workspace.activeAnswerTask : current.activeAnswerTask,
        }));
        setReviewStatus(review.status);
      })
      .catch(error => {
        if (error instanceof DOMException && error.name === "AbortError") return;
        setReviewLoadError(error instanceof Error ? error.message : "复盘对话加载失败，请稍后重试。");
      })
      .finally(() => setReviewLoading(false));
    return () => controller.abort();
  }, [id, setState]);
  const downloadReview = async () => {
    if (wordExportState === "generating") return;
    const title = state.review.title || interview?.title || "面试复盘";
    setWordExportState("generating");
    try {
      const { createInterviewReviewWordBlob, downloadInterviewReviewWord, interviewReviewWordFilename } = await import("./interview-review-word-export");
      const blob = await createInterviewReviewWordBlob(state.review, state.questions, interview);
      downloadInterviewReviewWord(interviewReviewWordFilename(title, state.review.endedAtMs), blob);
      setWordExportState("success");
    } catch {
      setWordExportState("error");
    }
  };
  const deleteShot = async (shotId: string) => { setDeleteError(""); setDeletingShotId(shotId); try { await runAdapterOperation(signal => interviewAppAdapter.deleteScreenshot(shotId, signal)); setState(current => ({ ...current, review: { ...current.review, screenshots: current.review.screenshots.filter(item => item.id !== shotId) } })); } catch { setDeleteError("截图删除失败，记录仍然保留，请重试。"); } finally { setDeletingShotId(null); } };
  const deleteInterview = async () => { if (!window.confirm(isWritten ? "删除整场笔试及其截图题和回答记录？" : "删除整场面试及其问题、回答和会话附件？可复用简历与知识库仍会保留。")) return; setDeleteError(""); setDeletingInterview(true); try { await runAdapterOperation(signal => interviewAppAdapter.deleteInterview(id, signal)); setState(current => ({ ...current, interviews: current.interviews.filter(item => item.id !== id), questions: [] })); navigate(sessionHomeRoute(interview?.sessionMode)); } catch { setDeleteError(isWritten ? "整场笔试删除失败，现有记录未改变，请重试。" : "整场面试删除失败，现有记录未改变，请重试。"); } finally { setDeletingInterview(false); } };
  if (isWritten) {
    const writtenQuestions = state.questions.filter(question => question.input === "screenshot");
    return <main className="app-page narrow written-result-page">
      <Link className="back-link" to={routes.writtenExams}>← 返回笔试模式</Link>
      <PageHeader eyebrow="WRITTEN EXAM RESULT" title={interview.title} detail="本场答题记录已保留，可随时从最近笔试重新查看。" action={<Link className="button primary" to={routes.writtenExams}>完成</Link>} />
      {reviewLoadError ? <div className="inline-error" role="status">{reviewLoadError}</div> : null}
      <section className="panel written-result-card">
        <div className="panel-heading"><h2>本场答题记录</h2><span>{writtenQuestions.length} 题</span></div>
        {reviewLoading ? <p className="review-loading">正在加载答题记录…</p> : writtenQuestions.length ? <div className="written-result-list">{[...writtenQuestions].reverse().map((question, index) => <article key={question.id}><header><span>第 {index + 1} 题</span><small>{question.askedAt}</small></header><h3>{question.text}</h3><div><strong>回答</strong><p>{question.advice.detail}</p></div></article>)}</div> : <EmptyState title="本场暂无答题记录" detail="本场笔试已经结束，没有保存成功的截屏回答。" />}
      </section>
      <div className="written-result-actions">
        {deleteError ? <div className="inline-error" role="alert">{deleteError}</div> : null}
        <button className="button danger" disabled={deletingInterview} onClick={() => void deleteInterview()}>{deletingInterview ? "正在删除…" : "删除本场笔试"}</button>
      </div>
    </main>;
  }
  return <main className="app-page"><Link className="back-link" to={routes.app}>← 返回面试首页</Link><PageHeader eyebrow="INTERVIEW REVIEW" title="本场面试复盘" detail="整理语音转写与 AI 回答建议，不对你的能力作自动评分。" action={<div className="review-header-actions"><button type="button" className="button primary" onClick={() => void downloadReview()} disabled={reviewLoading || wordExportState === "generating"}>{wordExportState === "generating" ? "正在生成 Word…" : "下载 Word"}</button><div className="review-meta"><strong>{state.review.duration}</strong><span>{state.review.transcripts.length} 条对话 · {state.questions.length} 个问题</span></div></div>} />
    <p className={`review-download-note${wordExportState === "error" ? " error-text" : ""}`} role={wordExportState === "error" ? "alert" : undefined}>{wordExportState === "error" ? "Word 生成失败，请重试。当前复盘内容不会丢失。" : wordExportState === "success" ? "Word 已生成并开始下载，请妥善保管本场面试对话。" : "Word 文件包含本场面试对话，仅在你的浏览器本地生成，请妥善保管。"}</p>{reviewLoadError ? <div className="inline-error" role="status">{reviewLoadError}</div> : null}
    <div className="review-grid"><div className="review-main"><section className="panel"><div className="panel-heading"><h2>真实对话记录</h2><span>语音转写</span></div>{reviewLoading ? <p className="review-loading">正在加载本场对话…</p> : state.review.transcripts.length ? <div className="review-transcript-list">{state.review.transcripts.map(item => <article key={item.id} className={`review-transcript ${item.role}`}><header><strong>{item.speakerLabel}</strong><time dateTime={new Date(item.occurredAtMs).toISOString()}>{new Date(item.occurredAtMs).toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false })}</time></header><p>{item.text}</p></article>)}</div> : <EmptyState title="没有可用的对话转写" detail="旧场次或未成功收音的场次可能没有持久语音转写，已有问题与 AI 建议仍可查看。" />}</section><section className="panel"><div className="panel-heading"><h2>问题与 AI 回答建议</h2><span>生成建议，不代表实际作答</span></div>{state.questions.length ? <div className="review-timeline">{[...state.questions].reverse().map((question, index) => <article key={question.id}><i>{index + 1}</i><div><small>{question.askedAt} · {question.input === "screenshot" ? "截图题" : question.input === "manual" ? "手动输入" : "音频转写"}</small><h3>{question.text}</h3><p>{question.advice.outline.join("；")}</p><div className="source-pills"><small>资料 v{question.advice.provenance.selectionRevision}</small>{question.advice.provenance.usedSources.map(source => <span key={source.sourceId}>{source.displayName}</span>)}</div></div></article>)}</div> : <EmptyState title="没有可复盘的问题" detail="本场面试没有已确认的问题记录。" />}</section></div>
      <aside><section className="panel review-summary"><div className="panel-heading"><h2>AI 整理摘要</h2><span className={reviewStatus}>{reviewStatus === "complete" ? "已生成" : reviewStatus === "failed" ? "生成失败" : "处理中"}</span></div>{reviewStatus === "complete" ? <><p>{state.review.summary}</p><div className="evidence-box"><span>说明</span><p>这是基于本场记录的生成建议，与原始问题记录分开保存。</p></div></> : reviewStatus === "failed" ? <div className="inline-error">摘要生成失败，原始记录仍可查看。<button onClick={() => setReviewStatus("complete")}>重试</button></div> : <p>正在整理本场已确认问题…</p>}</section><section className="panel data-panel"><div className="panel-heading"><h2>数据与附件</h2><span>可删除</span></div>{deleteError ? <div className="inline-error" role="alert">{deleteError}</div> : null}<ul className="compact-list"><li><span>简历与知识库</span><b>作为可复用资料保留</b></li><li><span>对话转写</span><b>随会话保存并删除</b></li><li><span>问题与 AI 建议</span><b>随会话保存</b></li>{state.review.screenshots.map(shot => <li key={shot.id}><span>{shot.name}</span><button disabled={deletingShotId === shot.id} onClick={() => void deleteShot(shot.id)}>{deletingShotId === shot.id ? "删除中…" : "删除截图"}</button></li>)}</ul><button className="button danger full" disabled={deletingInterview} onClick={() => void deleteInterview()}>{deletingInterview ? "正在删除…" : "删除整场面试"}</button></section></aside></div>
  </main>;
}

function LibraryPage() { const { state, setState } = usePrototype(); return <LibraryManager state={state} setState={setState} />; }

const money = (cents = 0) => new Intl.NumberFormat("zh-CN", { style: "currency", currency: "CNY", minimumFractionDigits: 2 }).format(cents / 100);

function PartnerProgramPage() {
  const [partner, setPartner] = useState<PartnerProgramState | null>(null);
  const [accepted, setAccepted] = useState(false);
  const [busy, setBusy] = useState<"join" | "payout" | "">("");
  const [message, setMessage] = useState("");
  const [payoutDraft, setPayoutDraft] = useState({ payoutMethod: "alipay" as "alipay" | "wechat", accountName: "", accountIdentifier: "" });
  const load = async (clearMessage = true) => {
    try { setPartner(await interviewAppAdapter.getPartnerProgram()); if (clearMessage) setMessage(""); }
    catch (error) { setMessage(error instanceof Error ? error.message : "合作伙伴数据暂时无法读取"); }
  };
  useEffect(() => { void load(); }, []);
  const join = async () => {
    if (!partner || !accepted) return;
    setBusy("join");
    try { setPartner(await interviewAppAdapter.joinPartnerProgram(partner.config.agreementVersion)); setMessage("合作伙伴计划已开通。专属链接可立即分享。"); }
    catch (error) { setMessage(error instanceof Error ? error.message : "暂时无法加入，请稍后重试"); }
    finally { setBusy(""); }
  };
  const payout = async () => {
    if (partner?.config.payoutProfileEnabled && !partner.payoutProfile) { setMessage("请先保存收款信息，再申请结算。"); return; }
    setBusy("payout");
    try { await interviewAppAdapter.requestPartnerPayout(); setMessage("本月结算申请已提交，我们会在审核后联系你。"); await load(false); }
    catch (error) { setMessage(error instanceof Error ? error.message : "暂时无法提交结算申请"); }
    finally { setBusy(""); }
  };
  const savePayoutProfile = async (event: FormEvent) => {
    event.preventDefault(); setBusy("payout");
    try { await interviewAppAdapter.savePartnerPayoutProfile(payoutDraft); setMessage("收款信息已加密保存。后续修改不会影响已提交的结算申请。"); setPayoutDraft(current => ({ ...current, accountName: "", accountIdentifier: "" })); await load(false); }
    catch (error) { setMessage(error instanceof Error ? error.message : "暂时无法保存收款信息"); }
    finally { setBusy(""); }
  };
  const copy = async () => {
    if (!partner?.shareUrl) return;
    await navigator.clipboard?.writeText(partner.shareUrl);
    setMessage("专属推广链接已复制。");
  };
  if (!partner) return <main className="app-page"><PageHeader eyebrow="PARTNER PROGRAM" title="合作伙伴计划" detail="分享面试稳，获得长期、透明、可核对的推广佣金。" /><div className="panel">{message || "正在读取合作伙伴信息…"}</div></main>;
  if (!partner.config.enabled) return <main className="app-page"><PageHeader eyebrow="PARTNER PROGRAM" title="合作伙伴计划" detail="分享面试稳，获得长期、透明、可核对的推广佣金。" /><EmptyState title="活动正在筹备" detail="开放后你可以主动加入并获得专属链接；这不会影响现有面试和积分权益。" /></main>;
  return <main className="app-page partner-program-page">
    <PageHeader eyebrow="PARTNER PROGRAM" title="合作伙伴计划" detail="一级推广，按净实收的 20% 计佣；每月可申请一次人工结算。" />
    {!partner.joined ? <section className="partner-intro panel"><div><span className="kicker">SHARE & EARN</span><h2>把真正有用的工具分享给更多求职者</h2><p>访客通过你的专属链接注册后，90 天内产生的合格订单会按退款后的净实收计算佣金。佣金经过 {partner.config.refundHoldDays} 天观察期后可申请结算。</p></div><dl><div><dt>佣金比例</dt><dd>{partner.config.commissionRateBps / 100}%</dd></div><div><dt>归因窗口</dt><dd>点击后 30 天内注册</dd></div><div><dt>订单周期</dt><dd>注册后 {partner.config.eligibleOrderDays} 天</dd></div><div><dt>最低结算</dt><dd>{money(partner.config.minimumPayoutCents)}</dd></div></dl><label className="partner-agreement"><input type="checkbox" checked={accepted} onChange={event => setAccepted(event.target.checked)} /><span>我已阅读并同意：仅进行真实推广，不进行自推、刷量或多级分销；佣金按退款后的净实收核算，结算时依法处理相关税务。</span></label><button className="button primary" disabled={!accepted || Boolean(busy)} onClick={() => void join()}>{busy === "join" ? "正在开通…" : "加入合作伙伴计划"}</button></section> : <>
      <section className="partner-share panel"><div><span className="kicker">YOUR PARTNER LINK</span><h2>你的专属推广链接</h2><p>同一个链接长期有效。请勿将链接用于自购、刷量或误导性推广。</p></div><div><code>{partner.shareUrl}</code><button className="button primary" onClick={() => void copy()}>复制链接</button></div></section>
      <section className="partner-metrics" aria-label="合作伙伴数据看板"><article><span>有效访客</span><strong>{partner.metrics?.validVisitors ?? 0}</strong></article><article><span>注册用户</span><strong>{partner.metrics?.registrations ?? 0}</strong></article><article><span>付费用户</span><strong>{partner.metrics?.payingUsers ?? 0}</strong></article><article><span>归因实收</span><strong>{money(partner.metrics?.attributedReceiptsCents)}</strong></article><article><span>待确认佣金</span><strong>{money(partner.balances?.pendingCents)}</strong></article><article><span>可提现佣金</span><strong>{money(partner.balances?.availableCents)}</strong></article><article><span>审核中</span><strong>{money(partner.balances?.reservedCents)}</strong></article><article><span>已结算</span><strong>{money(partner.balances?.settledCents)}</strong></article></section>
      {partner.config.payoutProfileEnabled ? <form className="partner-payout-profile panel" onSubmit={savePayoutProfile}><div><h2>人工结算收款信息</h2><p>仅用于管理员审核后人工打款。页面只显示脱敏信息，不会自动发起支付宝或微信转账。</p>{partner.payoutProfile ? <small>当前：{partner.payoutProfile.payoutMethod === "alipay" ? "支付宝" : "微信"} · {partner.payoutProfile.maskedAccountName} · {partner.payoutProfile.maskedAccountIdentifier}</small> : null}</div><label>收款方式<select value={payoutDraft.payoutMethod} onChange={event => setPayoutDraft(current => ({ ...current, payoutMethod: event.target.value as "alipay" | "wechat" }))}><option value="alipay">支付宝</option><option value="wechat">微信</option></select></label><label>实名姓名<input required minLength={2} maxLength={80} autoComplete="name" value={payoutDraft.accountName} onChange={event => setPayoutDraft(current => ({ ...current, accountName: event.target.value }))} /></label><label>收款账号<input required minLength={4} maxLength={160} autoComplete="off" value={payoutDraft.accountIdentifier} onChange={event => setPayoutDraft(current => ({ ...current, accountIdentifier: event.target.value }))} /></label><button className="button secondary" disabled={Boolean(busy)}>保存收款信息</button></form> : null}
      <section className="partner-settlement panel"><div><h2>月度结算</h2><p>可提现达到 {money(partner.config.minimumPayoutCents)} 后，每个自然月可以申请一次。退款或拒付会以冲正记录调整。</p></div><button className="button primary" disabled={Boolean(busy) || (partner.balances?.availableCents ?? 0) < partner.config.minimumPayoutCents} onClick={() => void payout()}>{busy === "payout" ? "正在提交…" : "申请结算"}</button>{partner.payouts?.length ? <div className="partner-payout-list">{partner.payouts.map(item => <p key={item.payoutRequestId}><span>{item.periodKey}</span><strong>{money(item.amountCents)}</strong><em>{item.status === "requested" ? "待审核" : item.status === "approved" ? "已批准" : item.status === "paid" ? "已结算" : "已驳回"}</em></p>)}</div> : <small>暂时没有结算记录。</small>}</section>
    </>}
    {message ? <p className="partner-message" role="status">{message}</p> : null}
  </main>;
}

function BillingRoutePage() { const { state, setState } = usePrototype(); return <BillingPage state={state} setState={setState} />; }
function GuideRoutePage() { const { state } = usePrototype(); return <GuidePage support={state.billing.support} />; }

function DevicesPage() {
  const { state } = usePrototype();
  return <main className="app-page"><PageHeader eyebrow="DESKTOP COMPANION" title="电脑伴随程序" detail="下载与你电脑匹配的伴随助手，并查看安装与系统授权说明。" /><DownloadCenter manifest={state.releaseManifest} /></main>;
}

function SettingsPage() {
  const [appearance, setAppearance] = useState<AppearancePreferences>(() => readAppearancePreferences());
  const updateAppearance = (patch: Partial<AppearancePreferences>) => {
    const next = { ...appearance, ...patch };
    setAppearance(next);
    applyAppearancePreferences(next);
    persistAppearancePreferences(next);
  };
  return <main className="app-page"><PageHeader eyebrow="SETTINGS" title="设置" detail="查看真实的数据行为和辅助功能。" /><div className="settings-list"><section className="panel"><h2>数据与隐私</h2><div className="setting-row"><span><strong>原始音频</strong><small>完成当前转写后不保留</small></span><b>默认不保存</b></div><div className="setting-row"><span><strong>面试记录</strong><small>请在对应复盘页查看、管理和删除记录。</small></span><Link to={`${routes.guide}#privacy-support`}>查看数据说明</Link></div></section><section className="panel"><h2>辅助功能</h2><label className="setting-row"><span><strong>减少动态效果</strong><small>减少波形与状态动画</small></span><input type="checkbox" /></label><label className="setting-row"><span><strong>回答字号</strong><small>只影响实时回答区域</small></span><select aria-label="回答字号" value={appearance.answerFontSize} onChange={event => updateAppearance({ answerFontSize: event.target.value as AppearancePreferences["answerFontSize"] })}><option value="normal">标准</option><option value="large">较大</option></select></label><label className="setting-row"><span><strong>页面主题</strong><small>明亮模式提高页面整体亮度，适合光线充足的环境</small></span><select aria-label="页面主题" value={appearance.theme} onChange={event => updateAppearance({ theme: event.target.value as AppearancePreferences["theme"] })}><option value="dark">深色</option><option value="bright">明亮</option></select></label></section></div></main>;
}

function RouteErrorPage() { return <main className="center-page"><EmptyState title="页面暂时无法加载" detail="没有输出任何敏感内容。请返回应用首页重试。" action={<Link className="button primary" to={routes.app}>返回首页</Link>} /></main>; }
function IntegrationModeErrorPage({ message, onRetry }: { readonly message: string; readonly onRetry: () => void }) { return <main className="center-page"><EmptyState title="后端页面状态暂时无法加载" detail={`${message}。页面会自动重试；服务恢复后将自动进入，无需重复登录。`} action={<button className="button primary" type="button" onClick={onRetry}>立即重试</button>} /></main>; }
function NotFoundPage() { return <main className="center-page"><EmptyState title="没有找到这个页面" detail="检查地址，或回到面试首页继续。" action={<Link className="button primary" to={routes.app}>返回首页</Link>} /></main>; }
function RouteLoadingPage() { return <main className="route-loading-page" role="status" aria-label="页面加载中" />; }

export function AppRoutes() {
  return <Routes><Route element={<PublicLayout />}><Route path={routes.landing} element={<LandingPage />} /><Route path={routes.login} element={<LoginPage />} /><Route path={routes.publicGuide} element={<GuideRoutePage />} /><Route path={routes.invite()} element={<ReferralLandingPage />} /><Route path={routes.terms} element={<LegalPage kind="terms" />} /><Route path={routes.privacy} element={<LegalPage kind="privacy" />} /></Route><Route element={<ProtectedRoute />}><Route path="/app" element={<AppLayout />}><Route index element={<HomePage />} /><Route path="written-exams" element={<WrittenExamHomePage />} /><Route path="interviews/new" element={<NewInterviewPage />} /><Route path="written-exams/new" element={<NewWrittenExamPage />} /><Route path="interviews/:id/prepare" element={<PreparationPage />} /><Route path="interviews/:id/review" element={<ReviewPage />} /><Route path="library" element={<LibraryPage />} /><Route path="billing" element={<BillingRoutePage />} /><Route path="partner-program" element={<PartnerProgramPage />} /><Route path="guide" element={<GuideRoutePage />} /><Route path="devices" element={<DevicesPage />} /><Route path="settings" element={<SettingsPage />} /></Route><Route path="/app/interviews/:id/live" element={<LivePage brand={<Logo />} accountMenu={<AccountMenu compact />} />} /></Route><Route path="/error" element={<RouteErrorPage />} /><Route path="*" element={<NotFoundPage />} /></Routes>;
}

function DocumentTitleManager() {
  const { pathname } = useLocation();
  useEffect(() => {
    if (pathname === routes.landing) {
      document.title = "AI面试助手｜实时语音识别、截图解题与个性化回答 - 面试稳";
    } else if (pathname === routes.publicGuide) {
      document.title = "面试稳AI助手使用手册｜安装、收音、截图回答与支付说明";
    } else if (pathname === routes.terms) {
      document.title = "用户协议 - 面试稳AI助手";
    } else if (pathname === routes.privacy) {
      document.title = "隐私政策 - 面试稳AI助手";
    } else if (pathname === routes.partnerProgram) {
      document.title = "合作伙伴计划 - 面试稳AI助手";
    } else {
      document.title = "面试稳AI助手";
    }
  }, [pathname]);
  return null;
}

export interface AppProps { readonly initialAuthenticated?: boolean; readonly initialState?: WebAppState; readonly publicStartup?: PublicStartupSnapshot | undefined }

export function App({ initialAuthenticated, initialState, publicStartup }: AppProps) {
  return <BrowserRouter><DocumentTitleManager /><PrototypeProvider initialAuthenticated={initialAuthenticated} initialState={initialState} publicStartup={publicStartup}><Suspense fallback={<RouteLoadingPage />}><AppRoutes /></Suspense></PrototypeProvider></BrowserRouter>;
}
