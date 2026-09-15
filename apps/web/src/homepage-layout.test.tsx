import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { App } from "./App";
import { interviewAppAdapter } from "./app-adapter";
import { fixtureAdapter, syntheticState } from "./test-state";
import { downloadableRelease } from "./platform";
import { HomepagePricing } from "./HomepagePricing";

function open(path = "/", state = structuredClone(syntheticState)) {
  window.history.replaceState({}, "", path);
  return render(<App initialAuthenticated={false} initialState={state} />);
}

describe("production-based domestic homepage layout", () => {
  beforeEach(() => {
    vi.spyOn(interviewAppAdapter, "getPartnerProgramConfig")
      .mockImplementation(signal => fixtureAdapter.getPartnerProgramConfig(signal));
  });
  afterEach(() => vi.restoreAllMocks());

  it("scopes layout to the homepage, preserving product identity and primary action", () => {
    const { container } = open();
    expect(container.querySelector(".cn-home-shell .cn-commercial-home")).not.toBeNull();
    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("AI 面试助手，让你的经历更好表达。");
    const hero = container.querySelector(".landing-hero") as HTMLElement;
    expect(within(hero).getByRole("link", { name: /免费使用/ })).toHaveAttribute("href", "/login");
    expect(hero).toHaveTextContent("面向求职者的AI面试助手");
    expect(within(hero).getAllByRole("region", { name: "下载电脑助手" })).toHaveLength(1);
  });

  it("does not apply the homepage layout to the existing login screen", () => {
    const { container } = open("/login");
    expect(container.querySelector(".public-shell")).not.toBeNull();
    expect(container.querySelector(".cn-home-shell")).toBeNull();
  });

  it("keeps the partner entry, public navigation and both video elements", () => {
    const { container } = open();
    expect(container.querySelector(".partner-nav-entry")).toHaveAttribute("href", "/app/partner-program");
    const navigation = screen.getByRole("navigation", { name: "公开导航" });
    expect(within(navigation).getByRole("link", { name: "下载" })).toHaveAttribute("href", "/download");
    const videos = Array.from(container.querySelectorAll("video"));
    expect(videos).toHaveLength(2);
    for (const video of videos) {
      expect(video.controls).toBe(true);
      expect(video.autoplay).toBe(false);
      expect(video.preload).toBe("none");
    }
  });

  it("shows all catalogue prices and changes selected membership without an order", () => {
    open();
    const plans = screen.getByLabelText("按天会员套餐");
    const visiblePasses = syntheticState.billing.catalog.filter(product => product.kind === "time_pass" && product.published);
    expect(within(plans).getAllByRole("button")).toHaveLength(visiblePasses.length);
    for (const pass of visiblePasses) {
      const price = "¥" + (pass.priceCents / 100).toFixed(2);
      const button = within(plans).getByRole("button", { name: `${pass.durationDays} 天 ${price}` });
      fireEvent.click(button);
      expect(button).toHaveAttribute("aria-pressed", "true");
      expect(within(plans).getAllByRole("button", { pressed: true })).toHaveLength(1);
      expect(screen.getByRole("region", { name: "当前会员权益" })).toHaveTextContent(price);
      expect(screen.getByRole("region", { name: "当前会员权益" })).toHaveTextContent(`有效期 ${pass.durationDays} 天`);
    }
    expect(screen.getByRole("link", { name: /查看完整套餐与权益/ })).toHaveAttribute("href", "/pricing");
  });

  it("does not fabricate memberships when the published catalogue is empty", () => {
    const state = structuredClone(syntheticState);
    open("/", { ...state, billing: { ...state.billing, catalog: [] } });
    expect(screen.queryByLabelText("按天会员套餐")).toBeNull();
    expect(screen.getByText(/当前暂无可展示的会员套餐/)).toBeInTheDocument();
  });

  it("retains manifest-driven Mac links and Escape-close focus behavior", () => {
    const { container } = open();
    const menu = container.querySelector(".cn-mac-download") as HTMLDetailsElement;
    const summary = menu.querySelector("summary") as HTMLElement;
    const expected = syntheticState.releaseManifest.entries.filter(entry => entry.platform === "macos" && downloadableRelease(entry));
    const links = Array.from(menu.querySelectorAll("a"));
    expect(links.map(link => link.getAttribute("href"))).toEqual(expected.map(entry => entry.downloadUrl));
    for (const link of links) expect(link.hasAttribute("download")).toBe(true);
    menu.open = true;
    fireEvent.keyDown(menu, { key: "Escape" });
    expect(menu.open).toBe(false);
    expect(summary).toHaveFocus();
  });

  it("retains the Windows manifest link and does not download during rendering", () => {
    const state = structuredClone(syntheticState);
    const entries = state.releaseManifest.entries.map(entry => entry.platform === "windows"
      ? { ...entry, signingStatus: "verified" as const, downloadUrl: "/downloads/synthetic-layout-windows.exe" } : entry);
    open("/", { ...state, releaseManifest: { ...state.releaseManifest, entries } });
    const download = within(screen.getByRole("region", { name: "下载电脑助手" }));
    expect(download.getByRole("link", { name: "Windows" })).toHaveAttribute("href", "/downloads/synthetic-layout-windows.exe");
  });

  it("keeps static homepage metadata and routes its price action to public pricing", () => {
    const html = readFileSync(resolve(process.cwd(), "index.html"), "utf8");
    const parsed = new DOMParser().parseFromString(html, "text/html");
    expect(parsed.querySelectorAll("h1")).toHaveLength(1);
    expect(parsed.querySelector('link[rel="canonical"]')?.getAttribute("href")).toBe("https://mianshiwen.cn/");
    expect(parsed.querySelector("#pricing a")?.getAttribute("href")).toBe("/pricing");
    expect(parsed.querySelector("#pricing")?.textContent).toContain("无需登录");
    expect(html.indexOf('id="product-tour"')).toBeLessThan(html.indexOf('id="pricing"'));
  });

  it("switches real product captures and their enlarged image links together", () => {
    open();
    const preview = screen.getByRole("figure", { name: "产品界面演示" });
    expect(within(preview).getByRole("button", { name: "项目追问" })).toHaveAttribute("aria-pressed", "true");
    expect(within(preview).getByRole("img")).toHaveAttribute("src", "/media/homepage/project-demo.png");
    fireEvent.click(within(preview).getByRole("button", { name: "截图问题" }));
    expect(within(preview).getByRole("button", { name: "截图问题" })).toHaveAttribute("aria-pressed", "true");
    expect(within(preview).getByRole("img")).toHaveAttribute("src", "/media/homepage/screenshot-demo.png");
    expect(within(preview).getByRole("link", { name: "查看截图问题演示大图" })).toHaveAttribute("href", "/media/homepage/screenshot-demo.png");
    expect(preview).toHaveTextContent("产品界面 · 合成示例");
    fireEvent.click(within(preview).getByRole("button", { name: "项目追问" }));
    expect(within(preview).getByRole("img")).toHaveAttribute("src", "/media/homepage/project-demo.png");
  });

  it("puts the existing tutorial before buying and keeps the overview user-initiated", () => {
    const { container } = open();
    const tour = container.querySelector("#product-tour")!;
    const pricing = container.querySelector("#pricing-value")!;
    expect(tour.compareDocumentPosition(pricing) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    const overview = container.querySelector(".cn-film-details") as HTMLDetailsElement;
    expect(overview.open).toBe(false);
    expect(tour.querySelector('video[aria-label="面试稳工具使用教程"]')).not.toBeNull();
  });

  it("explains memberships and material overage without creating payment promises", () => {
    const { container } = open();
    const pricing = container.querySelector("#pricing-value") as HTMLElement;
    expect(pricing).toHaveTextContent("知识材料按套餐额度或积分计费");
    expect(pricing).toHaveTextContent("仍受并发及防滥用限制");
    expect(pricing).toHaveTextContent("支付确认后");
    expect(within(pricing).getByRole("link", { name: /订单与退款咨询/ })).toHaveAttribute("href", "/contact");
    expect(within(pricing).queryByRole("button", { name: /购买|支付/ })).toBeNull();
  });

  it("uses current rates and excludes unpublished or invalid pass prices", () => {
    const state = structuredClone(syntheticState);
    const pass = state.billing.catalog.find(item => item.kind === "time_pass")!;
    state.billing = { ...state.billing, rates: { ...state.billing.rates, answerPoints: 9, screenshotAnswerPoints: 27 }, catalog: [
      { ...pass, id: "unpublished", displayName: "不应展示未发布", published: false },
      { ...pass, id: "bad-price", displayName: "不应展示无效价格", priceCents: NaN },
      { ...pass, id: "updated", displayName: "测试配置套餐", priceCents: 4567, durationDays: 7 },
    ] };
    open("/", state);
    expect(screen.getByLabelText("积分与会员区别")).toHaveTextContent("回答建议9 点起");
    expect(screen.getByLabelText("积分与会员区别")).toHaveTextContent("截图回答27 点起");
    const plans = screen.getByLabelText("按天会员套餐");
    expect(plans).toHaveTextContent("¥45.67");
    expect(screen.getByRole("region", { name: "当前会员权益" })).toHaveTextContent("有效期 7 天");
    expect(plans).not.toHaveTextContent("不应展示");
  });

  it("updates knowledge allowance with duration and falls back when a selected plan disappears", () => {
    const billing = structuredClone(syntheticState.billing);
    const source = billing.catalog.find(item => item.kind === "time_pass")!;
    const short = { ...source, id: "short", displayName: "短期套餐", durationDays: 1 as const, priceCents: 2900, knowledgeIndexAllowance: 0 as const };
    const long = { ...source, id: "long", displayName: "长期套餐", durationDays: 30 as const, priceCents: 32900, knowledgeIndexAllowance: 2 as const };
    const { rerender } = render(<HomepagePricing billing={{ ...billing, catalog: [long, short] }} />);
    expect(screen.getByRole("region", { name: "当前会员权益" })).toHaveTextContent("短期套餐");
    fireEvent.click(screen.getByRole("button", { name: "30 天 ¥329.00" }));
    expect(screen.getByRole("region", { name: "当前会员权益" })).toHaveTextContent("含 2 份知识材料额度");
    rerender(<HomepagePricing billing={{ ...billing, catalog: [short] }} />);
    expect(screen.getByRole("region", { name: "当前会员权益" })).toHaveTextContent("知识材料按实际用量另行计费");
    expect(screen.getByRole("region", { name: "当前会员权益" })).not.toHaveTextContent("329.00");
    rerender(<HomepagePricing billing={{ ...billing, catalog: [] }} />);
    expect(screen.queryByRole("region", { name: "当前会员权益" })).toBeNull();
    expect(screen.getByText(/当前暂无可展示的会员套餐/)).toBeInTheDocument();
  });

  it("shows relevant role links without needing to expand the full scenarios", () => {
    const { container } = open();
    const links = container.querySelectorAll(".cn-scenario-paths a");
    expect([...links].map(link => link.getAttribute("href"))).toEqual(["/features/ai-interview-assistant", "/features/realtime-interview", "/guides"]);
    expect(container.querySelector(".cn-more-scenarios > details")).not.toHaveAttribute("open");
    expect(container.querySelector(".partner-home-entry")).toBeNull();
    expect(container.querySelectorAll(".cn-tour-steps")).toHaveLength(1);
  });
});
