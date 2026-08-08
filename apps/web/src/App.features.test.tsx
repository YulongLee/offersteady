import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { App } from "./App";
import { syntheticState } from "./test-state";

vi.mock("./app-adapter", async () => {
  const { fixtureAdapter } = await import("./test-state");
  return { interviewAppAdapter: fixtureAdapter, runtimeConfig: { apiBaseUrl: "http://127.0.0.1:8000" } };
});

const open = (path: string) => {
  window.history.pushState({}, "", path);
  return render(<App initialAuthenticated initialState={structuredClone(syntheticState)} />);
};

describe("spec-driven interview features", () => {
  it("keeps prepared provenance visible without offering live material changes", () => {
    open("/app/interviews/demo/live");
    expect(screen.getByText(/回答依据/)).toBeInTheDocument();
    expect(screen.getByText(/高级前端工程师简历（合成） v3/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /调整资料|调整/ })).not.toBeInTheDocument();
  });

  it("creates an official checkout without collecting manual payment proof", async () => {
    const openSpy = vi.spyOn(window, "open").mockReturnValue(null);
    open("/app/billing");
    expect(screen.getByText("200 点", { selector: ".balance-card strong" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "3 天会员" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "1000 积分" })).toBeInTheDocument();
    fireEvent.click(screen.getAllByRole("button", { name: "购买" })[0]!);
    const dialog = screen.getByRole("dialog");
    expect(within(dialog).queryByLabelText("交易单号")).not.toBeInTheDocument(); expect(within(dialog).queryByLabelText("付款截图")).not.toBeInTheDocument();
    fireEvent.click(within(dialog).getByRole("button", { name: "支付宝支付" }));
    await waitFor(() => expect(within(dialog).getByRole("link", { name: "打开支付宝官方收银台" })).toBeInTheDocument());
    expect(openSpy).toHaveBeenCalledWith(expect.stringContaining("pay.mzfpay.com"), "_blank", "noopener,noreferrer");
    expect(within(dialog).getByText(/等待服务端验签通知/)).toBeInTheDocument();
    expect(within(dialog).queryByRole("button", { name: "模拟服务端验签通知" })).not.toBeInTheDocument();
    openSpy.mockRestore();
  });

  it("shows only enabled payment channels and disables checkout when none are ready", () => {
    const clonedSingle = structuredClone(syntheticState);
    const single = { ...clonedSingle, billing: { ...clonedSingle.billing, availablePaymentChannels: ["wechat"] as const } };
    window.history.pushState({}, "", "/app/billing");
    const rendered = render(<App initialAuthenticated initialState={single} />);
    fireEvent.click(screen.getAllByRole("button", { name: "购买" })[0]!);
    expect(within(screen.getByRole("dialog")).getByRole("button", { name: "微信支付" })).toBeInTheDocument();
    expect(within(screen.getByRole("dialog")).queryByRole("button", { name: "支付宝支付" })).not.toBeInTheDocument();
    rendered.unmount();

    const clonedDisabled = structuredClone(syntheticState);
    const disabled = { ...clonedDisabled, billing: { ...clonedDisabled.billing, availablePaymentChannels: [] as const } };
    render(<App initialAuthenticated initialState={disabled} />);
    expect(screen.getAllByRole("button", { name: "支付暂未开放" })[0]).toBeDisabled();
  });

  it("renders only two source-fixed roles and confirms unclear question content once", () => {
    open("/app/interviews/demo/live");
    expect(screen.getAllByText("面试官").length).toBeGreaterThan(1);
    expect(screen.getByText("我")).toBeInTheDocument();
    expect(screen.queryByText("角色待确认")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /设为面试官|设为我/ })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "确认问题" }));
    expect(screen.getAllByText("还有一个细节，具体怎么监控").length).toBeGreaterThan(0);
    expect(screen.queryByText("问题内容不清晰")).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "积分" })).toBeInTheDocument();
  });
});
