interface Props {
  readonly manualDraft: string;
  readonly onChange: (value: string) => void;
}

export function ManualQuestionComposer({ manualDraft, onChange }: Props) {
  return <section className="manual-question-composer" aria-label="手动问题输入">
    <div className="manual-question-head">
      <div>
        <span className="kicker">MANUAL QUESTION</span>
        <h3>手动输入问题</h3>
      </div>
      <small>输入后在右侧使用快答</small>
    </div>
    <label>
      <span className="sr-only">手动输入面试官的问题</span>
      <textarea
        aria-label="手动输入面试官的问题"
        value={manualDraft}
        onChange={event => onChange(event.target.value)}
        placeholder="输入面试官的问题"
        rows={2}
      />
    </label>
  </section>;
}
