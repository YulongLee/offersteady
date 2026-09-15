export function isGlobalAppPath(pathname: string): boolean {
  return /^\/app(?:\/|$)/.test(pathname);
}

export function clearAppEntryShell(): void {
  document.documentElement.removeAttribute("data-app-entry");
  document.getElementById("app-entry-shell")?.remove();
}
