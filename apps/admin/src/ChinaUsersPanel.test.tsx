// @vitest-environment jsdom
import { act, cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ChinaUsersPanel } from "./ChinaUsersPanel";
import { App } from "./App";
import { adminApi, AdminAuthenticationError } from "./api";

type TestUser = { user_id: string; display_name: string; phone_hint: string; points_balance: number; account_status: string };
const users: [TestUser, TestUser] = [
  { user_id: "synthetic-user-a", display_name: "测试小林", phone_hint: "138****0001", points_balance: 200, account_status: "active" },
  { user_id: "synthetic-user-b", display_name: "测试小林", phone_hint: "138****0002", points_balance: 500, account_status: "active" },
];
const deferred = <T,>() => { let resolve!: (value: T) => void; const promise = new Promise<T>(done => { resolve = done; }); return { promise, resolve }; };
const open = (permissions = ["users.read", "billing.adjust", "users.suspend"]) => {
  const onAuthenticationExpired = vi.fn();
  const rendered = render(<ChinaUsersPanel permissions={permissions} onAuthenticationExpired={onAuthenticationExpired} />);
  return { ...rendered, onAuthenticationExpired };
};
const search = (value: string) => {
  fireEvent.change(screen.getByLabelText("用户名 / 用户 ID"), { target: { value } });
  fireEvent.submit(screen.getByRole("button", { name: "搜索" }).closest("form")!);
};
const choose = async (index = 0) => {
  await screen.findByText(users[0].user_id);
  fireEvent.click(screen.getAllByRole("button", { name: "调整积分" })[index]!);
};
const fill = (amount = "-20", reason = "合成测试调整积分") => {
  fireEvent.change(screen.getByLabelText("积分增减值"), { target: { value: amount } });
  fireEvent.change(screen.getByLabelText("操作原因"), { target: { value: reason } });
};

