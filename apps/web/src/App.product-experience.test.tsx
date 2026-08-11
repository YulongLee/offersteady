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
    const grant = screen.getByText("200 点", { selector: ".free-grant strong" }).parentElement;
    expect(grant).toHaveTextContent("免费使用");
    expect(grant).not.toHaveTextContent("新用户");
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

  it("presents six clearly labelled scenario stories without inventing real endorsements", () => {
    open("/", false);
    const section = screen.getByRole("heading", { name: "典型使用反馈" }).closest("section");
    expect(section).not.toBeNull();
    expect(within(section!).getAllByRole("article")).toHaveLength(6);
    expect(within(section!).getAllByText("情景示例")).toHaveLength(6);
    expect(section).toHaveTextContent("情景示例 · 非真实用户评价");
    expect(section).toHaveTextContent("不代表真实人物、任职背书或录用结果");
    ["产品经理 · 社招面试", "后端工程师 · 技术面", "数据分析师 · 案例面", "应届毕业生 · 首次面试", "设计岗位 · 作品集面试", "跨行业求职者 · 转岗面试"].forEach(title => {
      expect(within(section!).getByRole("heading", { name: title })).toBeInTheDocument();
    });
    expect(within(section!).getAllByText("典型困扰")).toHaveLength(6);
    expect(within(section!).getAllByLabelText("使用能力")).toHaveLength(6);
    expect(section!.querySelectorAll(".scenario-capabilities span")).toHaveLength(18);
    expect(section!.querySelectorAll('.user-scenario-icon[aria-hidden="true"] svg')).toHaveLength(6);
    expect(section).not.toHaveTextContent(/腾讯|字节|Google|Microsoft|亚马逊|美团|五星|获得.*Offer|成功案例/);
    const styles = readFileSync("src/styles.css", "utf8");
    expect(styles).toMatch(/\.user-scenarios-grid\s*\{[^}]*grid-template-columns:\s*repeat\(2,/s);
    expect(styles).toMatch(/@media\s*\(max-width:\s*720px\)[\s\S]*\.user-scenarios-grid\s*\{\s*grid-template-columns:\s*1fr;/);
  });

  it("shows verifiable product facts and interactive FAQ answers from current billing state", () => {
    open("/", false, state => {
      state.billing = {
        ...state.billing,
        rates: { ...state.billing.rates, answerPoints: 7, screenshotAnswerPoints: 18, knowledgeIndexMinimumPoints: 25 },
        availablePaymentChannels: ["alipay"],
        ledger: state.billing.ledger.map(item => item.kind === "welcome_grant" ? { ...item, points: 300 } : item),
      };
    });
    const section = screen.getByRole("region", { name: "产品信息与常见问题" });
    const facts = within(section).getByLabelText("可核验产品信息");
    expect(facts.querySelectorAll("article")).toHaveLength(4);
    expect(facts).toHaveTextContent("3 种");
    expect(facts).toHaveTextContent("6 项");
    expect(facts).toHaveTextContent("2 种");
    expect(facts).toHaveTextContent("300 点");
    expect(facts).not.toHaveTextContent(/50000|95%|8000|100\+/);
    const faq = within(section).getByRole("heading", { name: "常见问题" }).closest<HTMLElement>("div.public-faq");
    expect(faq).not.toBeNull();
    expect(faq!.querySelectorAll("details")).toHaveLength(6);
    expect(within(faq!).getByText(/普通回答 7 点、截图回答 18 点，知识材料 25 点起/)).toBeInTheDocument();
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
    privacy.unmount();

    window.history.pushState({}, "", "/login");
    render(<App initialAuthenticated={false} initialState={structuredClone(syntheticState)} />);
    const consent = document.querySelector(".login-legal-copy");
    expect(consent).not.toBeNull();
    expect(within(consent as HTMLElement).getByRole("link", { name: "用户协议" })).toHaveAttribute("href", "/terms");
    expect(within(consent as HTMLElement).getByRole("link", { name: "隐私政策" })).toHaveAttribute("href", "/privacy");
  });

  it("creates an empty library for free and keeps new knowledge uploads non-ready until processing finishes", async () => {
    open("/app/library"); fireEvent.click(screen.getByRole("button", { name: /新建资料库/ })); let dialog = screen.getByRole("dialog"); fireEvent.change(within(dialog).getByLabelText("资料库名称"), { target: { value: "算法面试" } }); fireEvent.click(within(dialog).getByRole("button", { name: "确认创建" })); expect(await screen.findByText(/空资料库不扣点/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "添加第一份资料" })); dialog = screen.getByRole("dialog"); const file = new File(["synthetic"], "算法笔记.md", { type: "text/markdown" }); fireEvent.change(within(dialog).getByLabelText("选择资料文件"), { target: { files: [file] } }); expect(within(dialog).getByText(/当前 200 点 → 成功后 180 点/)).toBeInTheDocument(); expect(within(dialog).getByText(/3 Token/)).toBeInTheDocument(); fireEvent.click(within(dialog).getByRole("button", { name: "确认报价并建立索引" })); expect(await screen.findByText(/等待服务端建立索引/)).toBeInTheDocument(); expect(screen.getByText("算法笔记.md")).toBeInTheDocument(); expect(screen.getByText("建立索引中")).toBeInTheDocument();
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
    expect(within(dialog).getByText("使用 1 份会员额度")).toBeInTheDocument(); expect(within(dialog).getByText(/当前剩余 2 份/)).toBeInTheDocument(); fireEvent.click(within(dialog).getByRole("button", { name: "确认报价并建立索引" })); expect(await screen.findByText(/索引成功后才会正式结算/)).toBeInTheDocument();
  });

  it("blocks a points quote when the balance cannot cover the minimum", () => {
    open("/app/library", true, state => { state.billing = { ...state.billing, balance: 0, activePass: null }; }); fireEvent.click(screen.getByRole("button", { name: "＋ 添加资料" })); const dialog = screen.getByRole("dialog"); fireEvent.change(within(dialog).getByLabelText("选择资料文件"), { target: { files: [new File(["synthetic"], "余额不足.md", { type: "text/markdown" })] } }); expect(within(dialog).getByRole("link", { name: "积分不足，去充值" })).toBeInTheDocument();
  });

  it("separates verified downloads from the unsigned Windows preview", () => {
    open("/app/devices"); expect(screen.getByRole("button", { name: /macOS Apple Silicon/ })).toBeInTheDocument(); expect(screen.getByRole("button", { name: /macOS Intel/ })).toBeInTheDocument(); fireEvent.click(screen.getByRole("button", { name: /Windows 10\/11/ })); expect(screen.getByRole("button", { name: "完成签名后开放" })).toBeDisabled();
  });

  it("provides a protected searchable guide with support fallbacks", () => {
    open("/app/guide"); expect(screen.getByRole("heading", { name: "使用说明" })).toBeInTheDocument(); fireEvent.change(screen.getByPlaceholderText(/Windows、支付未到账/), { target: { value: "支付未到账" } }); expect(screen.getByRole("button", { name: /积分、会员与支付/ })).toBeInTheDocument(); fireEvent.click(screen.getByRole("button", { name: /积分、会员与支付/ })); expect(screen.getByText(/不要重复付款/)).toBeInTheDocument(); expect(screen.getByText("OneShowAILab")).toBeInTheDocument(); expect(screen.getByRole("link", { name: "发送邮件" })).toHaveAttribute("href", "mailto:contact@oneshowailab.com");
  });
});
