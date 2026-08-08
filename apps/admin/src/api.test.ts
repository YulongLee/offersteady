import { describe, expect, it } from "vitest";

import { adminAuthenticationMessage } from "./api";

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