describe("China users search and controlled actions", () => {
  beforeEach(() => {
    vi.spyOn(adminApi, "listUsers").mockResolvedValue({ items: users });
    vi.spyOn(adminApi, "action").mockResolvedValue({ status: "success" });
    vi.spyOn(window, "confirm").mockReturnValue(true);
  });
  afterEach(() => { cleanup(); vi.restoreAllMocks(); vi.unstubAllGlobals(); sessionStorage.clear(); });

  it("shows registration time in Beijing across midnight, not the last login time", async () => {
    vi.mocked(adminApi.listUsers).mockResolvedValue({ items: [
      { ...users[0], created_at_ms: Date.parse("2025-03-01T15:59:59Z"), last_login_at_ms: Date.parse("2025-04-01T00:00:00Z") },
      { ...users[1], created_at_ms: String(Date.parse("2025-03-01T16:00:00Z")) },
    ] });
    open(); await screen.findByText(users[0].user_id);
    expect(screen.getByRole("columnheader", { name: "注册时间（北京时间）" })).toBeTruthy();
    const first = screen.getByText(users[0].user_id).closest("tr")!;
    const second = screen.getByText(users[1].user_id).closest("tr")!;
    expect(within(first).getByText("2025-03-01 23:59:59")).toBeTruthy();
    expect(within(second).getByText("2025-03-02 00:00:00")).toBeTruthy();
    await choose(1);
    expect(within(screen.getByRole("region", { name: "用户权益操作" })).getByText("注册时间（北京时间）：2025-03-02 00:00:00")).toBeTruthy();
    expect(screen.queryByText(/2025-04-01/)).toBeNull();
    expect(adminApi.listUsers).toHaveBeenCalledTimes(1);
    expect(adminApi.action).not.toHaveBeenCalled();
  });

  it.each([undefined, null, "", " ", "not-a-date", "2025-03-01T16:00:00Z", true, 0, -1, NaN, Infinity, 1.5, 8640000000000001])("safely displays unavailable registration time %s", async created_at_ms => {
    vi.mocked(adminApi.listUsers).mockResolvedValue({ items: [{ ...users[0], created_at_ms }] });
    open(); await screen.findByText(users[0].user_id);
    const cells = within(screen.getByText(users[0].user_id).closest("tr")!).getAllByRole("cell");
    expect(cells[2]?.textContent).toBe("—");
    await choose();
    expect(screen.getByText("注册时间（北京时间）：—")).toBeTruthy();
    expect(screen.queryByText(/Invalid Date/)).toBeNull();
    expect(adminApi.action).not.toHaveBeenCalled();
  });

  it("updates the registration time with search and clears the old selected identity", async () => {
    vi.mocked(adminApi.listUsers).mockResolvedValueOnce({ items: [{ ...users[0], created_at_ms: Date.parse("2025-01-01T00:00:00Z") }] });
    open(); await choose();
    expect(screen.getByText("注册时间（北京时间）：2025-01-01 08:00:00")).toBeTruthy();
    vi.mocked(adminApi.listUsers).mockResolvedValueOnce({ items: [{ ...users[1], created_at_ms: Date.parse("2025-02-01T00:00:00Z") }] });
    search("新用户");
    await screen.findByText("2025-02-01 08:00:00");
    expect(screen.queryByText(/2025-01-01/)).toBeNull();
    expect(screen.queryByRole("region", { name: "用户权益操作" })).toBeNull();
    expect(adminApi.listUsers).toHaveBeenCalledTimes(2);
  });

  it("queries all users only on submit and trims the search", async () => {
    open(); await screen.findByText(users[0].user_id);
    fireEvent.change(screen.getByLabelText("用户名 / 用户 ID"), { target: { value: "  小林  " } });
    expect(adminApi.listUsers).toHaveBeenCalledTimes(1);
    fireEvent.click(screen.getByRole("button", { name: "搜索" }));
    await waitFor(() => expect(adminApi.listUsers).toHaveBeenLastCalledWith("小林", 0));
    expect(adminApi.action).not.toHaveBeenCalled();
  });

  it("preserves search during pagination and resets to the first page", async () => {
    vi.mocked(adminApi.listUsers).mockResolvedValue({ items: Array.from({ length: 50 }, (_, i) => ({ ...users[0], user_id: `synthetic-${i}` })) });
    open(); await screen.findByText("synthetic-0"); search("小林");
    await screen.findByText("搜索“小林”");
    fireEvent.click(screen.getByRole("button", { name: "下一页" }));
    await waitFor(() => expect(adminApi.listUsers).toHaveBeenLastCalledWith("小林", 50));
    await screen.findByText("第 2 页");
    fireEvent.click(screen.getByRole("button", { name: "上一页" }));
    await screen.findByText("第 1 页");
    fireEvent.click(screen.getByRole("button", { name: "重置" }));
    await waitFor(() => expect(adminApi.listUsers).toHaveBeenLastCalledWith("", 0));
  });

  it("ignores late results from older searches", async () => {
    const old = deferred<{ items: TestUser[] }>();
    vi.mocked(adminApi.listUsers).mockImplementation(q => q === "旧" ? old.promise : Promise.resolve({ items: q === "新" ? [users[1]] : users }));
    open(); await screen.findByText(users[0].user_id); search("旧"); search("新");
    await screen.findByText(users[1].user_id);
    await act(async () => old.resolve({ items: [users[0]] }));
    expect(screen.queryByText(users[0].user_id)).toBeNull();
  });

  it("clears a prior selected user when a new query fails and offers retry", async () => {
    open(); await choose(); fill();
    vi.mocked(adminApi.listUsers).mockRejectedValueOnce(new Error("合成查询故障"));
    search("找不到的用户");
    await screen.findByText("合成查询故障");
    expect(screen.queryByRole("region", { name: "用户权益操作" })).toBeNull();
    expect(screen.queryByText(users[0].user_id)).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "重新查询" }));
    await screen.findByText(users[0].user_id);
    expect(adminApi.listUsers).toHaveBeenLastCalledWith("找不到的用户", 0);
  });

  it("shows no matches and removes stale action controls", async () => {
    open(); await choose();
    vi.mocked(adminApi.listUsers).mockResolvedValueOnce({ items: [] }); search("空结果");
    await screen.findByText(/没有找到匹配用户/);
    expect(screen.queryByLabelText("积分增减值")).toBeNull();
  });

  it.each([100, -20])("confirms the exact same-name user before adjusting %i points", async amount => {
    open(); await choose(1); fill(String(amount));
    const editor = screen.getByRole("region", { name: "用户权益操作" });
    expect(within(editor).getByText(`用户 ID：${users[1].user_id}`)).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "确认调整积分" }));
    await waitFor(() => expect(adminApi.action).toHaveBeenCalledTimes(1));
    expect(window.confirm).toHaveBeenCalledWith(expect.stringContaining(`用户 ID：${users[1].user_id}`));
    expect(window.confirm).toHaveBeenCalledWith(expect.stringContaining(users[1].phone_hint));
    expect(adminApi.action).toHaveBeenCalledWith(`/users/${users[1].user_id}/points`, expect.objectContaining({ points: amount, reason: "合成测试调整积分", confirmed: true, idempotencyKey: expect.any(String) }));
    await screen.findByText(/已完成：/);
    expect(screen.queryByLabelText("积分增减值")).toBeNull();
  });

  it("does not submit when confirmation is cancelled", async () => {
    vi.mocked(window.confirm).mockReturnValue(false); open(); await choose(); fill();
    fireEvent.click(screen.getByRole("button", { name: "确认调整积分" }));
    expect(adminApi.action).not.toHaveBeenCalled();
  });

  it.each(["", "0", "1.5", "1000001", "-1000001"])("rejects invalid amount %s", async amount => {
    open(); await choose(); fill(amount);
    fireEvent.submit(screen.getByRole("button", { name: "确认调整积分" }).closest("form")!);
    expect(adminApi.action).not.toHaveBeenCalled(); expect(window.confirm).not.toHaveBeenCalled();
    expect(screen.getByRole("alert").textContent).toContain("非零整数");
  });

  it("requires a meaningful reason", async () => {
    open(); await choose(); fill("10", "原因");
    fireEvent.click(screen.getByRole("button", { name: "确认调整积分" }));
    expect(adminApi.action).not.toHaveBeenCalled();
    expect(screen.getByRole("alert").textContent).toContain("操作原因");
  });

  it("allows finance to adjust without suspension permission and blocks read-only users", async () => {
    const ui = open(["users.read", "billing.adjust"]); await choose();
    expect(screen.queryByRole("button", { name: "封禁账号" })).toBeNull();
    ui.rerender(<ChinaUsersPanel permissions={["users.read"]} onAuthenticationExpired={vi.fn()} />);
    expect(screen.queryByRole("button", { name: "调整积分" })).toBeNull();
    expect(screen.queryByRole("button", { name: "确认调整积分" })).toBeNull();
  });

  it("locks duplicate submissions and reuses the command key after a transport failure", async () => {
    vi.mocked(adminApi.action).mockRejectedValueOnce(new Error("合成网络超时"));
    open(); await choose(); fill(); fireEvent.click(screen.getByRole("button", { name: "确认调整积分" }));
    await screen.findByText(/合成网络超时/);
    const key = vi.mocked(adminApi.action).mock.calls[0]![1].idempotencyKey;
    const pending = deferred<Record<string, unknown>>(); vi.mocked(adminApi.action).mockReturnValueOnce(pending.promise);
    const form = screen.getByRole("button", { name: "确认调整积分" }).closest("form")!;
    fireEvent.submit(form); fireEvent.submit(form);
    expect(adminApi.action).toHaveBeenCalledTimes(2);
    expect(vi.mocked(adminApi.action).mock.calls[1]![1].idempotencyKey).toBe(key);
    expect((screen.getByLabelText("用户名 / 用户 ID") as HTMLInputElement).disabled).toBe(true);
    await act(async () => pending.resolve({ status: "success" }));
    await screen.findByText(/已完成：/);
  });

  it("uses a new key for a changed adjustment after failure", async () => {
    vi.mocked(adminApi.action).mockRejectedValueOnce(new Error("合成错误"));
    open(); await choose(); fill(); fireEvent.click(screen.getByRole("button", { name: "确认调整积分" }));
    await screen.findByText(/合成错误/); fill("50");
    fireEvent.click(screen.getByRole("button", { name: "确认调整积分" }));
    await waitFor(() => expect(adminApi.action).toHaveBeenCalledTimes(2));
    const calls = vi.mocked(adminApi.action).mock.calls;
    expect(calls[1]![1].idempotencyKey).not.toBe(calls[0]![1].idempotencyKey);
  });

  it("keeps success distinct from a failed list refresh", async () => {
    open(); await choose(); fill(); vi.mocked(adminApi.listUsers).mockRejectedValueOnce(new Error("合成刷新失败"));
    fireEvent.click(screen.getByRole("button", { name: "确认调整积分" }));
    await screen.findByText("合成刷新失败"); expect(screen.getByText(/已完成：/)).toBeTruthy();
    expect(screen.queryByRole("button", { name: "确认调整积分" })).toBeNull();
    expect(adminApi.action).toHaveBeenCalledTimes(1);
  });

  it("preserves time and account operations with their own permissions", async () => {
    open(); await screen.findByText(users[0].user_id);
    fireEvent.click(screen.getAllByRole("button", { name: "增加时长" })[0]!);
    fireEvent.change(screen.getByLabelText("增加天数"), { target: { value: "7" } });
    fireEvent.change(screen.getByLabelText("操作原因"), { target: { value: "合成测试会员补偿" } });
    fireEvent.click(screen.getByRole("button", { name: "确认增加时长" }));
    await screen.findByText(/已完成：/);
    expect(adminApi.action).toHaveBeenCalledWith(`/users/${users[0].user_id}/time`, expect.objectContaining({ days: 7 }));
    await screen.findByText(users[0].user_id);
    fireEvent.click(screen.getAllByRole("button", { name: "封禁账号" })[0]!);
    fireEvent.change(screen.getByLabelText("操作原因"), { target: { value: "合成测试账号异常" } });
    fireEvent.click(screen.getByRole("button", { name: "确认封禁账号" }));
    await waitFor(() => expect(adminApi.action).toHaveBeenCalledWith(`/users/${users[0].user_id}/suspend`, expect.objectContaining({ confirmed: true })));
  });

  it("retains the active search on header refresh", async () => {
    const ui = open(); await choose(); search("小林"); await screen.findByText("搜索“小林”"); await choose();
    ui.rerender(<ChinaUsersPanel permissions={["users.read", "billing.adjust"]} refreshKey={1} onAuthenticationExpired={vi.fn()} />);
    await waitFor(() => expect(adminApi.listUsers).toHaveBeenCalledTimes(3));
    expect(adminApi.listUsers).toHaveBeenLastCalledWith("小林", 0);
    expect(screen.queryByLabelText("积分增减值")).toBeNull();
  });

  it("handles expired admin authentication", async () => {
    vi.mocked(adminApi.listUsers).mockRejectedValueOnce(new AdminAuthenticationError("登录已过期"));
    const ui = open(); await waitFor(() => expect(ui.onAuthenticationExpired).toHaveBeenCalledWith("登录已过期"));
  });

  it("connects the CN users navigation to the searchable panel", async () => {
    vi.spyOn(adminApi, "token").mockReturnValue("synthetic-token");
    vi.spyOn(adminApi, "session").mockResolvedValue({ role: "finance", permissions: ["users.read", "billing.adjust"] } as Awaited<ReturnType<typeof adminApi.session>>);
    const list = vi.spyOn(adminApi, "list");
    render(<App />);
    await screen.findByLabelText("用户名 / 用户 ID");
    await screen.findByText(users[0].user_id);
    expect(list).not.toHaveBeenCalled();
    search("小林"); await screen.findByText("搜索“小林”");
    fireEvent.click(screen.getByRole("button", { name: "刷新" }));
    await waitFor(() => expect(adminApi.listUsers).toHaveBeenCalledTimes(3));
    expect(adminApi.listUsers).toHaveBeenLastCalledWith("小林", 0);
  });
});

describe("CN users query contract", () => {
  afterEach(() => { vi.restoreAllMocks(); sessionStorage.clear(); });
  it("encodes names and special characters and retains the page offset", async () => {
    const fetch = vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify({ data: { items: users } }), { status: 200 }));
    await adminApi.listUsers("  小林 & user/+?  ", 50);
    const url = new URL(String(fetch.mock.calls[0]![0]), "http://localhost");
    expect(url.pathname).toBe("/api/v1/admin/users");
    expect(url.searchParams.get("search")).toBe("小林 & user/+?");
    expect(url.searchParams.get("limit")).toBe("50");
    expect(url.searchParams.get("offset")).toBe("50");
  });
});
