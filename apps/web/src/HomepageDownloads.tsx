import type { DesktopReleaseManifest } from "@offersteady/protocol";
import { AppleLogoIcon, WindowsLogoIcon, DownloadSimpleIcon, CaretDownIcon } from "@phosphor-icons/react";
import { downloadableRelease } from "./platform";

export function HomepageDownloads({ manifest }: { readonly manifest: DesktopReleaseManifest }) {
  const available = manifest.entries.filter(downloadableRelease);
  const windows = available.find(entry => entry.platform === "windows");
  const macs = available.filter(entry => entry.platform === "macos");
  return <section className="cn-hero-downloads" aria-label="下载电脑助手">
    {windows ? <a className="cn-download-button" href={windows.downloadUrl} download><WindowsLogoIcon size={20} aria-hidden="true" />Windows<DownloadSimpleIcon size={16} aria-hidden="true" /></a> : <button className="cn-download-button" disabled>Windows 暂不可用</button>}
    {macs.length ? <details className="cn-mac-download" onKeyDown={event => { if (event.key === "Escape") { event.currentTarget.open = false; event.currentTarget.querySelector("summary")?.focus(); } }}>
      <summary className="cn-download-button"><AppleLogoIcon size={20} aria-hidden="true" />macOS<CaretDownIcon size={16} aria-hidden="true" /></summary>
      <div className="cn-mac-options">{macs.map(entry => <a key={entry.id} href={entry.downloadUrl} download>{entry.architecture === "arm64" ? "Apple Silicon" : entry.architecture === "x64" ? "Intel" : "通用版"}<DownloadSimpleIcon size={16} aria-hidden="true" /></a>)}</div>
    </details> : <button className="cn-download-button" disabled>macOS 暂不可用</button>}
  </section>;
}
