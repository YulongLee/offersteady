// @vitest-environment jsdom
import { act, cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { GlobalMembersPanel } from "./App";
import { adminApi } from "./api";

const user = (id: string) => ({ user_id: id, email: `${id}@example.test`, display_name: "Same Name", created_at_ms: Date.parse("2026-09-28T16:30:00Z") });
const detail = (id: string) => ({ identity: user(id), state: { usage: { copilotUnlimited: true }, features: {} }, entitlements: [
  { id: `ent-${id}`, status: "active", sourceKind: "admin", offerCode: "global-pro-weekly" },
], orders: [], subscriptions: [] });
const page = (ids = ["one", "two"]) => ({ items: ids.map(user), limit: 30, offset: 0 });
const deferred = <T,>() => { let resolve!: (value: T) => void; let reject!: (error: Error) => void; const promise = new Promise<T>((a, b) => { resolve = a; reject = b; }); return { resolve, reject, promise }; };
beforeEach(() => {
  vi.spyOn(adminApi, "globalMembers").mockResolvedValue(page());
  vi.spyOn(adminApi, "globalMember").mockImplementation(async id => detail(id));
  vi.spyOn(adminApi, "grantGlobalMemberPlan").mockResolvedValue({});
  vi.spyOn(adminApi, "revokeGlobalMemberEntitlement").mockResolvedValue({});
  vi.spyOn(window, "confirm").mockReturnValue(true);
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); });
async function open(id = "one") {
  render(<GlobalMembersPanel />);
  fireEvent.click(await screen.findByRole("button", { name: new RegExp(`${id}@example.test`) }));
  await screen.findByText("人工会员管理");
}
function reason() { fireEvent.change(screen.getByLabelText("会员操作原因"), { target: { value: "Synthetic support credit" } }); }

it("pages with the committed query and clears selection", async () => {
  vi.mocked(adminApi.globalMembers).mockResolvedValue(page(Array.from({ length: 30 }, (_, i) => `user-${i}`)));
  render(<GlobalMembersPanel />);
  await screen.findByRole("button", { name: /user-0@example.test/ });
  fireEvent.change(screen.getByLabelText("搜索国际版用户"), { target: { value: "Same" } });
  fireEvent.click(screen.getByRole("button", { name: "搜索用户" }));
  fireEvent.click(await screen.findByRole("button", { name: /user-0@example.test/ }));
  await screen.findByText("人工会员管理");
  fireEvent.click(screen.getByRole("button", { name: "下一页" }));
  await waitFor(() => expect(adminApi.globalMembers).toHaveBeenLastCalledWith("Same", 30));
  expect(screen.queryByText("人工会员管理")).toBeNull();
  expect(screen.getByText("第 2 页")).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "上一页" }));
  await waitFor(() => expect(adminApi.globalMembers).toHaveBeenLastCalledWith("Same", 0));
});

it("ignores an older search response", async () => {
  const old = deferred<ReturnType<typeof page>>();
  vi.mocked(adminApi.globalMembers).mockReturnValueOnce(old.promise).mockResolvedValueOnce(page(["new"]));
  render(<GlobalMembersPanel />);
  fireEvent.change(screen.getByLabelText("搜索国际版用户"), { target: { value: "new" } });
  fireEvent.click(screen.getByRole("button", { name: "搜索用户" }));
  await screen.findByRole("button", { name: /new@example.test/ });
  await act(async () => old.resolve(page(["old"])));
  expect(screen.queryByRole("button", { name: /old@example.test/ })).toBeNull();
});

it("ignores older member details and targets the selected same-name user", async () => {
  const old = deferred<ReturnType<typeof detail>>();
  vi.mocked(adminApi.globalMember).mockImplementation(id => id === "one" ? old.promise : Promise.resolve(detail(id)));
  render(<GlobalMembersPanel />);
  fireEvent.click(await screen.findByRole("button", { name: /one@example.test/ }));
  fireEvent.click(screen.getByRole("button", { name: /two@example.test/ }));
  await screen.findByText("人工会员管理");
  await act(async () => old.resolve(detail("one")));
  reason(); fireEvent.click(screen.getByRole("button", { name: "确认赠送" }));
  await waitFor(() => expect(adminApi.grantGlobalMemberPlan).toHaveBeenCalledTimes(1));
  expect(vi.mocked(adminApi.grantGlobalMemberPlan).mock.calls[0]?.[0]).toBe("two");
  expect(window.confirm).toHaveBeenCalledWith(expect.stringContaining("用户 ID：two"));
});

it("shows the same UTC registration time in results and details", async () => {
  await open();
  expect(screen.getAllByText(/注册时间：2026-09-28 16:30:00 UTC/).length).toBe(3);
});

it.each([null, "bad", true, -1, 0, "", 1.5, 9e15])("handles an invalid registration timestamp %s", async value => {
  vi.mocked(adminApi.globalMembers).mockResolvedValue({ ...page(), items: [{ ...user("one"), created_at_ms: value }] });
  vi.mocked(adminApi.globalMember).mockResolvedValue({ ...detail("one"), identity: { ...user("one"), created_at_ms: value } });
  await open();
  expect(screen.getAllByText("注册时间：—")).toHaveLength(2);
});

