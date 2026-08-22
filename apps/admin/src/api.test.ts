import { describe, expect, it } from "vitest";

import { adminAuthenticationMessage, adminGatewayMessage } from "./api";

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
