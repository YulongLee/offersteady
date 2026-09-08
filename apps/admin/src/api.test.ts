import { afterEach, describe, expect, it, vi } from "vitest";

import { adminApi, adminAuthenticationMessage, adminGatewayMessage } from "./api";

afterEach(() => vi.restoreAllMocks());

describe("admin authentication error guidance", () => {
  it("turns expired sessions into a readable relogin message", () => {
    expect(adminAuthenticationMessage(401, "admin_session_invalid")).toBe("管理员登录已过期，请重新登录后继续操作。");
  });

  it("turns recent MFA expiry into a readable verification message", () => {
    expect(adminAuthenticationMessage(403, "admin_step_up_required")).toBe("管理员安全验证已过期，请重新登录后继续操作。");
  });

  it("does not classify unrelated validation errors as authentication failures", () => {
    expect(adminAuthenticationMessage(409, "merchantPrivateKey 不是有效的 PEM 私钥")).toBeNull();
  });
});

describe("admin gateway error guidance", () => {
  it.each([502, 503, 504])("explains a temporary upstream failure for %s", status => {
    expect(adminGatewayMessage(status)).toContain("暂时无法连接后端服务");
    expect(adminGatewayMessage(status)).toContain("无需重新输入手机号");
  });

  it("leaves business errors to their server detail", () => {
    expect(adminGatewayMessage(422)).toBeNull();
  });
});

describe("Global Admin email authentication client", () => {
  it("uses the existing email challenge endpoints without changing Admin authorization", async () => {
    const envelope = (data: unknown) => new Response(JSON.stringify({ data }), { status: 200, headers: { "content-type": "application/json" } });
    const fetchSpy = vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(envelope({ challengeId: "synthetic-email-challenge", cooldownSeconds: 60, maskedEmail: "op*****@example.com" }))
      .mockResolvedValueOnce(envelope({ tokens: { accessToken: "synthetic-user-access-token" } }));

    const sent = await adminApi.sendEmailCode("operator@example.com");
    const verified = await adminApi.verifyEmailLogin("operator@example.com", sent.challengeId, "123456");

    expect(sent.maskedEmail).toBe("op*****@example.com");
    expect(verified.tokens.accessToken).toBe("synthetic-user-access-token");
    expect(String(fetchSpy.mock.calls[0]?.[0])).toContain("/api/v1/auth/email/send-code");
    expect(String(fetchSpy.mock.calls[1]?.[0])).toContain("/api/v1/auth/email/verify-login");
    expect(JSON.parse(String(fetchSpy.mock.calls[0]?.[1]?.body))).toEqual({ email: "operator@example.com", clientLabel: "global-commercial-admin" });
  });
});

describe("Global Creem administration client", () => {
  it("keeps Test mode explicit and never sends blank secrets as persisted values", async () => {
    const envelope = (data: unknown) => new Response(JSON.stringify({ data }), { status: 200, headers: { "content-type": "application/json" } });
    const fetchSpy = vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(envelope({ credentials: { apiKey: { configured: true } } }))
      .mockResolvedValueOnce(envelope({ mode: "test", items: [], syncedAtMs: 1 }))
      .mockResolvedValueOnce(envelope({ validationStatus: "ready" }));

    await adminApi.saveGlobalCommerceCredentials("test", "creem_test_synthetic", "", "configure test mode");
    await adminApi.globalCommerceProducts("test");
    await adminApi.saveGlobalCommerceMapping("test", "global-pro-weekly", "prod_synthetic", "map test product");

    expect(String(fetchSpy.mock.calls[0]?.[0])).toContain("/credentials?mode=test");
    expect(JSON.parse(String(fetchSpy.mock.calls[0]?.[1]?.body))).toEqual({ apiKey: "creem_test_synthetic", webhookSecret: null, reason: "configure test mode" });
    expect(String(fetchSpy.mock.calls[1]?.[0])).toContain("/products?mode=test");
    expect(String(fetchSpy.mock.calls[2]?.[0])).toContain("/mappings/global-pro-weekly?mode=test");
  });
});
