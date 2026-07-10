import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const {
  createWechatAuthorizationSession,
  simulateAuthorize,
  getWechatAuthorizationSession,
  acceptAuthorizedResult,
} = vi.hoisted(() => ({
  createWechatAuthorizationSession: vi.fn(),
  simulateAuthorize: vi.fn(),
  getWechatAuthorizationSession: vi.fn(),
  acceptAuthorizedResult: vi.fn(),
}));

vi.mock("./auth-client", () => ({
  authClient: {
    createWechatAuthorizationSession,
    getWechatAuthorizationSession,
    simulateAuthorize,
    acceptAuthorizedResult,
  },
}));

import { WechatLoginDialog } from "./WechatLoginDialog";

describe("WechatLoginDialog", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    createWechatAuthorizationSession.mockResolvedValue({
      authRequestId: "wechat-auth-1",
      status: "waiting",
      authorizationUrl: "https://wechat.example/qr",
      qrCodeText: "https://wechat.example/qr",
      expiresAtMs: Date.now() + 300_000,
      createdAtMs: Date.now(),
      updatedAtMs: Date.now(),
      providerSubjectHint: "微信用户1234",
    });
    getWechatAuthorizationSession.mockResolvedValue({
      authRequestId: "wechat-auth-1",
      status: "waiting",
      authorizationUrl: "https://wechat.example/qr",
      qrCodeText: "https://wechat.example/qr",
      expiresAtMs: Date.now() + 300_000,
      createdAtMs: Date.now(),
      updatedAtMs: Date.now(),
      providerSubjectHint: "微信用户1234",
    });
    simulateAuthorize.mockResolvedValue({
      authRequestId: "wechat-auth-1",
      status: "authorized",
      authorizationUrl: "https://wechat.example/qr",
      qrCodeText: "https://wechat.example/qr",
      expiresAtMs: Date.now() + 300_000,
      createdAtMs: Date.now(),
      updatedAtMs: Date.now(),
      providerSubjectHint: "微信用户1234",
      result: {
        user: {
          userId: "user-1",
          displayName: "微信用户1234",
          createdAtMs: 1,
          bindings: [],
        },
        tokens: { accessToken: "access-token", refreshToken: "refresh-token" },
      },
    });
    acceptAuthorizedResult.mockReturnValue({
      accessToken: "access-token",
      refreshToken: "refresh-token",
      account: { id: "user-1", displayName: "微信用户1234", createdAtMs: 1, bindings: [] },
    });
  });

  it("creates an authorization session and completes authorization through the backend contract", async () => {
    const onAuthorized = vi.fn();
    render(<WechatLoginDialog onClose={() => undefined} onAuthorized={onAuthorized} />);

    await screen.findByText("https://wechat.example/qr");
    fireEvent.click(screen.getByRole("button", { name: "模拟授权成功" }));

    await waitFor(() => expect(onAuthorized).toHaveBeenCalled());
    expect(createWechatAuthorizationSession).toHaveBeenCalled();
    expect(simulateAuthorize).toHaveBeenCalledWith("wechat-auth-1");
    expect(acceptAuthorizedResult).toHaveBeenCalled();
  });
});
