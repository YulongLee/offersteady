// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { Login } from "./App";
import { adminApi } from "./api";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe("edition-aware Admin login", () => {
  it("uses email verification for the Global Admin build", async () => {
    const ready = vi.fn();
    vi.spyOn(adminApi, "sendEmailCode").mockResolvedValue({ challengeId: "synthetic-email-challenge", cooldownSeconds: 60, maskedEmail: "op*****@example.com" });
    vi.spyOn(adminApi, "verifyEmailLogin").mockResolvedValue({ tokens: { accessToken: "synthetic-user-access-token" } });
    vi.spyOn(adminApi, "login").mockResolvedValue({ token: "synthetic-admin-token", role: "super_admin", permissions: [], expiresAtMs: 1 });

    render(<Login mode="email" onReady={ready} />);

    expect(screen.getByLabelText("管理员邮箱")).toBeTruthy();
    expect(screen.queryByLabelText("手机号")).toBeNull();
    fireEvent.change(screen.getByLabelText("管理员邮箱"), { target: { value: "Operator@Example.com" } });
    fireEvent.click(screen.getByRole("button", { name: "获取邮件验证码" }));
    expect(await screen.findByText(/op\*{5}@example\.com/)).toBeTruthy();
    fireEvent.change(screen.getByLabelText("邮件验证码"), { target: { value: "123456" } });
    fireEvent.click(screen.getByRole("button", { name: "进入运营中心" }));

    await waitFor(() => expect(ready).toHaveBeenCalledOnce());
    expect(adminApi.sendEmailCode).toHaveBeenCalledWith("operator@example.com");
    expect(adminApi.verifyEmailLogin).toHaveBeenCalledWith("operator@example.com", "synthetic-email-challenge", "123456");
    expect(adminApi.login).toHaveBeenCalledWith("synthetic-user-access-token");
  });

  it("keeps phone and SMS controls for the domestic Admin build", () => {
    render(<Login mode="phone" onReady={() => undefined} />);

    expect(screen.getByLabelText("手机号")).toBeTruthy();
    expect(screen.getByRole("button", { name: "获取短信验证码" })).toBeTruthy();
    expect(screen.queryByLabelText("管理员邮箱")).toBeNull();
    expect(screen.queryByRole("button", { name: "获取邮件验证码" })).toBeNull();
  });

  it("does not grant Admin access when a verified email lacks authorization", async () => {
    const ready = vi.fn();
    vi.spyOn(adminApi, "sendEmailCode").mockResolvedValue({ challengeId: "synthetic-unapproved-challenge", cooldownSeconds: 60, maskedEmail: "un*******@example.com" });
    vi.spyOn(adminApi, "verifyEmailLogin").mockResolvedValue({ tokens: { accessToken: "synthetic-unapproved-access-token" } });
    vi.spyOn(adminApi, "login").mockRejectedValue(new Error("Administrator identity or MFA is invalid"));

    render(<Login mode="email" onReady={ready} />);
    fireEvent.change(screen.getByLabelText("管理员邮箱"), { target: { value: "unapproved@example.com" } });
    fireEvent.click(screen.getByRole("button", { name: "获取邮件验证码" }));
    await screen.findByText(/un\*{7}@example\.com/);
    fireEvent.change(screen.getByLabelText("邮件验证码"), { target: { value: "123456" } });
    fireEvent.click(screen.getByRole("button", { name: "进入运营中心" }));

    expect(await screen.findByText("Administrator identity or MFA is invalid")).toBeTruthy();
    expect(ready).not.toHaveBeenCalled();
  });
});
