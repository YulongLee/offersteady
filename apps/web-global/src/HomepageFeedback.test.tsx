import { act, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import homepageHtml from "../index.html?raw";
import { HomepageFeedback } from "./HomepageFeedback";
import feedback from "./homepage-feedback.json";

let reduced = false;
let width = 1280;
let visibility: (visible: boolean) => void;
let observerDisconnected: ReturnType<typeof vi.fn>;
let mediaChanges: Map<string, () => void>;

beforeEach(() => {
  vi.useFakeTimers();
  reduced = false;
  width = 1280;
  mediaChanges = new Map();
  observerDisconnected = vi.fn();
  vi.stubGlobal("matchMedia", vi.fn((query: string) => ({
    get matches() { return query.includes("reduced-motion") ? reduced : width <= (query.includes("720") ? 720 : 1050); },
    addEventListener: (_: string, handler: () => void) => mediaChanges.set(query, handler),
    removeEventListener: (_: string, handler: () => void) => { if (mediaChanges.get(query) === handler) mediaChanges.delete(query); },
  })));
  vi.stubGlobal("IntersectionObserver", class {
    constructor(callback: (entries: { isIntersecting: boolean }[]) => void) { visibility = visible => callback([{ isIntersecting: visible }]); }
    observe() { visibility(true); }
    disconnect() { observerDisconnected(); }
  });
  vi.spyOn(document, "hidden", "get").mockReturnValue(false);
});

afterEach(() => { vi.useRealTimers(); vi.unstubAllGlobals(); vi.restoreAllMocks(); });
const tick = () => act(() => { vi.advanceTimersByTime(10_000); });
const firstQuote = () => document.querySelector(".feedback-card blockquote")?.textContent;

describe("homepage feedback", () => {
  it("contains exactly 20 anonymous translations and preserves qualifications", () => {
    expect(feedback.entries).toHaveLength(20);
    expect(new Set(feedback.entries.map(entry => entry.id)).size).toBe(20);
    expect(JSON.stringify(feedback)).not.toMatch(/[\u3400-\u9fff]/);
    expect(feedback.entries[3].quote).toContain("more detailed guide");
    expect(feedback.entries[8].quote).toContain("inaccurately");
    expect(feedback.entries[12].quote).toContain("don't know the result yet");
    expect(feedback.entries[17].quote).toContain("I'd suggest");
    expect(feedback.entries[19].quote).toContain("Better stability");
    for (const entry of feedback.entries) expect(Object.keys(entry).sort()).toEqual(["id", "quote", "topic"]);
  });

  it.each([[1280, 3], [900, 2], [390, 1]])("shows the correct number of full quotes at %ipx", (viewport, count) => {
    width = viewport;
    render(<HomepageFeedback />);
    const region = screen.getByRole("region", { name: /What our users say/ });
    expect(within(region).getAllByRole("article")).toHaveLength(count);
    expect(within(region).getAllByText("Anonymous user")).toHaveLength(count);
    expect(within(region).getByText(feedback.note)).toBeInTheDocument();
    expect(firstQuote()).toBe(feedback.entries[0].quote);
    expect(region.querySelector("img")).toBeNull();
  });

  it("makes every entry reachable and wraps both directions", () => {
    width = 390;
    render(<HomepageFeedback />);
    for (const entry of feedback.entries) {
      expect(firstQuote()).toBe(entry.quote);
      fireEvent.click(screen.getByRole("button", { name: "Next feedback" }));
    }
    expect(firstQuote()).toBe(feedback.entries[0].quote);
    fireEvent.click(screen.getByRole("button", { name: "Previous feedback" }));
    expect(firstQuote()).toBe(feedback.entries[19].quote);
    tick();
    expect(firstQuote()).toBe(feedback.entries[19].quote);
  });

  it("rotates only while visible and pauses on hover or a hidden tab", () => {
    render(<HomepageFeedback />);
    tick();
    expect(firstQuote()).toBe(feedback.entries[1].quote);
    const region = screen.getByRole("region", { name: /What our users say/ });
    fireEvent.mouseEnter(region);
    tick();
    expect(firstQuote()).toBe(feedback.entries[1].quote);
    fireEvent.mouseLeave(region);
    act(() => visibility(false));
    tick();
    expect(firstQuote()).toBe(feedback.entries[1].quote);
    act(() => visibility(true));
    vi.spyOn(document, "hidden", "get").mockReturnValue(true);
    fireEvent(document, new Event("visibilitychange"));
    tick();
    expect(firstQuote()).toBe(feedback.entries[1].quote);
    vi.spyOn(document, "hidden", "get").mockReturnValue(false);
    fireEvent(document, new Event("visibilitychange"));
    tick();
    expect(firstQuote()).toBe(feedback.entries[2].quote);
  });

  it("stops on keyboard focus and requires an explicit restart", () => {
    render(<HomepageFeedback />);
    fireEvent.focus(screen.getByRole("button", { name: "Next feedback" }));
    tick();
    expect(firstQuote()).toBe(feedback.entries[0].quote);
    fireEvent.click(screen.getByRole("button", { name: "Play feedback rotation" }));
    tick();
    expect(firstQuote()).toBe(feedback.entries[1].quote);
  });

  it("a pointer click on Pause stays paused even when focus changes first", () => {
    render(<HomepageFeedback />);
    const pause = screen.getByRole("button", { name: "Pause feedback rotation" });
    fireEvent.pointerDown(pause);
    fireEvent.focus(pause);
    fireEvent.click(pause);
    tick();
    expect(firstQuote()).toBe(feedback.entries[0].quote);
    expect(screen.getByRole("button", { name: "Play feedback rotation" })).toBeInTheDocument();
  });

  it("defaults to paused with reduced motion, and responds to preference changes", () => {
    reduced = true;
    render(<HomepageFeedback />);
    tick();
    expect(firstQuote()).toBe(feedback.entries[0].quote);
    fireEvent.click(screen.getByRole("button", { name: "Next feedback" }));
    expect(firstQuote()).toBe(feedback.entries[1].quote);
    fireEvent.click(screen.getByRole("button", { name: "Play feedback rotation" }));
    act(() => mediaChanges.get("(prefers-reduced-motion: reduce)")!());
    tick();
    expect(firstQuote()).toBe(feedback.entries[1].quote);
  });

  it("supports horizontal swipe without treating vertical scrolling as navigation", () => {
    width = 390;
    render(<HomepageFeedback />);
    const cards = document.getElementById("homepage-feedback-cards")!;
    fireEvent.touchStart(cards, { touches: [{ clientX: 250, clientY: 100 }] });
    fireEvent.touchEnd(cards, { changedTouches: [{ clientX: 100, clientY: 110 }] });
    expect(firstQuote()).toBe(feedback.entries[1].quote);
    fireEvent.touchStart(cards, { touches: [{ clientX: 250, clientY: 100 }] });
    fireEvent.touchEnd(cards, { changedTouches: [{ clientX: 180, clientY: 280 }] });
    expect(firstQuote()).toBe(feedback.entries[1].quote);
    tick();
    expect(firstQuote()).toBe(feedback.entries[1].quote);
  });

  it("cleans up timers, observers and media listeners when leaving the homepage", () => {
    const { unmount } = render(<HomepageFeedback />);
    expect(vi.getTimerCount()).toBeGreaterThan(0);
    unmount();
    expect(vi.getTimerCount()).toBe(0);
    expect(observerDisconnected).toHaveBeenCalled();
    expect(mediaChanges.size).toBe(0);
  });

  it("exposes the same quotes in static HTML without review schema", () => {
    const html = homepageHtml;
    const parsed = new DOMParser().parseFromString(html, "text/html");
    const section = parsed.getElementById("user-feedback")!;
    expect(section).not.toBeNull();
    expect(section.querySelectorAll("blockquote")).toHaveLength(20);
    expect(section.textContent).toContain(feedback.note);
    for (const entry of feedback.entries) expect(section.textContent).toContain(entry.quote);
    expect(html).not.toContain('"aggregateRating"');
    expect(html).not.toContain('"@type": "Review"');
  });
});
