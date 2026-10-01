import { useEffect, useRef, useState, type FormEvent } from "react";
import { Link, Navigate, useLocation, useNavigate } from "react-router-dom";
import { authClient } from "./auth-client";
import { routes } from "./routes";
import { Logo } from "./PageShell";

export function loginDestination(value: unknown): string {
  return typeof value === "string" && /^\/app(?:[/?#]|$)/.test(value) && !/[\\\r\n]/.test(value) ? value : routes.app;
}

export function LoginPage({ initialAuthenticated }: { readonly initialAuthenticated?: boolean | undefined }) {
  const [authenticated, setAuthenticated] = useState(initialAuthenticated ?? false);
  const restoreController = useRef<AbortController | null>(null);
  const navigate = useNavigate();
  const location = useLocation();
  const [mode, setMode] = useState<"login" | "registration" | "password_setup" | "password_reset">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [code, setCode] = useState("");
  const [challengeId, setChallengeId] = useState("");
  const [cooldown, setCooldown] = useState(0);
  const [busy, setBusy] = useState<"send" | "complete" | "login" | "">("");
  const [message, setMessage] = useState("");
  const destination = loginDestination((location.state as { from?: string } | null)?.from);
  const stopRestoring = () => restoreController.current?.abort();
  const enter = () => { setAuthenticated(true); navigate(destination, { replace: true }); };
  useEffect(() => {
    if (initialAuthenticated !== undefined || !authClient.readStoredSession()) return;
    const controller = new AbortController();
    restoreController.current = controller;
    // Restore only authentication, never workspace data; the form stays usable.
    void authClient.restore(controller.signal).then(() => {
      if (!controller.signal.aborted) setAuthenticated(true);
    }).catch(error => {
      if (!controller.signal.aborted && !(error instanceof DOMException && error.name === "AbortError")) authClient.clear();
    });
    return () => controller.abort();
  }, [initialAuthenticated]);
  useEffect(() => {
    if (cooldown <= 0) return;
    const id = window.setTimeout(() => setCooldown(value => Math.max(0, value - 1)), 1000);
    return () => window.clearTimeout(id);
  }, [cooldown]);
  if (authenticated) return <Navigate to={destination} replace />;
  const resetMode = (nextMode: typeof mode) => {
    stopRestoring();
    setMode(nextMode); setPassword(""); setConfirmPassword(""); setCode(""); setChallengeId(""); setCooldown(0); setMessage("");
  };
  const validEmail = () => {
    const normalizedEmail = email.trim().toLowerCase();
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(normalizedEmail)) {
      setMessage("Enter a valid email address.");
      return null;
    }
    return normalizedEmail;
  };
  const requestCode = async () => {
    stopRestoring();
    const normalizedEmail = validEmail();
    if (!normalizedEmail || mode === "login") return;
    setBusy("send");
    setMessage("");
    try {
      const response = await authClient.sendGlobalEmailCode(normalizedEmail, mode);
      setChallengeId(response.challengeId);
      setCooldown(response.cooldownSeconds);
      setMessage(`We sent a verification code to ${response.maskedEmail}.`);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "We could not send the verification code.");
    } finally {
      setBusy("");
    }
  };
  const submit = async (event: FormEvent) => {
    event.preventDefault();
    stopRestoring();
    const normalizedEmail = validEmail();
    if (!normalizedEmail) return;
    if (mode === "login") {
      setBusy("login"); setMessage("");
      try { await authClient.loginGlobal({ email: normalizedEmail, password }); enter(); }
      catch (error) { setMessage(error instanceof Error ? error.message : "Sign-in failed. Please try again."); }
      finally { setBusy(""); }
      return;
    }
    if (!challengeId) { await requestCode(); return; }
    if (password !== confirmPassword) { setMessage("Passwords do not match."); return; }
    setBusy("complete"); setMessage("");
    try { await authClient.completeGlobalPasswordFlow({ mode, email: normalizedEmail, challengeId, code, password }); enter(); }
    catch (error) { setMessage(error instanceof Error ? error.message : "We could not complete this request."); }
    finally { setBusy(""); }
  };
  const heading = mode === "login" ? "Sign in to OfferSteady" : mode === "registration" ? "Create your account" : mode === "password_setup" ? "Set a password" : "Reset your password";
  const action = mode === "login" ? (busy === "login" ? "Signing in..." : "Sign in") : !challengeId ? (busy === "send" ? "Sending..." : "Send verification code") : busy === "complete" ? "Saving..." : mode === "registration" ? "Create account" : mode === "password_setup" ? "Set password" : "Reset password";
  return <main className="center-page"><section className="login-card"><Logo /><span className="prototype-badge">Global account</span><h1>{heading}</h1><p>{mode === "login" ? "Use your email and password to access your workspace." : "We will verify your email before saving a new password."}</p><form onFocusCapture={stopRestoring} className="sms-login-form" onSubmit={submit}><label><span>Email address</span><input value={email} onChange={event => { setEmail(event.target.value); if (challengeId) { setChallengeId(""); setCode(""); } }} inputMode="email" autoComplete="email" placeholder="you@example.com" /></label>{mode === "login" ? <label><span>Password</span><input type="password" value={password} onChange={event => setPassword(event.target.value)} autoComplete="current-password" /></label> : challengeId ? <><label><span>Verification code</span><input value={code} onChange={event => setCode(event.target.value.replace(/\D/g, "").slice(0, 8))} inputMode="numeric" autoComplete="one-time-code" placeholder="Enter your code" /></label><label><span>New password</span><input type="password" value={password} onChange={event => setPassword(event.target.value)} autoComplete="new-password" aria-describedby="password-guidance" /></label><label><span>Confirm password</span><input type="password" value={confirmPassword} onChange={event => setConfirmPassword(event.target.value)} autoComplete="new-password" /></label><small id="password-guidance">Use at least 15 characters. Password managers and pasted passwords are supported.</small></> : null}<div className="sms-actions"><button className="button primary large full" type="submit" disabled={Boolean(busy)}>{action}</button>{mode !== "login" && challengeId ? <button className="button ghost full" type="button" disabled={cooldown > 0 || Boolean(busy)} onClick={() => { void requestCode(); }}>{cooldown > 0 ? `Resend in ${cooldown}s` : "Resend code"}</button> : null}</div></form><div className="login-mode-actions">{mode === "login" ? <><button className="text-link" type="button" onClick={() => resetMode("registration")}>Create account</button><button className="text-link" type="button" onClick={() => resetMode("password_reset")}>Forgot password?</button><button className="text-link" type="button" onClick={() => resetMode("password_setup")}>Existing code-login user? Set a password</button></> : <button className="text-link" type="button" onClick={() => resetMode("login")}>Back to sign in</button>}</div>{message ? <p className="login-message" role="status">{message}</p> : null}<Link className="text-link login-back" to={routes.landing}>Back to home</Link><small className="login-legal-copy">By continuing, you agree to our <Link to={routes.terms}>Terms of Service</Link> and <Link to={routes.privacy}>Privacy Policy</Link>. Never share your password or verification code.</small></section></main>;
}
