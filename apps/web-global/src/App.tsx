import { Component, Suspense, type ReactNode } from "react";
import { BrowserRouter, Link, Navigate, Route, Routes, useLocation } from "react-router-dom";
import type { WebAppState } from "./domain";
import { authClient } from "./auth-client";
import { DocumentTitleManager } from "./DocumentTitleManager";
import { WorkspaceApp, LoginPage, PublicReviewPage } from "./entry-routes";
import { LandingPage, PublicLayout } from "./PublicPages";
import { RouteLoadingPage } from "./PageShell";
import { publicReviewCatalogue } from "./public-review-pages";
import { routes } from "./routes";
import "./styles.css";
import "./homepage-commercial.css";

export interface AppProps { readonly initialAuthenticated?: boolean | undefined; readonly initialState?: WebAppState | undefined }

class PageLoadBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  render() {
    if (this.state.failed) return <main className="center-page"><section className="empty-state"><h2>Could not load this page</h2><p>Check your connection and reload to try again.</p><button type="button" className="button primary" onClick={() => window.location.reload()}>Reload page</button></section></main>;
    return this.props.children;
  }
}

function WorkspaceEntry(props: AppProps) {
  const location = useLocation();
  // A hint only: WorkspaceApp still restores the session before loading user data.
  const hasSession = props.initialAuthenticated ?? Boolean(authClient.readStoredSession());
  if (!hasSession) return <Navigate to={routes.login} state={{ from: location.pathname + location.search + location.hash }} replace />;
  return <WorkspaceApp {...props} />;
}

function NotFoundPage() {
  return <main className="center-page"><section className="empty-state"><span>◇</span><h2>Page not found</h2><p>Check the address, or return to your interview workspace.</p><Link className="button primary" to={routes.app}>Back to home</Link></section></main>;
}

export function AppRoutes(props: AppProps) {
  const location = useLocation();
  const authenticatedHint = props.initialAuthenticated ?? Boolean(authClient.readStoredSession());
  const boundaryKey = /^\/app(?:\/|$)/.test(location.pathname) ? "workspace" : location.pathname;
  return <PageLoadBoundary key={boundaryKey}><Suspense fallback={<RouteLoadingPage />}><Routes>
    <Route element={<PublicLayout authenticated={authenticatedHint} />}>
      <Route path={routes.landing} element={<LandingPage />} />
      <Route path={routes.login} element={<LoginPage initialAuthenticated={props.initialAuthenticated} />} />
      <Route path={routes.invite()} element={<Navigate to={routes.landing} replace />} />
      {publicReviewCatalogue.pages.map(page => <Route key={page.slug} path={`/${page.slug}`} element={<PublicReviewPage slug={page.slug} />} />)}
    </Route>
    <Route path="/billing/success" element={<Navigate to={routes.billing} replace />} />
    <Route path="/app/*" element={<WorkspaceEntry {...props} />} />
    <Route path="/error" element={<main className="center-page"><section className="empty-state"><h2>This page is temporarily unavailable</h2><Link className="button primary" to={routes.app}>Back to home</Link></section></main>} />
    <Route path="*" element={<NotFoundPage />} />
  </Routes></Suspense></PageLoadBoundary>;
}

export function App(props: AppProps) {
  return <BrowserRouter><DocumentTitleManager /><AppRoutes {...props} /></BrowserRouter>;
}
