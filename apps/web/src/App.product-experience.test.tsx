import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { App } from "./App";
import type { WebAppState } from "./domain";
import { mockSuccessfulMaterialUploadAdapter } from "./test-adapter-builders";
import { syntheticState } from "./test-state";

const open = (path: string, authenticated = true, mutate?: (state: WebAppState) => void) => { mockSuccessfulMaterialUploadAdapter(); const state = structuredClone(syntheticState); mutate?.(state); window.history.pushState({}, "", path); return render(<App initialAuthenticated={authenticated} initialState={state} />); };

describe("optimized product experience", () => {
  it("uses product-value messaging and exposes SMS login without pretending it is live", () => {
    open("/", false); expect(screen.getByRole("heading", { name: /更从容地冲刺 Offer/ })).toBeInTheDocument(); expect(screen.getByRole("heading", { name: "回答更贴合你的经历" })).toBeInTheDocument(); expect(screen.getByText(/知识材料 20 点起/)).toBeInTheDocument(); expect(screen.getByText(/15 天和 30 天各含 2 份/)).toBeInTheDocument(); expect(screen.queryByText(/进入产品原型/)).not.toBeInTheDocument(); expect(document.body).not.toHaveTextContent(/保证.*Offer|唯一标准答案|完全准确/);
    fireEvent.click(screen.getByText("查看使用与隐私说明")); expect(screen.getAllByText(/原始音频默认不保存/).length).toBeGreaterThan(0);
    fireEvent.click(screen.getByRole("link", { name: /免费使用/ })); expect(screen.getByRole("button", { name: /获取验证码/ })).toBeInTheDocument(); expect(screen.getByText(/手机号验证码/)).toBeInTheDocument();
  });

  it("creates an empty library for free and keeps new knowledge uploads non-ready until processing finishes", async () => {
    open("/app/library"); fireEvent.click(screen.getByRole("button", { name: /新建资料库/ })); let dialog = screen.getByRole("dialog"); fireEvent.change(within(dialog).getByLabelText("资料库名称"), { target: { value: "算法面试" } }); fireEvent.click(within(dialog).getByRole("button", { name: "确认创建" })); expect(await screen.findByText(/空资料库不扣点/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "添加第一份资料" })); dialog = screen.getByRole("dialog"); const file = new File(["synthetic"], "算法笔记.md", { type: "text/markdown" }); fireEvent.change(within(dialog).getByLabelText("选择资料文件"), { target: { files: [file] } }); expect(within(dialog).getByText(/当前 200 点 → 成功后 180 点/)).toBeInTheDocument(); expect(within(dialog).getByText(/3 Token/)).toBeInTheDocument(); fireEvent.click(within(dialog).getByRole("button", { name: "确认报价并建立索引" })); expect(await screen.findByText(/等待服务端建立索引/)).toBeInTheDocument(); expect(screen.getByText("算法笔记.md")).toBeInTheDocument(); expect(screen.getByText("建立索引中")).toBeInTheDocument();
  });

  it("shows the revised catalog and complete consumption rules", () => {
    open("/app/billing"); expect(screen.getByRole("heading", { name: "3 天会员" }).parentElement).toHaveTextContent("¥69.90"); expect(screen.getByRole("heading", { name: "3 天会员" }).parentElement).toHaveTextContent("知识材料按点"); expect(screen.getByRole("heading", { name: "30 天会员" }).parentElement).toHaveTextContent("含 2 份知识材料"); expect(screen.getByRole("heading", { name: "300 点" }).parentElement).toHaveTextContent("¥39.90"); expect(screen.getByText("点数消费说明")).toBeInTheDocument(); expect(screen.getByText(/每 5,000 Token 20 点/)).toBeInTheDocument();
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
    open("/app/guide"); expect(screen.getByRole("heading", { name: "使用说明" })).toBeInTheDocument(); fireEvent.change(screen.getByPlaceholderText(/Windows、支付未到账/), { target: { value: "支付未到账" } }); expect(screen.getByRole("button", { name: /积分、会员与支付/ })).toBeInTheDocument(); fireEvent.click(screen.getByRole("button", { name: /积分、会员与支付/ })); expect(screen.getByText(/不要重复付款/)).toBeInTheDocument(); expect(screen.getByAltText(/客服群二维码/)).toBeInTheDocument();
  });
});
