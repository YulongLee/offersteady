import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { App } from "./App";
import type { WebAppState } from "./domain";
import { mockSuccessfulMaterialUploadAdapter } from "./test-adapter-builders";
import { syntheticState } from "./test-state";

const open = (path: string, authenticated = true, mutate?: (state: WebAppState) => void) => { mockSuccessfulMaterialUploadAdapter(); const state = structuredClone(syntheticState); mutate?.(state); window.history.pushState({}, "", path); return render(<App initialAuthenticated={authenticated} initialState={state} />); };

describe("optimized product experience", () => {
  it("matches the filed website name and exposes the MIIT filing link", () => {
    open("/", false);
    expect(document.title).toBe("面试稳AI助手");
    expect(screen.getAllByText("面试稳AI助手").length).toBeGreaterThan(0);
    const filing = screen.getByRole("link", { name: "浙ICP备2026052190号-1" });
    expect(filing).toHaveAttribute("href", "https://beian.miit.gov.cn");
    const hero = screen.getByRole("heading", { name: /更从容地冲刺 Offer/ }).closest("section");
    expect(hero).not.toBeNull();
    expect(within(hero!).getByRole("link", { name: /免费使用/ })).toHaveAttribute("href", "/login");
    expect(within(hero!).getByRole("link", { name: "使用手册" })).toHaveAttribute("href", "/guide");
    expect(hero).not.toHaveTextContent("200 点");
    expect(hero).not.toHaveTextContent("看看怎么收费");
  });

  it("renders a commercial footer with public documents and configured contacts", () => {
    open("/", false, state => {
      state.billing = { ...state.billing, support: { ...state.billing.support, wechatId: "configured-wechat", email: "help@example.test", serviceHours: "每天 09:00–21:00" } };
    });
    const footer = document.querySelector<HTMLElement>(".public-footer");
    expect(footer).not.toBeNull();
    expect(within(footer!).getByText("configured-wechat")).toBeInTheDocument();
    expect(within(footer!).getByRole("link", { name: "help@example.test" })).toHaveAttribute("href", "mailto:help@example.test");
    expect(footer).toHaveTextContent("每天 09:00–21:00");
    expect(within(footer!).getByRole("link", { name: "使用手册" })).toHaveAttribute("href", "/guide");
    expect(within(footer!).getByRole("link", { name: "下载安装说明" })).toHaveAttribute("href", "/guide#desktop");
    expect(within(footer!).getByRole("link", { name: "用户协议" })).toHaveAttribute("href", "/terms");
    expect(within(footer!).getByRole("link", { name: "隐私政策" })).toHaveAttribute("href", "/privacy");
    expect(within(footer!).getByRole("link", { name: "浙ICP备2026052190号-1" })).toHaveAttribute("href", "https://beian.miit.gov.cn");
  });

  it("uses product-value messaging and exposes SMS login without pretending it is live", () => {
    open("/", false); expect(screen.getByRole("heading", { name: /更从容地冲刺 Offer/ })).toBeInTheDocument(); expect(screen.getByRole("heading", { name: "回答更贴合你的经历" })).toBeInTheDocument();
    const pricing = document.querySelector<HTMLElement>("#pricing-value");
    expect(pricing).not.toBeNull();
    expect(within(pricing!).getByText(/知识材料 20 点起/)).toBeInTheDocument();
    expect(within(pricing!).getByText(/15 天和 30 天各含 2 份/)).toBeInTheDocument(); expect(screen.queryByText(/进入产品原型/)).not.toBeInTheDocument(); expect(document.body).not.toHaveTextContent(/保证.*Offer|唯一标准答案|完全准确/);
    fireEvent.click(screen.getByText("查看使用与隐私说明")); expect(screen.getAllByText(/原始音频默认不保存/).length).toBeGreaterThan(0);
    fireEvent.click(screen.getAllByRole("link", { name: /免费使用/ })[0]!); expect(screen.getByRole("button", { name: /获取验证码/ })).toBeInTheDocument(); expect(screen.getByText(/手机号验证码/)).toBeInTheDocument();
  });

  it("opens the user guide from the public homepage without requiring login", () => {
    open("/", false);
    const hero = screen.getByRole("heading", { name: /更从容地冲刺 Offer/ }).closest("section");
    fireEvent.click(within(hero!).getByRole("link", { name: "使用手册" }));
    expect(screen.getByRole("heading", { name: "使用说明" })).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/Windows、支付未到账/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "免费使用" })).toHaveAttribute("href", "/login");
  });

  it("presents six truthful core capabilities in an accessible responsive grid", () => {
    open("/", false);
    const section = screen.getByRole("heading", { name: "面试稳AI助手核心功能" }).closest("section");
    expect(section).not.toBeNull();
    expect(within(section!).getAllByRole("article")).toHaveLength(6);
    ["实时面试辅助", "截图题快速回答", "个性化知识库", "简历与 JD 上下文", "面试记录与复盘", "跨设备伴随使用"].forEach(title => {
      expect(within(section!).getByRole("heading", { name: title })).toBeInTheDocument();
    });
    expect(section!.querySelectorAll('.core-capability-icon[aria-hidden="true"] svg')).toHaveLength(6);
    expect(section).not.toHaveTextContent(/99%|保证.*Offer|绝对隐蔽|面试猫/);
    const styles = readFileSync("src/styles.css", "utf8");
    expect(styles).toMatch(/\.core-capabilities-grid\s*\{[^}]*grid-template-columns:\s*repeat\(2,/s);
    expect(styles).toMatch(/@media\s*\(max-width:\s*720px\)[\s\S]*\.core-capabilities-grid\s*\{\s*grid-template-columns:\s*1fr;/);
  });

  it("presents common interview platforms without claiming universal or official integration", () => {
    open("/", false);
    const section = screen.getByRole("heading", { name: "适配常见远程面试与在线笔试平台" }).closest("section");
    expect(section).not.toBeNull();
    expect(within(section!).getAllByRole("listitem")).toHaveLength(10);
    ["Zoom", "Google Meet", "Microsoft Teams", "腾讯会议", "飞书", "钉钉", "企业微信", "力扣", "牛客", "Slack"].forEach(platform => {
      expect(within(section!).getByText(platform, { selector: "strong" })).toBeInTheDocument();
      expect(within(section!).getByRole("img", { name: `${platform} 品牌标识` })).toHaveAttribute("src", expect.stringMatching(/^https:\/\//));
    });
    expect(section!.querySelectorAll("[data-brand-source^='https://']")).toHaveLength(10);
    expect(section!.querySelectorAll(".platform-brand-wordmark")).toHaveLength(1);
    expect(section!.querySelectorAll(".platform-brand-lockup")).toHaveLength(9);
    expect(within(section!).getByText("Slack", { selector: ".brand-slack strong" })).toBeVisible();
    expect(section).not.toHaveTextContent(/\b(?:ZM|GM|MT|LC|SL)\b/);
    expect(section).not.toHaveTextContent("实际可用能力取决于电脑系统权限");
    expect(section).not.toHaveTextContent("不代表官方合作或直接集成");
    expect(section).not.toHaveTextContent("支持所有");
  });

  it("presents six commercial use cases without inventing user endorsements", () => {
    open("/", false);
    const section = screen.getByRole("heading", { name: "覆盖多种岗位与面试场景" }).closest("section");
    expect(section).not.toBeNull();
    expect(within(section!).getAllByRole("article")).toHaveLength(6);
    expect(section).toHaveTextContent("ROLE-BASED WORKFLOWS");
    expect(section).toHaveTextContent("帮助你更快组织真实经历与专业表达");
    expect(section).not.toHaveTextContent(/典型使用反馈|情景示例|非真实用户评价|用户评价|用户反馈/);
    ["产品经理 · 社招面试", "后端工程师 · 技术面", "数据分析师 · 案例面", "应届毕业生 · 首次面试", "设计岗位 · 作品集面试", "跨行业求职者 · 转岗面试"].forEach(title => {
      expect(within(section!).getByRole("heading", { name: title })).toBeInTheDocument();
    });
    expect(within(section!).getAllByText("典型困扰")).toHaveLength(6);
    expect(within(section!).getAllByLabelText("使用能力")).toHaveLength(6);
    expect(section!.querySelectorAll(".scenario-capabilities span")).toHaveLength(18);
    expect(section!.querySelectorAll('.user-scenario-icon[aria-hidden="true"] svg')).toHaveLength(6);
    expect(section).not.toHaveTextContent(/腾讯|字节|Google|Microsoft|亚马逊|美团|五星|获得.*Offer|成功案例|真实案例/);
    const styles = readFileSync("src/styles.css", "utf8");
    expect(styles).toMatch(/\.user-scenarios-grid\s*\{[^}]*grid-template-columns:\s*repeat\(2,/s);
    expect(styles).toMatch(/@media\s*\(max-width:\s*720px\)[\s\S]*\.user-scenarios-grid\s*\{\s*grid-template-columns:\s*1fr;/);
  });

  it("shows the requested commercial metrics without exposing the welcome-point amount", () => {
    open("/", false, state => {
      state.billing = {
        ...state.billing,
        rates: { ...state.billing.rates, answerPoints: 7, screenshotAnswerPoints: 18, knowledgeIndexMinimumPoints: 25 },
        availablePaymentChannels: ["alipay"],
        ledger: state.billing.ledger.map(item => item.kind === "welcome_grant" ? { ...item, points: 300 } : item),
      };
    });
    const section = screen.getByRole("region", { name: "产品信息与常见问题" });
    const facts = within(section).getByLabelText("产品数据");
    expect(facts.querySelectorAll("article")).toHaveLength(4);
    expect(facts).toHaveTextContent("10W+");
    expect(facts).toHaveTextContent("98%");
    expect(facts).toHaveTextContent("1W+");
    expect(facts).toHaveTextContent("100+");
    expect(facts).not.toHaveTextContent(/300 点|免费使用积分/);
    expect(document.querySelector("main")).not.toHaveTextContent(/200\s*点/);
    const faq = within(section).getByRole("heading", { name: "常见问题" }).closest<HTMLElement>("div.public-faq");
    expect(faq).not.toBeNull();
    expect(faq!.querySelectorAll("details")).toHaveLength(6);
    expect(within(faq!).getByText(/具体可用权益和后续使用方式/)).toBeInTheDocument();
    expect(within(faq!).getByText(/支付宝。实际可用方式/)).toBeInTheDocument();
    const firstDetails = faq!.querySelector("details")!;
    expect(firstDetails).toHaveAttribute("open");
    fireEvent.click(within(firstDetails).getByText("面试稳AI助手适合哪些岗位？"));
    expect(firstDetails).not.toHaveAttribute("open");
    const styles = readFileSync("src/styles.css", "utf8");
    expect(styles).toMatch(/\.product-facts-grid\s*\{[^}]*grid-template-columns:\s*repeat\(4,/s);
    expect(styles).toMatch(/@media\s*\(max-width:\s*720px\)[\s\S]*\.product-facts-grid\s*\{[^}]*grid-template-columns:\s*repeat\(2,/);
  });

  it("exposes directly accessible legal pages and links them from login", () => {
    const terms = open("/terms", false);
    expect(screen.getByRole("heading", { name: "用户协议", level: 1 })).toBeInTheDocument();
    expect(screen.getByText(/AI 生成内容仅供参考/)).toBeInTheDocument();
    expect(screen.getAllByRole("link", { name: "隐私政策" }).some(link => link.getAttribute("href") === "/privacy")).toBe(true);
    terms.unmount();

    window.history.pushState({}, "", "/privacy");
    const privacy = render(<App initialAuthenticated={false} initialState={structuredClone(syntheticState)} />);
    expect(screen.getByRole("heading", { name: "隐私政策", level: 1 })).toBeInTheDocument();
    expect(screen.getAllByText(/原始音频默认不保存/).length).toBeGreaterThan(0);
    expect(screen.getByText(/目前没有向你承诺统一的自动删除期限/)).toBeInTheDocument();
    expect(screen.queryByText(/正式商业化前/)).not.toBeInTheDocument();
    privacy.unmount();

    window.history.pushState({}, "", "/login");
    render(<App initialAuthenticated={false} initialState={structuredClone(syntheticState)} />);
    const consent = document.querySelector(".login-legal-copy");
    expect(consent).not.toBeNull();
    expect(within(consent as HTMLElement).getByRole("link", { name: "用户协议" })).toHaveAttribute("href", "/terms");
    expect(within(consent as HTMLElement).getByRole("link", { name: "隐私政策" })).toHaveAttribute("href", "/privacy");
    expect(screen.getByText("当前可免费使用")).toBeInTheDocument();
    expect(screen.queryByText(/新用户赠 200 点/)).not.toBeInTheDocument();
  });

  it("creates an empty library for free and keeps new knowledge uploads non-ready until processing finishes", async () => {
    open("/app/library"); fireEvent.click(screen.getByRole("button", { name: /新建资料库/ })); let dialog = screen.getByRole("dialog"); fireEvent.change(within(dialog).getByLabelText("资料库名称"), { target: { value: "算法面试" } }); fireEvent.click(within(dialog).getByRole("button", { name: "确认创建" })); expect(await screen.findByText(/空资料库不扣点/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "添加第一份资料" })); dialog = screen.getByRole("dialog"); const file = new File(["synthetic"], "算法笔记.md", { type: "text/markdown" }); fireEvent.change(within(dialog).getByLabelText("选择资料文件"), { target: { files: [file] } }); expect(await within(dialog).findByText(/当前 200 点 → 成功后 180 点/)).toBeInTheDocument(); expect(within(dialog).getByText(/3 Token/)).toBeInTheDocument(); fireEvent.click(within(dialog).getByRole("button", { name: "确认报价并建立索引" })); expect(await screen.findByText(/报价已由服务端确认并预留/)).toBeInTheDocument(); expect(screen.getByText("算法笔记.md")).toBeInTheDocument(); expect(screen.getByText("建立索引中")).toBeInTheDocument();
  });

  it("shows the revised catalog and complete consumption rules", () => {
    open("/app/billing"); expect(screen.getByRole("heading", { name: "1 天会员" }).parentElement).toHaveTextContent("¥29.90"); expect(screen.getByRole("heading", { name: "3 天会员" }).parentElement).toHaveTextContent("知识材料按点"); expect(screen.getByRole("heading", { name: "30 天会员" }).parentElement).toHaveTextContent("含 2 份知识材料"); expect(screen.getByRole("heading", { name: "1000 积分" }).parentElement).toHaveTextContent("¥99.90"); expect(screen.getByRole("heading", { name: "66666 积分" })).toBeInTheDocument(); expect(screen.getByText("点数消费说明")).toBeInTheDocument(); expect(screen.getByText(/每 5,000 Token 20 点/)).toBeInTheDocument();
  });

  it("shows when a queued long pass and its knowledge allowance will activate", () => {
    const now = Date.now();
    open("/app/billing", true, state => {
      state.billing = {
        ...state.billing,
        activePass: { id: "member-7", userId: state.account.id, productId: "pass-7", orderId: "active-order", startsAtMs: now, endsAtMs: now + 7 * 86_400_000, knowledgeAllowanceGranted: 0, knowledgeAllowanceUsed: 0, knowledgeAllowanceLocked: 0 },
        queuedPasses: [{ id: "member-15", userId: state.account.id, productId: "pass-15", orderId: "queued-order", startsAtMs: now + 7 * 86_400_000, endsAtMs: now + 22 * 86_400_000, knowledgeAllowanceGranted: 2, knowledgeAllowanceUsed: 0, knowledgeAllowanceLocked: 0 }],
      };
    });
    const queued = screen.getByRole("heading", { name: "待生效会员" }).closest("section");
    expect(queued).not.toBeNull();
    expect(within(queued!).getByText(/含 2 份知识材料额度/)).toBeInTheDocument();
  });

  it("shows a long-pass allowance quote before knowledge indexing starts", async () => {
    open("/app/library", true, state => { state.billing = { ...state.billing, activePass: { id: "member-15", userId: state.account.id, productId: "pass-15", orderId: "synthetic-order", startsAtMs: 1, endsAtMs: Date.now() + 86_400_000, knowledgeAllowanceGranted: 2, knowledgeAllowanceUsed: 0, knowledgeAllowanceLocked: 0 } }; });
    fireEvent.click(screen.getByRole("button", { name: "＋ 添加资料" })); const dialog = screen.getByRole("dialog"); fireEvent.change(within(dialog).getByLabelText("选择资料文件"), { target: { files: [new File(["synthetic"], "会员资料.md", { type: "text/markdown" })] } });
    expect(await within(dialog).findByText("使用 1 份会员额度")).toBeInTheDocument(); expect(within(dialog).getByText(/当前剩余 2 份/)).toBeInTheDocument(); fireEvent.click(within(dialog).getByRole("button", { name: "确认报价并建立索引" })); expect(await screen.findByText(/索引成功后自动结算/)).toBeInTheDocument();
  });

  it("blocks a points quote when the balance cannot cover the minimum", async () => {
    open("/app/library", true, state => { state.billing = { ...state.billing, balance: 0, activePass: null }; }); fireEvent.click(screen.getByRole("button", { name: "＋ 添加资料" })); const dialog = screen.getByRole("dialog"); fireEvent.change(within(dialog).getByLabelText("选择资料文件"), { target: { files: [new File(["synthetic"], "余额不足.md", { type: "text/markdown" })] } }); expect(await within(dialog).findByRole("link", { name: "积分不足，去充值" })).toBeInTheDocument();
  });

  it("never prices a PDF from its binary file size", async () => {
    open("/app/library");
    fireEvent.click(screen.getByRole("button", { name: "＋ 添加资料" }));
    const dialog = screen.getByRole("dialog");
    const binaryPdf = new File([new Uint8Array(4_000_000)], "带图片的资料.pdf", { type: "application/pdf" });
    fireEvent.change(within(dialog).getByLabelText("选择资料文件"), { target: { files: [binaryPdf] } });
    expect(within(dialog).getByText("正在解析并计算报价")).toBeInTheDocument();
    expect(within(dialog).queryByText(/1,000,000 Token/)).not.toBeInTheDocument();
    expect(await within(dialog).findByText(/3 Token/)).toBeInTheDocument();
    expect(within(dialog).getByText("服务端最终报价")).toBeInTheDocument();
  });

  it("separates downloadable releases from an unpublished Windows preview", () => {
    open("/app/devices"); expect(screen.getByRole("button", { name: /macOS Apple Silicon/ })).toBeInTheDocument(); expect(screen.getByRole("button", { name: /macOS Intel/ })).toBeInTheDocument(); fireEvent.click(screen.getByRole("button", { name: /Windows 10\/11/ })); expect(screen.getByRole("button", { name: "暂未开放下载" })).toBeDisabled();
  });

  it("never exposes internal desktop artifacts as downloads", () => {
    open("/app/devices", true, state => {
      const [first, ...rest] = state.releaseManifest.entries;
      if (!first) throw new Error("desktop release fixture is required");
      state.releaseManifest = { ...state.releaseManifest, entries: [{
          ...first,
          signingStatus: "local-development",
          distributionStatus: "internal",
          notarized: false,
          downloadUrl: "/api/v1/web/downloads/desktop/internal.zip",
          localPath: "/api/v1/web/downloads/desktop/internal.zip",
        }, ...rest] };
    });
    fireEvent.click(screen.getByRole("button", { name: /macOS Apple Silicon/ }));
    expect(screen.getByText("内部构建不可下载")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "暂未开放下载" })).toBeDisabled();
    expect(screen.queryByRole("link", { name: /下载安装包/ })).not.toBeInTheDocument();
  });

  it("allows operator-published companion releases without claiming verified signing", () => {
    open("/app/devices", true, state => {
      state.releaseManifest = {
        ...state.releaseManifest,
        entries: state.releaseManifest.entries.map(entry => ({
          ...entry,
          signingStatus: "local-development",
          distributionStatus: "published",
          notarized: false,
          downloadUrl: `/api/v1/web/downloads/desktop/${entry.id}`,
        })),
      };
    });
    expect(screen.getAllByText("✓ 正式版可下载")).toHaveLength(3);
    expect(screen.getByRole("link", { name: "下载安装包" })).toHaveAttribute("href", expect.stringContaining("/api/v1/web/downloads/desktop/"));
    expect(screen.queryByText("✓ 已验证")).not.toBeInTheDocument();
  });

  it("provides a protected searchable guide with support fallbacks", () => {
    open("/app/guide"); expect(screen.getByRole("heading", { name: "使用说明" })).toBeInTheDocument(); fireEvent.change(screen.getByPlaceholderText(/Windows、支付未到账/), { target: { value: "支付未到账" } }); expect(screen.getByRole("button", { name: /积分、会员与支付/ })).toBeInTheDocument(); fireEvent.click(screen.getByRole("button", { name: /积分、会员与支付/ })); expect(screen.getByText(/不要重复付款/)).toBeInTheDocument(); expect(screen.getByText("OneShowAILab")).toBeInTheDocument(); expect(screen.getByRole("link", { name: "发送邮件" })).toHaveAttribute("href", "mailto:contact@oneshowailab.com");
  });
});
