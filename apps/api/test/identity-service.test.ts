import { describe, expect, it } from "vitest";
import { IdentityError, IdentityService } from "../src/identity-service.js";

const provider = { exchangeCode: async (code: string) => ({ subjectId: `subject:${code}`, displayName: `用户${code}` }) };
describe("IdentityService", () => {
  it("creates one account and consumes authorization state once", async () => {
    const service = new IdentityService(provider); const state = service.createWechatState(1, 100);
    const result = await service.completeWechat(state.id, "a", 2); expect(result.createdAccount).toBe(true);
    await expect(service.completeWechat(state.id, "a", 3)).rejects.toMatchObject({ code: "invalid-state" });
  });
  it("returns an existing account for the same provider subject", async () => {
    const service = new IdentityService(provider); const first = await service.completeWechat(service.createWechatState(1).id, "a", 2); const second = await service.completeWechat(service.createWechatState(3).id, "a", 4);
    expect(second.account.id).toBe(first.account.id); expect(second.createdAccount).toBe(false);
  });
  it("blocks binding collisions and removal of the last login", async () => {
    const service = new IdentityService(provider); const first = await service.completeWechat(service.createWechatState(1).id, "a", 2); const second = await service.completeWechat(service.createWechatState(3).id, "b", 4);
    await expect(service.bindWechat(second.account.id, service.createWechatState(5).id, "a", true, 6)).rejects.toMatchObject({ code: "collision" });
    expect(() => service.unbind(first.account.id, first.account.bindings[0]!.id)).toThrowError(expect.objectContaining({ code: "forbidden" }));
    expect(IdentityError).toBeDefined();
  });
  it("rejects expired state and provider failures safely", async () => {
    const expired = new IdentityService(provider); await expect(expired.completeWechat(expired.createWechatState(1, 1).id, "a", 2)).rejects.toMatchObject({ code: "invalid-state" });
    const failed = new IdentityService({ exchangeCode: async () => { throw new Error("secret provider detail"); } }); await expect(failed.completeWechat(failed.createWechatState(1).id, "x", 2)).rejects.toMatchObject({ message: "微信授权暂时不可用" });
  });
});
