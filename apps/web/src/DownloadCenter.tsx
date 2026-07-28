import { useMemo, useState } from "react";
import type { DesktopReleaseManifest } from "@offersteady/protocol";
import { downloadableRelease, recommendedRelease } from "./platform";
import { Link } from "react-router-dom";
import { routes } from "./routes";

export function DownloadCenter({ manifest }: { readonly manifest: DesktopReleaseManifest }) {
  const recommendation = useMemo(() => recommendedRelease(manifest, navigator.userAgent), [manifest]);
  const [selectedId, setSelectedId] = useState(recommendation?.id ?? manifest.entries[0]?.id ?? "");
  const selected = manifest.entries.find(entry => entry.id === selectedId);
  const size = (bytes: number) => `${Math.round(bytes / 1024 / 1024)} MB`;
  const localInstructions = selected?.platform === "windows"
    ? "当前为 Windows x64 未签名安装测试版；双击安装程序，若 SmartScreen 提示未知发布者，请核对 SHA-256 后选择“更多信息 → 仍要运行”。安装后可从桌面或开始菜单启动。"
    : `当前为 macOS ${selected?.architecture === "arm64" ? "Apple Silicon" : "Intel"} ad-hoc 测试版；下载后解压，若 macOS 提示无法验证开发者，请右键 App 选择“打开”。`;
  return <section className="panel download-center"><div className="panel-heading"><div><h2>下载电脑伴随程序</h2><p>支持 macOS Apple Silicon、macOS Intel 与 Windows 10/11 x64。</p></div><Link to={`${routes.guide}#desktop`}>安装说明</Link></div><div className="download-grid">{manifest.entries.map(entry => { const available = downloadableRelease(entry); const local = entry.signingStatus === "local-development"; return <button key={entry.id} className={`download-choice ${selectedId === entry.id ? "selected" : ""}`} onClick={() => setSelectedId(entry.id)}><span className="platform-mark">{entry.platform === "macos" ? "⌘" : "⊞"}</span><strong>{entry.displayName}</strong><small>{entry.architecture} · {entry.minimumOs}</small>{recommendation?.id === entry.id ? <b>推荐</b> : null}<i>{local ? (available ? "✓ 测试版可下载" : "测试版待发布") : available ? "✓ 已验证" : "签名验证中"}</i></button>; })}</div>{selected ? <div className="release-detail"><div><strong>{selected.displayName} · {selected.version}</strong><span>{size(selected.fileSizeBytes)} · SHA-256 {selected.sha256.slice(0, 10)}…</span><span>麦克风：{selected.capabilities.microphone ? "支持" : "不可用"} · 系统音频：{selected.capabilities.systemAudio ? "支持" : "不可用"}</span>{selected.signingStatus === "local-development" ? <span>{localInstructions}</span> : null}{selected.buildCommand && !downloadableRelease(selected) ? <span>生成命令：{selected.buildCommand}</span> : null}</div>{downloadableRelease(selected) ? <a className="button primary" href={selected.downloadUrl ?? selected.localPath} download>{selected.platform === "windows" ? "下载 Windows 安装程序" : selected.signingStatus === "local-development" ? "下载 macOS 测试版" : "下载安装包"}</a> : <button className="button ghost" disabled>{selected.signingStatus === "local-development" ? "测试版待发布" : "完成签名后开放"}</button>}</div> : null}<details className="install-help"><summary>如何选择版本？</summary><p>Mac 在“关于本机”中查看芯片：Apple M 系列选择 arm64，Intel 处理器选择 x64；Windows 10/11 常见 Intel 或 AMD 电脑选择 Windows x64。</p></details></section>;
}
