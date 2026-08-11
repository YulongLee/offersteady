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
  const localInstructions = "这是内部开发构建，不向用户提供下载。完成代码签名、安全校验和 macOS 公证后才会开放正式安装包。";
  return <section className="panel download-center"><div className="panel-heading"><div><h2>下载电脑伴随程序</h2><p>支持 macOS Apple Silicon、macOS Intel 与 Windows 10/11 x64。</p></div><Link to={`${routes.guide}#desktop`}>安装说明</Link></div><div className="download-grid">{manifest.entries.map(entry => { const available = downloadableRelease(entry); const local = entry.signingStatus === "local-development"; return <button key={entry.id} className={`download-choice ${selectedId === entry.id ? "selected" : ""}`} onClick={() => setSelectedId(entry.id)}><span className="platform-mark">{entry.platform === "macos" ? "⌘" : "⊞"}</span><strong>{entry.displayName}</strong><small>{entry.architecture} · {entry.minimumOs}</small>{recommendation?.id === entry.id ? <b>{entry.platform === "macos" ? "这台 Mac" : "这台电脑"}</b> : null}<i>{available ? "✓ 已验证" : local ? "内部构建不可下载" : "签名验证中"}</i></button>; })}</div>{selected ? <div className="release-detail"><div><strong>{selected.displayName} · {selected.version}</strong><span>{size(selected.fileSizeBytes)} · SHA-256 {selected.sha256.slice(0, 10)}…</span><span>麦克风：{selected.capabilities.microphone ? "支持" : "不可用"} · 系统音频：{selected.capabilities.systemAudio ? "支持" : "不可用"}</span>{selected.signingStatus === "local-development" ? <span>{localInstructions}</span> : null}</div>{downloadableRelease(selected) ? <a className="button primary" href={selected.downloadUrl} download>{selected.platform === "windows" ? "下载 Windows 安装程序" : "下载安装包"}</a> : <button className="button ghost" disabled>{selected.signingStatus === "local-development" ? "正式版待发布" : "完成签名后开放"}</button>}</div> : null}<details className="install-help"><summary>如何选择版本？</summary><p>Mac 在“关于本机”中查看芯片：Apple M 系列选择 arm64，Intel 处理器选择 x64；Windows 10/11 常见 Intel 或 AMD 电脑选择 Windows x64。</p></details></section>;
}