it("deduplicates pending grants and reuses the key after uncertain failure", async () => {
  const pending = deferred<Record<string, unknown>>();
  vi.mocked(adminApi.grantGlobalMemberPlan).mockReturnValueOnce(pending.promise).mockResolvedValueOnce({});
  await open(); reason();
  const button = screen.getByRole("button", { name: "确认赠送" });
  fireEvent.click(button); fireEvent.click(button);
  expect(adminApi.grantGlobalMemberPlan).toHaveBeenCalledTimes(1);
  const first = vi.mocked(adminApi.grantGlobalMemberPlan).mock.calls[0];
  await act(async () => pending.reject(new Error("Synthetic timeout")));
  fireEvent.click(screen.getByRole("button", { name: "确认赠送" }));
  await waitFor(() => expect(adminApi.grantGlobalMemberPlan).toHaveBeenCalledTimes(2));
  expect(vi.mocked(adminApi.grantGlobalMemberPlan).mock.calls[1]).toEqual(first);
});

it("a changed operation gets a different key", async () => {
  vi.mocked(adminApi.grantGlobalMemberPlan).mockRejectedValue(new Error("Synthetic failure"));
  await open(); reason(); fireEvent.click(screen.getByRole("button", { name: "确认赠送" }));
  await screen.findByText(/Synthetic failure/);
  fireEvent.change(screen.getByLabelText("会员操作原因"), { target: { value: "Different support reason" } });
  fireEvent.click(screen.getByRole("button", { name: "确认赠送" }));
  await waitFor(() => expect(adminApi.grantGlobalMemberPlan).toHaveBeenCalledTimes(2));
  expect(vi.mocked(adminApi.grantGlobalMemberPlan).mock.calls[1]?.[3]).not.toBe(vi.mocked(adminApi.grantGlobalMemberPlan).mock.calls[0]?.[3]);
});

it("does not repeat a successful grant when detail refresh fails", async () => {
  vi.mocked(adminApi.globalMember).mockResolvedValueOnce(detail("one")).mockRejectedValueOnce(new Error("Synthetic refresh failure")).mockResolvedValueOnce(detail("one"));
  await open(); reason(); fireEvent.click(screen.getByRole("button", { name: "确认赠送" }));
  await screen.findByText(/权益操作已成功，但详情刷新失败/);
  expect(screen.queryByRole("button", { name: "确认赠送" })).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: "刷新用户详情" }));
  await screen.findByText("人工会员管理");
  expect(adminApi.grantGlobalMemberPlan).toHaveBeenCalledTimes(1);
});

it("keeps revocation retries idempotent and leaves free grants protected", async () => {
  vi.mocked(adminApi.revokeGlobalMemberEntitlement).mockRejectedValueOnce(new Error("Synthetic timeout")).mockResolvedValueOnce({});
  vi.mocked(adminApi.globalMember).mockResolvedValue({ ...detail("one"), entitlements: [...detail("one").entitlements, { id: "free", sourceKind: "free_grant", status: "active", offerCode: "global-free" }] });
  await open(); reason();
  expect(screen.getAllByRole("button", { name: "撤销此权益" })).toHaveLength(1);
  fireEvent.click(screen.getByRole("button", { name: "撤销此权益" }));
  await screen.findByText(/Synthetic timeout/);
  fireEvent.click(screen.getByRole("button", { name: "撤销此权益" }));
  await waitFor(() => expect(adminApi.revokeGlobalMemberEntitlement).toHaveBeenCalledTimes(2));
  const calls = vi.mocked(adminApi.revokeGlobalMemberEntitlement).mock.calls;
  expect(calls[0]).toEqual(calls[1]);
  expect(calls[0]?.slice(0, 2)).toEqual(["one", "ent-one"]);
});

it("requires a reason and respects cancelled confirmation", async () => {
  await open(); fireEvent.click(screen.getByRole("button", { name: "确认赠送" }));
  expect(adminApi.grantGlobalMemberPlan).not.toHaveBeenCalled();
  reason(); vi.mocked(window.confirm).mockReturnValue(false);
  fireEvent.click(screen.getByRole("button", { name: "确认赠送" }));
  expect(adminApi.grantGlobalMemberPlan).not.toHaveBeenCalled();
});

it("failed searches cannot leave old results actionable", async () => {
  await open();
  vi.mocked(adminApi.globalMembers).mockRejectedValueOnce(new Error("Synthetic unavailable"));
  fireEvent.click(screen.getByRole("button", { name: "搜索用户" }));
  await screen.findByText("Synthetic unavailable");
  expect(screen.queryByText("人工会员管理")).toBeNull();
  expect(within(screen.getByRole("region", { name: "用户搜索结果" })).queryByRole("button", { name: /one@example.test/ })).toBeNull();
});
