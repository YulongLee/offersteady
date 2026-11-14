import "./window-api";
import "./online-shell.css";
import type { FloatingWindowState } from "./window-api";

const transparency = document.querySelector<HTMLInputElement>("#transparency")!;
const transparencyValue = document.querySelector<HTMLOutputElement>("#transparency-value")!;
const retry = document.querySelector<HTMLButtonElement>("#retry")!;
const tuckAway = document.querySelector<HTMLButtonElement>("#tuck-away")!;
const title = document.querySelector<HTMLElement>("#status-title")!;
const detail = document.querySelector<HTMLElement>("#status-detail")!;
const protection = document.querySelector<HTMLElement>("#protection")!;
const host = document.querySelector<HTMLElement>("#host")!;
const buildLabel = document.querySelector<HTMLElement>("#build-label")!;

const protectionLabels: Record<FloatingWindowState["protection"], string> = {
  requested: "已请求窗口捕获保护 · 以接收端为准",
  unavailable: "窗口捕获保护不可用 · 整屏共享可能显示浮窗",
  unsupported: "整屏共享可能显示浮窗",
};

function render(state: FloatingWindowState) {
  buildLabel.hidden = state.productionBuild;
  transparency.value = String(state.transparency);
  transparencyValue.value = `${state.transparency}%`;
  transparency.disabled = false;
  host.textContent = state.host;
  tuckAway.hidden = !state.canTuckAway;
  protection.textContent = protectionLabels[state.protection];
  const failed = state.status === "failed";
  title.textContent = failed ? "暂时无法打开面试稳" : "正在连接面试稳";
  detail.textContent = failed ? "请检查网络后重新连接。" : "登录和面试将在此窗口打开。";
  retry.hidden = !failed;
}

const unsubscribe = window.floatingPreview.onStatus(render);
window.addEventListener("pagehide", unsubscribe, { once: true });
void window.floatingPreview.state().then(render).catch(() => {
  title.textContent = "暂时无法读取浮窗状态";
});

transparency.addEventListener("input", () => {
  transparencyValue.value = `${transparency.value}%`;
});

transparency.addEventListener("change", async () => {
  const percentage = transparency.valueAsNumber;
  transparency.disabled = true;
  try {
    render(await window.floatingPreview.setTransparency(percentage));
  } catch {
    const state = await window.floatingPreview.state().catch(() => undefined);
    if (state) render(state);
    protection.textContent = "调整透明度失败，请重试";
    transparency.disabled = false;
  }
});

retry.addEventListener("click", () => {
  void window.floatingPreview.retry().catch(() => {
    detail.textContent = "重新连接失败，请关闭浮窗后再试。";
  });
});

tuckAway.addEventListener("click", () => {
  void window.floatingPreview.tuckAway().catch(() => {
    protection.textContent = "未能收起浮窗，请重试";
  });
});
