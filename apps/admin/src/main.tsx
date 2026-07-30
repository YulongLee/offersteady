import { Component, StrictMode, type ErrorInfo, type ReactNode } from "react";
import { createRoot } from "react-dom/client";

import { App } from "./App";
import "./styles.css";

class AdminErrorBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false };

  static getDerivedStateFromError() {
    return { failed: true };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("admin_ui_render_failed", error, info.componentStack);
  }

  render() {
    if (this.state.failed) {
      return (
        <main className="fatal-shell">
          <section className="fatal-card">
            <p className="eyebrow">RECOVERABLE ERROR</p>
            <h1>当前页面加载失败</h1>
            <p>后台没有修改任何业务数据。请重新加载页面，系统会重新读取生产服务。</p>
            <button type="button" onClick={() => window.location.reload()}>重新加载后台</button>
          </section>
        </main>
      );
    }
    return this.props.children;
  }
}

createRoot(document.getElementById("root")!).render(
  <StrictMode><AdminErrorBoundary><App /></AdminErrorBoundary></StrictMode>,
);
