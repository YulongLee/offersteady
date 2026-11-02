import { useEffect, useState } from "react";

export function HideWindowButton() {
  const [shortcut, setShortcut] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    let current = true;
    void window.offersteady?.getWindowVisibility?.().then(value => {
      if (current) setShortcut(value.restoreShortcut);
    }).catch(() => undefined);
    return () => { current = false; };
  }, []);
  return <button type="button" className="hide-companion-button" aria-label="隐藏伴随助手"
    title={shortcut ? "点击原菜单栏／托盘图标位置或按 ⌘/Ctrl + Shift + H 恢复" : "点击原菜单栏／托盘图标位置恢复窗口"}
    onClick={() => {
      setFailed(false);
      void window.offersteady?.hideWindow?.().then(value => {
        if (!value.hidden) setFailed(true);
      }).catch(() => setFailed(true));
    }}>{failed ? "重试隐藏" : "隐藏"}</button>;
}
