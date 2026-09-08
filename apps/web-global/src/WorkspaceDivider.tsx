import { useEffect, useRef, type KeyboardEvent, type PointerEvent, type RefObject } from "react";
import { DEFAULT_SPLIT_RATIO, clampSplitRatio, type SplitRatioBounds } from "./live-workspace";

interface Props {
  readonly containerRef: RefObject<HTMLDivElement | null>;
  readonly ratio: number;
  readonly bounds: SplitRatioBounds;
  readonly onChange: (ratio: number) => void;
}

export function WorkspaceDivider({ containerRef, ratio, bounds, onChange }: Props) {
  const activePointer = useRef<number | null>(null);
  const frame = useRef<number | null>(null);
  const pendingRatio = useRef(ratio);

  useEffect(() => () => { if (frame.current !== null) cancelAnimationFrame(frame.current); }, []);

  const schedule = (next: number) => {
    pendingRatio.current = clampSplitRatio(next, bounds);
    if (frame.current !== null) return;
    frame.current = requestAnimationFrame(() => { frame.current = null; onChange(pendingRatio.current); });
  };
  const updateFromPointer = (event: PointerEvent<HTMLDivElement>) => {
    if (activePointer.current !== event.pointerId) return;
    const rect = containerRef.current?.getBoundingClientRect();
    if (!rect?.width) return;
    schedule((event.clientX - rect.left) / rect.width * 100);
  };
  const endPointer = (event: PointerEvent<HTMLDivElement>) => {
    if (activePointer.current !== event.pointerId) return;
    activePointer.current = null;
    if (event.currentTarget.hasPointerCapture?.(event.pointerId)) event.currentTarget.releasePointerCapture(event.pointerId);
  };
  const onKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    const step = event.shiftKey ? 10 : 2;
    const key = event.key || event.code || ({ 13: "Enter", 35: "End", 36: "Home", 37: "ArrowLeft", 39: "ArrowRight" } as Record<number, string>)[event.keyCode] || "";
    let next: number | null = null;
    if (key === "ArrowLeft") next = ratio - step;
    if (key === "ArrowRight") next = ratio + step;
    if (key === "Home") next = bounds.min;
    if (key === "End") next = bounds.max;
    if (key === "Enter") next = DEFAULT_SPLIT_RATIO;
    if (next === null) return;
    event.preventDefault();
    onChange(clampSplitRatio(next, bounds));
  };

  return <div className="workspace-divider" role="separator" aria-label="调整实时对话与回答宽度" aria-orientation="vertical" aria-valuemin={Math.round(bounds.min)} aria-valuemax={Math.round(bounds.max)} aria-valuenow={Math.round(ratio)} tabIndex={0} title="拖动或使用左右方向键调整；回车恢复默认" onKeyDownCapture={onKeyDown} onPointerDown={event => { activePointer.current = event.pointerId; event.currentTarget.setPointerCapture?.(event.pointerId); }} onPointerMove={updateFromPointer} onPointerUp={endPointer} onPointerCancel={endPointer} onDoubleClick={() => onChange(clampSplitRatio(DEFAULT_SPLIT_RATIO, bounds))}><span /></div>;
}
