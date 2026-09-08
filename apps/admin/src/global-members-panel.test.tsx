// @vitest-environment jsdom

import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { GlobalMembersPanel } from "./App";
import { adminApi } from "./api";


describe("GlobalMembersPanel", () => {
  afterEach(() => vi.restoreAllMocks());

  it("searches by email and renders server-authoritative member usage", async () => {
    vi.spyOn(adminApi, "globalMembers").mockResolvedValue({
      items: [{ user_id: "user-1", email: "candidate@example.com", display_name: "Candidate", current_plan_name: "Pro Weekly", current_ends_at_ms: 1_800_000_000_000 }],
      limit: 30,
      offset: 0,
    });
    vi.spyOn(adminApi, "globalMember").mockResolvedValue({
      identity: { user_id: "user-1", email: "candidate@example.com", display_name: "Candidate", created_at_ms: 1_700_000_000_000 },
      state: { usage: { copilotUnlimited: true, screenAssistUnlimited: true }, features: { resumeJd: true, knowledgeBase: true, writtenExam: true } },
      entitlements: [{ id: "entitlement-1", offerCode: "global-pro-weekly", sourceKind: "admin", status: "active", startsAtMs: 1_700_000_000_000, endsAtMs: 1_800_000_000_000 }],
      orders: [],
      subscriptions: [],
    });

    render(<GlobalMembersPanel />);
    fireEvent.change(screen.getByLabelText("搜索国际版用户"), { target: { value: "candidate@example.com" } });
    fireEvent.click(screen.getByRole("button", { name: "搜索用户" }));
    await screen.findByText("candidate@example.com");
    fireEvent.click(screen.getByRole("button", { name: /candidate@example.com/i }));

    await waitFor(() => expect(screen.getAllByText("Unlimited")).toHaveLength(2));
    expect(screen.getByText("Resume / JD")).toBeTruthy();
    expect(screen.getByText("人工会员管理")).toBeTruthy();
    expect(adminApi.globalMembers).toHaveBeenCalledWith("candidate@example.com");
  });
});
