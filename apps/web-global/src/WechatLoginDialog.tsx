import { useEffect, useState } from "react";
import type { SafeAccountSummary } from "@offersteady/protocol";

import { assetUrl } from "./assets";
import { authClient, type WechatAuthorizationSessionResponse } from "./auth-client";
type State = "creating" | "waiting" | "scanned" | "authorized" | "expired" | "failed";
export function WechatLoginDialog({ onClose, onAuthorized }: { readonly onClose: () => void; readonly onAuthorized: (account: SafeAccountSummary) => void }) {
  const [state, setState] = useState<State>("creating");
  const [authRequestId, setAuthRequestId] = useState<string | null>(null);
  const [qrText, setQrText] = useState("微信官方授权二维码占位");
  const [errorMessage, setErrorMessage] = useState("");
  const syncFromBackend = async (nextState: State, fetcher: () => Promise<WechatAuthorizationSessionResponse>) => {
    try {
      const payload = await fetcher();
      setState(payload.status);
      setAuthRequestId(payload.authRequestId);
      setQrText(payload.qrCodeText);
      setErrorMessage(payload.errorMessage ?? "");
      if (payload.result) {
        const stored = authClient.acceptAuthorizedResult(payload.result);
        setState("authorized");
        window.setTimeout(() => onAuthorized(stored.account), 180);
      }
    } catch (error) {
      setState(nextState);
      setErrorMessage(error instanceof Error ? error.message : "微信授权暂时不可用");
    }
  };
  useEffect(() => {
    const controller = new AbortController();
    void (async () => {
      try {
        const created = await authClient.createWechatAuthorizationSession(controller.signal);
        setState(created.status);
        setAuthRequestId(created.authRequestId);
        setQrText(created.qrCodeText);
      } catch (error) {
        setState("failed");
        setErrorMessage(error instanceof Error ? error.message : "微信授权暂时不可用");
      }
    })();
    return () => controller.abort();
  }, []);
  useEffect(() => {
    if (!authRequestId || state === "authorized" || state === "expired" || state === "failed") return;
    const id = window.setInterval(() => {
      void syncFromBackend(state, () => authClient.getWechatAuthorizationSession(authRequestId));
    }, 1200);
    return () => window.clearInterval(id);
  }, [authRequestId, state]);
  const title = state === "creating" ? "正在创建微信授权" : state === "waiting" ? "使用微信扫码登录" : state === "scanned" ? "已扫码，请在微信确认" : state === "authorized" ? "授权成功" : state === "expired" ? "二维码已过期" : "微信授权暂时不可用";
  return <div className="sheet-backdrop" role="dialog" aria-modal="true" aria-labelledby="wechat-login-title"><section className="sheet wechat-login-sheet"><button className="sheet-close" aria-label="关闭微信登录" onClick={onClose}>×</button><img className="channel-logo" src={assetUrl("payments.wechat")} alt="微信登录" /><h2 id="wechat-login-title">{title}</h2><p>授权只用于创建或绑定面试稳账号，不会读取聊天记录。</p><div className={`auth-qr ${state}`}><span>{state === "creating" ? "创建授权会话…" : state === "expired" ? "授权已失效" : state === "failed" ? (errorMessage || "提供方连接失败") : qrText}</span><small>生产环境由服务端返回短期官方二维码</small></div>{import.meta.env.DEV && authRequestId && (state === "waiting" || state === "scanned") ? <div className="prototype-auth-actions"><button onClick={() => void syncFromBackend("failed", () => authClient.simulateScan(authRequestId))}>模拟已扫码</button><button onClick={() => void syncFromBackend("failed", () => authClient.simulateAuthorize(authRequestId))}>模拟授权成功</button><button onClick={() => setState("expired")}>模拟过期</button></div> : null}{state === "expired" || state === "failed" ? <button className="button primary full" onClick={() => { setState("creating"); setAuthRequestId(null); setErrorMessage(""); void authClient.createWechatAuthorizationSession().then(created => { setState(created.status); setAuthRequestId(created.authRequestId); setQrText(created.qrCodeText); }).catch(error => { setState("failed"); setErrorMessage(error instanceof Error ? error.message : "微信授权暂时不可用"); }); }}>刷新授权二维码</button> : null}<small className="auth-boundary">当前开发环境可通过兼容 Provider 联调；正式环境将切换为服务端微信授权提供方。</small></section></div>;
}
