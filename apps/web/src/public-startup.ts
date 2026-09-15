// Only reuse trusted, server-delivered public markup; never persisted/user HTML.
export interface PublicStartupSnapshot { readonly pathname: string; readonly html: string }
export function capturePublicStartup(document: Document, pathname: string): PublicStartupSnapshot | undefined {
  if (!/^\/(?:guide|terms|privacy)?\/?$/.test(pathname)) return undefined;
  const root = document.getElementById("root");
  if (!root?.querySelector("h1")) return undefined;
  return { pathname, html: root.innerHTML };
}
