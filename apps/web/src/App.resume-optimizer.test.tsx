import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { App } from "./App";
import { optimizerCaps, optimizerState } from "./test/resume-optimizer-fixtures";
afterEach(() => vi.restoreAllMocks());
const setup = (path: string) => { vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => { const url = String(input); const data = url.endsWith("resume-optimizer/capabilities") ? optimizerCaps() : url.endsWith("resume-optimizer/jobs") ? { jobs: [] } : { enabled: false }; return new Response(JSON.stringify({ success: true, data }), { headers: { "Content-Type": "application/json" } }); }); window.history.pushState({}, "", path); return render(<App initialAuthenticated initialState={optimizerState()} />); };
describe("国服简历优化入口", () => {
  it("受保护工作台导航可进入中文优化页", async () => { setup("/app/resume-optimizer"); expect(await screen.findByRole("heading", { level: 1, name: "简历优化" })).toBeInTheDocument(); expect(screen.getAllByRole("link", { name: /简历优化/ }).every(link => link.getAttribute("href") === "/app/resume-optimizer")).toBe(true); expect(await screen.findByRole("button", { name: "开始优化" })).toBeInTheDocument(); expect(screen.queryByText(/本次 100 积分|可用积分：/)).not.toBeInTheDocument(); });
  it("资料简历页提供入口且仍保留上传按钮", async () => { setup("/app/library"); fireEvent.click(screen.getByRole("button", { name: /简历/ })); expect(screen.getByRole("link", { name: "简历优化 →" })).toHaveAttribute("href", "/app/resume-optimizer"); expect(screen.getByRole("button", { name: "＋ 添加简历" })).toBeInTheDocument(); fireEvent.click(screen.getByRole("link", { name: "简历优化 →" })); await waitFor(() => expect(screen.getByRole("heading", { level: 1, name: "简历优化" })).toBeInTheDocument()); });
});
