import { AppleLogoIcon, WindowsLogoIcon, DownloadSimpleIcon, CaretDownIcon } from "@phosphor-icons/react";
import downloads from "./homepage-downloads.generated.json";

export function HomepageDownloads() {
  const windows = downloads.find(e => e.platform === "windows");
  const macs = downloads.filter(e => e.platform === "macos");
  return <section className="hero-downloads" aria-label="Download Desktop Companion">
    <div className="hero-download-actions">
      {windows ? <a className="hero-download-button" href={windows.href}><WindowsLogoIcon size={20} aria-hidden="true" />Windows<DownloadSimpleIcon size={16} aria-hidden="true" /></a> : <button className="hero-download-button" disabled>Windows unavailable</button>}
      {macs.length ? <details className="hero-mac-download"><summary className="hero-download-button"><AppleLogoIcon size={20} aria-hidden="true" />macOS<CaretDownIcon size={16} aria-hidden="true" /></summary>
        <div className="hero-mac-options">{macs.map(e => <a key={e.architecture} href={e.href}><strong>{e.architecture === "arm64" ? "Apple Silicon" : "Intel"}</strong></a>)}</div>
      </details> : <button className="hero-download-button" disabled>macOS unavailable</button>}
    </div>
  </section>;
}
