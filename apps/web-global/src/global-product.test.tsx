import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { App } from "./App";
import type { WebAppState } from "./domain";
import { syntheticState } from "../../web/src/test-state";
import { globalEditionMetadata } from "./product-edition";
import { translateGlobalCopy } from "./global-copy";
import { globalCopyByHash } from "./global-copy.generated";
import { authClient } from "./auth-client";
import { readRuntimeConfig } from "./runtime-config";
import { publicReviewCatalogue, publicReviewPage } from "./public-review-pages";

describe("Global English product", () => {
  beforeEach(() => {
    window.history.replaceState({}, "", "/");
    window.localStorage.clear();
    window.sessionStorage.clear();
  });

  it("renders the public product shell in English", () => {
    render(<App initialAuthenticated={false} initialState={structuredClone(syntheticState) as unknown as WebAppState} />);

    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(publicReviewCatalogue.heroTitle);
    expect(screen.getAllByRole("link", { name: /sign in/i }).length).toBeGreaterThan(0);
    expect(document.body.textContent?.replaceAll(publicReviewCatalogue.operator, "")).not.toMatch(/[\u3400-\u9fff]/);
    expect(document.body.textContent).toContain(`Operated by ${publicReviewCatalogue.operator}`);
  });

  it("renders the international product film with user-controlled playback", () => {
    render(<App initialAuthenticated={false} initialState={structuredClone(syntheticState) as unknown as WebAppState} />);

    expect(screen.getByRole("heading", { name: "A look inside OfferSteady" })).toBeInTheDocument();
    const video = screen.getByLabelText("OfferSteady product film") as HTMLVideoElement;
    expect(video).toHaveAttribute("controls");
    expect(video.muted).toBe(true);
    expect(video.playsInline).toBe(true);
    expect(video).toHaveAttribute("preload", "metadata");
    expect(video).not.toHaveAttribute("autoplay");
    expect(video).toHaveAttribute("poster", "/media/offersteady-global-commercial-poster-20260907.jpg");
    expect(video.querySelector("source")).toHaveAttribute("src", "/media/offersteady-global-commercial-20260907.mp4");
    expect(video.querySelector("source")).toHaveAttribute("type", "video/mp4");
  });

  it("places translated anonymous feedback between benefits and pricing", () => {
    render(<App initialAuthenticated={false} initialState={structuredClone(syntheticState) as unknown as WebAppState} />);
    const feedback = screen.getByRole("region", { name: /What our users say/ });
    expect(feedback.previousElementSibling).toHaveAttribute("id", "benefits");
    expect(feedback.nextElementSibling).toHaveAttribute("id", "plans");
    expect(within(feedback).getByRole("button", { name: "Next feedback" })).toBeInTheDocument();
  });

  it("adds a narrated usage guide without replacing the product film", () => {
    render(<App initialAuthenticated={false} initialState={structuredClone(syntheticState) as unknown as WebAppState} />);
    expect(screen.getByLabelText("OfferSteady product film")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Your first session, step by step" })).toBeInTheDocument();
    const video = screen.getByLabelText("OfferSteady getting started guide") as HTMLVideoElement;
    expect(video).toHaveAttribute("controls");
    expect(video.muted).toBe(true);
    expect(video.playsInline).toBe(true);
    expect(video).toHaveAttribute("preload", "metadata");
    expect(video).not.toHaveAttribute("autoplay");
    expect(video).toHaveAttribute("poster", "/media/offersteady-global-usage-poster-20260907.jpg");
    expect(video.querySelector("source")).toHaveAttribute("src", "/media/offersteady-global-usage-20260907.mp4");
    expect(video.querySelector("source")).toHaveAttribute("type", "video/mp4");
  });

  it("shows canonical time-based pricing on the homepage without starting checkout", () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch");
    const canonicalPlans = publicReviewPage("pricing")?.plans ?? [];
    render(<App initialAuthenticated={false} initialState={structuredClone(syntheticState) as unknown as WebAppState} />);

    const pricing = screen.getByRole("region", { name: "Pay for the time you need." });
    expect(within(pricing).getByText(/without an annual commitment/)).toBeInTheDocument();
    for (const plan of canonicalPlans) {
      const card = within(pricing).getByRole("heading", { level: 3, name: plan.name }).closest("article");
      expect(card).not.toBeNull();
      expect(within(card as HTMLElement).getByText(plan.price)).toBeInTheDocument();
      if (plan.term) expect(within(card as HTMLElement).getByText(plan.term.trim())).toBeInTheDocument();
      for (const feature of plan.features.slice(0, plan.name === "Free" ? 2 : undefined)) {
        expect(within(card as HTMLElement).getByText(`✓ ${feature}`)).toBeInTheDocument();
      }
      if (plan.featured) expect(card).toHaveClass("featured");
    }
    expect(within(pricing).getByRole("link", { name: /Start free/ })).toHaveAttribute("href", "/login");
    expect(within(pricing).getByRole("link", { name: /Compare all plans/ })).toHaveAttribute("href", "/pricing");
    expect(fetchSpy.mock.calls.some(([input]) => /checkout/i.test(String(input)))).toBe(false);
    fetchSpy.mockRestore();
  });

  it("keeps arbitrary user content unchanged while translating known product copy", () => {
    expect(translateGlobalCopy("面试稳AI助手")).toBe("OfferSteady AI Interview Assistant");
    expect(translateGlobalCopy("这是用户自己输入的一段中文内容")).toBe("这是用户自己输入的一段中文内容");
  });

  it("defaults to the US profile and English backend contract", () => {
    expect(globalEditionMetadata({
      BASE_URL: "/",
      MODE: "test",
      DEV: false,
      PROD: false,
      SSR: false,
      VITE_APP_ENV: "test",
      VITE_API_BASE_URL: "http://127.0.0.1:8000",
      VITE_PUBLIC_APP_VERSION: "test",
    })).toMatchObject({ locale: "en-US", interviewLanguage: "en-US", edition: "global" });
  });

  it("keeps Global commerce disabled unless Creem is explicitly selected and enabled", () => {
    const base = { VITE_APP_ENV: "production", VITE_API_BASE_URL: "/", VITE_PUBLIC_APP_VERSION: "test" } as const;
    expect(readRuntimeConfig({ ...base, VITE_GLOBAL_COMMERCE_ENABLED: "true", VITE_GLOBAL_COMMERCE_PROVIDER: "none" }).commerceEnabled).toBe(false);
    expect(readRuntimeConfig({ ...base, VITE_GLOBAL_COMMERCE_ENABLED: "true", VITE_GLOBAL_COMMERCE_PROVIDER: "creem" })).toMatchObject({ commerceEnabled: true, commerceProvider: "creem" });
  });

  it("contains no Chinese output in the generated product-copy catalogue", () => {
    expect(Object.values(globalCopyByHash).join("\n")).not.toMatch(/[\u3400-\u9fff]/);
  });

  it.each([
    ["/app", "Your interviews"],
    ["/app/written-exams", "Your written exams"],
    ["/app/interviews/new", "Create an Interview"],
    ["/app/written-exams/new", "Create a Written Exam"],
    ["/app/interviews/demo/prepare", "PREPARATION"],
    ["/app/interviews/demo/live", "Live Conversation"],
    ["/app/interviews/review/review", "Interview Review"],
    ["/app/library", "Materials"],
    ["/app/billing", "Choose access that matches your interview schedule."],
    ["/app/guide", "User guide"],
    ["/app/devices", "Devices"],
    ["/app/settings", "Settings"],
  ])("keeps the Global customer route %s available in English", (path, expectedCopy) => {
    window.history.replaceState({}, "", path);
    const state = structuredClone(syntheticState) as unknown as WebAppState;
    state.interviews = state.interviews.map((interview) => ({ ...interview, interviewLanguage: "en-US" }));

    render(<App initialAuthenticated initialState={state} />);

    expect(screen.getAllByText(expectedCopy, { exact: false }).length).toBeGreaterThan(0);
    expect(document.body).not.toHaveTextContent("Additional product information is available for this step.");
    expect(document.body).not.toHaveTextContent("Continue the interview workflow and use AI output only as guidance based on your real experience.");
    expect(document.body).not.toHaveTextContent("Manage the materials selected for this session. Only use information you can verify.");
  });

  it("renders concise workbench navigation without generic fallback copy", () => {
    window.history.replaceState({}, "", "/app");
    const state = structuredClone(syntheticState) as unknown as WebAppState;
    state.interviews = state.interviews.map((interview) => ({ ...interview, interviewLanguage: "en-US" }));

    render(<App initialAuthenticated initialState={state} />);

    const navigation = screen.getByRole("navigation", { name: "Application navigation" });
    const mobileNavigation = screen.getByRole("navigation", { name: "Mobile application navigation" });
    for (const label of ["Interviews", "Written exams", "Materials", "Plans & credits", "Product guide", "Devices", "Settings"]) {
      expect(within(navigation).getByRole("link", { name: label })).toBeInTheDocument();
      expect(within(mobileNavigation).getByRole("link", { name: label })).toBeInTheDocument();
    }
    expect(within(navigation).queryByRole("link", { name: "User manual" })).not.toBeInTheDocument();
    expect(within(navigation).queryByRole("link", { name: /用户手册/ })).not.toBeInTheDocument();
    expect(within(mobileNavigation).queryByRole("link", { name: "User manual" })).not.toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 1, name: "Your interviews" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "+ New interview" })).toBeInTheDocument();
    expect(document.body).not.toHaveTextContent("Additional product information is available for this step.");
    expect(document.body).not.toHaveTextContent("Continue the interview workflow and use AI output only as guidance based on your real experience.");
  });

  it("shows the approved international pricing without domestic payment methods", () => {
    window.history.replaceState({}, "", "/app/billing");
    const fetchSpy = vi.spyOn(globalThis, "fetch");
    render(<App initialAuthenticated initialState={structuredClone(syntheticState) as unknown as WebAppState} />);

    expect(screen.getByRole("heading", { level: 1, name: "Choose access that matches your interview schedule." })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Pro Weekly" })).toBeInTheDocument();
    expect(screen.getByText("$49.99")).toBeInTheDocument();
    expect(screen.getByText("Renews monthly until canceled")).toBeInTheDocument();
    expect(document.body).not.toHaveTextContent(/referral|invite friends|alipay|wechat pay/i);
    expect(fetchSpy.mock.calls.some(([input]) => /referral|checkout/i.test(String(input)))).toBe(false);
    fetchSpy.mockRestore();
  });

  it("redirects legacy Global invitation links without resolving or activating referrals", async () => {
    window.history.replaceState({}, "", "/invite/legacy-code-123");
    const fetchSpy = vi.spyOn(globalThis, "fetch");
    render(<App initialAuthenticated={false} initialState={structuredClone(syntheticState) as unknown as WebAppState} />);

    expect(await screen.findByRole("heading", { level: 1, name: publicReviewCatalogue.heroTitle })).toBeInTheDocument();
    expect(window.location.pathname).toBe("/");
    expect(fetchSpy.mock.calls.some(([input]) => /referral/i.test(String(input)))).toBe(false);
    fetchSpy.mockRestore();
  });

  it("uses a focused empty state when no interview exists", () => {
    window.history.replaceState({}, "", "/app");
    const state = structuredClone(syntheticState) as unknown as WebAppState;
    state.interviews = [];

    render(<App initialAuthenticated initialState={state} />);

    expect(screen.getByRole("heading", { name: "Create your first interview" })).toBeInTheDocument();
    expect(screen.getByText("Your recent interviews will appear here.")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Materials ready" })).toBeInTheDocument();
  });

  it("renders an empty materials workspace with concise English product copy", () => {
    window.history.replaceState({}, "", "/app/library");
    const state = structuredClone(syntheticState) as unknown as WebAppState;
    state.librarySources = [];
    state.knowledgeCollections = [];
    state.knowledgeDocuments = [];

    render(<App initialAuthenticated initialState={state} />);

    expect(screen.getByRole("heading", { level: 1, name: "Interview materials" })).toBeInTheDocument();
    expect(screen.getByText("Create your first knowledge base")).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: "New library" }).length).toBeGreaterThan(0);
    expect(document.body.textContent).not.toMatch(/[\u3400-\u9fff]/);
  });

  it("renders Resume and Job Description empty states entirely in English", () => {
    window.history.replaceState({}, "", "/app/library");
    const state = structuredClone(syntheticState) as unknown as WebAppState;
    state.librarySources = [];
    state.knowledgeCollections = [];
    state.knowledgeDocuments = [];

    render(<App initialAuthenticated initialState={state} />);

    fireEvent.click(screen.getByRole("button", { name: /Resume/ }));
    expect(screen.getByRole("heading", { name: "No resumes yet" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Add Resume" })).toBeInTheDocument();
    expect(document.body.textContent).not.toMatch(/[\u3400-\u9fff]/);
    fireEvent.click(screen.getByRole("button", { name: "Add Resume" }));
    expect(screen.getByLabelText("Select resume file")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("e.g. Senior frontend resume")).toBeInTheDocument();
    expect(document.body.textContent).not.toMatch(/[\u3400-\u9fff]/);
    fireEvent.click(screen.getByRole("button", { name: "Cancel" }));

    fireEvent.click(screen.getByRole("button", { name: /Job Description/ }));
    expect(screen.getByRole("heading", { name: "No job descriptions yet" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Add JD" })).toBeInTheDocument();
    expect(document.body.textContent).not.toMatch(/[\u3400-\u9fff]/);
    fireEvent.click(screen.getByRole("button", { name: "Add JD" }));
    expect(screen.getByLabelText("Job description text")).toBeInTheDocument();
    expect(screen.getByLabelText("Select job description file")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Add and process" })).toBeDisabled();
    expect(document.body.textContent).not.toMatch(/[\u3400-\u9fff]/);
  });

  it.each([
    ["/login", "Sign in"],
    ["/terms", "Terms of Service"],
    ["/privacy", "Privacy Policy"],
    ["/refund-policy", "Refund Policy"],
    ["/pricing", "Choose the plan that fits your interview schedule."],
    ["/contact", "Contact OfferSteady"],
    ["/about", "Interview guidance grounded in your real experience."],
    ["/security", "Security and privacy are product boundaries."],
    ["/features", "AI interview guidance for preparation and live sessions."],
    ["/features/ai-interview-assistant", "Keep interview guidance connected to your real experience."],
    ["/features/realtime-interview", "Follow live interview questions without losing the conversation."],
    ["/features/screenshot-answer", "Turn a selected screen region into structured answer guidance."],
    ["/features/interview-review", "Review what was asked, what appeared, and what to improve."],
    ["/guides", "Prepare evidence before you prepare wording."],
    ["/interview-questions", "Understand what the interviewer is trying to evaluate."],
    ["/download", "Connect interview audio and screenshots to your Web workspace."],
  ])("keeps the Global public route %s available in English", (path, expectedCopy) => {
    window.history.replaceState({}, "", path);
    render(<App initialAuthenticated={false} initialState={structuredClone(syntheticState) as unknown as WebAppState} />);

    expect(screen.getAllByText(expectedCopy, { exact: false }).length).toBeGreaterThan(0);
  });

  it("does not expose the removed public user-manual route", () => {
    window.history.replaceState({}, "", "/guide");
    render(<App initialAuthenticated={false} initialState={structuredClone(syntheticState) as unknown as WebAppState} />);

    expect(screen.queryByRole("heading", { name: "User guide" })).not.toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Page not found" })).toBeInTheDocument();
  });

  it("shows live pricing with sign-in links without opening a payment flow", () => {
    window.history.replaceState({}, "", "/pricing");
    const fetchSpy = vi.spyOn(globalThis, "fetch");
    render(<App initialAuthenticated={false} initialState={structuredClone(syntheticState) as unknown as WebAppState} />);

    expect(screen.getByRole("heading", { name: "Free" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Interview Day Pass" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Pro Weekly" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Pro Monthly" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Job Hunt" })).toBeInTheDocument();
    const checkoutLinks = screen.getAllByRole("link", { name: "Sign in to choose plan" });
    expect(checkoutLinks).toHaveLength(4);
    for (const link of checkoutLinks) expect(link).toHaveAttribute("href", "/login");
    expect(screen.getByText(/Monthly subscription · renews automatically until cancelled/)).toBeInTheDocument();
    expect(screen.getAllByText(/One-time payment · no automatic renewal/)).toHaveLength(3);
    expect(screen.getByText(/24 consecutive hours from confirmed payment/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Start Free" })).toHaveAttribute("href", "/login");
    expect(fetchSpy).not.toHaveBeenCalled();
    fetchSpy.mockRestore();
  });

  it("gives the public Download page a verified Start Free path without exposing an installer", () => {
    window.history.replaceState({}, "", "/download");
    render(<App initialAuthenticated={false} initialState={structuredClone(syntheticState) as unknown as WebAppState} />);

    expect(screen.getByRole("link", { name: /Start Free/ })).toHaveAttribute("href", "/login");
    expect(screen.getByText(/Verified Companion release options appear in the interview preparation flow/)).toBeInTheDocument();
    expect(document.querySelector('a[href$=".dmg"], a[href$=".pkg"], a[href$=".exe"], a[href$=".msi"]')).toBeNull();
  });

  it("keeps merchant identity, support, compliance, and refund navigation consistent", () => {
    window.history.replaceState({}, "", "/contact");
    render(<App initialAuthenticated={false} initialState={structuredClone(syntheticState) as unknown as WebAppState} />);

    expect(screen.getAllByText(/杭州临平知界智能技术工作室/).length).toBeGreaterThan(0);
    expect(screen.getAllByRole("link", { name: "contact@oneshowailab.com" }).length).toBeGreaterThan(0);
    expect(screen.getByRole("link", { name: "Refund Policy" })).toHaveAttribute("href", "/refund-policy");
  });

  it("uses an email-and-password customer sign-in form", async () => {
    window.history.replaceState({}, "", "/login");
    const fetchSpy = vi.spyOn(globalThis, "fetch");
    render(<App initialAuthenticated={false} initialState={structuredClone(syntheticState) as unknown as WebAppState} />);

    expect(screen.getByLabelText("Email address")).toBeInTheDocument();
    expect(screen.getByLabelText("Password")).toBeInTheDocument();
    expect(screen.queryByText("手机号")).not.toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Email address"), { target: { value: "not-an-email" } });
    fireEvent.click(screen.getByRole("button", { name: "Sign in" }));
    expect(await screen.findByText("Enter a valid email address.")).toBeInTheDocument();
    expect(fetchSpy).not.toHaveBeenCalled();
    fetchSpy.mockRestore();
  });

  it("shows the masked destination and resend cooldown after sending a code", async () => {
    window.history.replaceState({}, "", "/login");
    const response = new Response(JSON.stringify({ success: true, data: { challengeId: "email-challenge-ui", status: "sent", provider: "fake", expiresAtMs: Date.now() + 60_000, cooldownSeconds: 60, maskedEmail: "ca*****@example.com" }, error: null, requestId: "test", meta: { apiVersion: "v1", timestamp: "now" } }), { status: 200, headers: { "content-type": "application/json" } });
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(response);
    render(<App initialAuthenticated={false} initialState={structuredClone(syntheticState) as unknown as WebAppState} />);

    fireEvent.click(screen.getByRole("button", { name: "Create account" }));
    fireEvent.change(screen.getByLabelText("Email address"), { target: { value: "candidate@example.com" } });
    fireEvent.click(screen.getByRole("button", { name: "Send verification code" }));
    expect(await screen.findByText(/ca\*{5}@example\.com/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Resend in 60s" })).toBeDisabled();
    expect(fetchSpy).toHaveBeenCalledOnce();
    fetchSpy.mockRestore();
  });

  it("uses purpose-bound registration and password endpoints", async () => {
    const envelope = (data: unknown) => new Response(JSON.stringify({ success: true, data, error: null, requestId: "test", meta: { apiVersion: "v1", timestamp: "now" } }), { status: 200, headers: { "content-type": "application/json" } });
    const fetchSpy = vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(envelope({ challengeId: "email-challenge-test", status: "sent", provider: "fake", expiresAtMs: Date.now() + 60_000, cooldownSeconds: 60, maskedEmail: "ca*****@example.com" }))
      .mockResolvedValueOnce(envelope({ user: { userId: "email-user", displayName: "candidate", createdAtMs: 1, bindings: [{ bindingId: "email-binding", provider: "email", displayName: "Email", status: "active", boundAtMs: 1 }] }, tokens: { accessToken: "access", refreshToken: "refresh" } }));

    const sent = await authClient.sendGlobalEmailCode("candidate@example.com", "registration");
    expect(sent.maskedEmail).toBe("ca*****@example.com");
    const session = await authClient.completeGlobalPasswordFlow({ mode: "registration", email: "candidate@example.com", challengeId: sent.challengeId, code: "123456", password: "correct horse battery staple" });
    expect(session.account.bindings[0]?.provider).toBe("email");
    await waitFor(() => expect(fetchSpy).toHaveBeenCalledTimes(3));
    expect(String(fetchSpy.mock.calls[0]?.[0])).toContain("/api/v1/auth/global/email/send-code");
    expect(String(fetchSpy.mock.calls[1]?.[0])).toContain("/api/v1/auth/global/register");
    fetchSpy.mockRestore();
  });

  it("signs in with a password without requesting an email code", async () => {
    const envelope = (data: unknown) => new Response(JSON.stringify({ success: true, data, error: null, requestId: "test", meta: { apiVersion: "v1", timestamp: "now" } }), { status: 200, headers: { "content-type": "application/json" } });
    const fetchSpy = vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(envelope({ user: { userId: "password-user", displayName: "candidate", createdAtMs: 1, bindings: [{ bindingId: "email-binding", provider: "email", displayName: "Email", status: "active", boundAtMs: 1 }] }, tokens: { accessToken: "access", refreshToken: "refresh" } }))
      .mockResolvedValueOnce(envelope({ accepted: true }));

    const session = await authClient.loginGlobal({ email: "candidate@example.com", password: "correct horse battery staple" });
    expect(session.account.id).toBe("password-user");
    await waitFor(() => expect(fetchSpy).toHaveBeenCalledTimes(2));
    expect(String(fetchSpy.mock.calls[0]?.[0])).toContain("/api/v1/auth/global/password/login");
    expect(String(fetchSpy.mock.calls[0]?.[0])).not.toContain("send-code");
    fetchSpy.mockRestore();
  });
});
