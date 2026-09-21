interface Props {
  readonly enabled: boolean;
  readonly disabled?: boolean;
  readonly mobile?: boolean;
  readonly onToggle: () => void;
}

export function WebSearchToggle({ enabled, disabled = false, mobile = false, onToggle }: Props) {
  return <div className={`live-auto-answer live-web-search-toggle${mobile ? " mobile" : ""}`} title="开启后，详细回答会结合实时网页资料；快答链路不受影响">
    <span>{mobile ? "联网" : "联网回答"}</span>
    <label className="switch-control">
      <input type="checkbox" role="switch" aria-label="联网回答" checked={enabled} disabled={disabled} onChange={onToggle} />
      <span aria-hidden="true" />
    </label>
  </div>;
}
