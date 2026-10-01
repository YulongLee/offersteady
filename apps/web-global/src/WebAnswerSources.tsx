import type { AnswerProvenance } from "@offersteady/protocol";

export function WebAnswerSources({ provenance }: { provenance: AnswerProvenance }) {
  const status = provenance.webSearchStatus;
  if (!status || status === "disabled") return null;
  const sources = (provenance.webSources ?? []).filter(source => {
    try { const url = new URL(source.url); return ["https:", "http:"].includes(url.protocol) && !url.username && !url.password; }
    catch { return false; }
  });
  return <aside className="web-answer-sources">
    <p role="status">{status === "pending" ? "Web search enriches the detailed answer only. Quick answers do not wait for it."
      : status === "succeeded" ? "Detailed answer supported by public web sources. Verify the source before relying on it."
      : "Web search unavailable. The detailed answer uses the standard answer flow."}</p>
    {!!sources.length && <ul>{sources.map((source, index) => <li key={`${source.url}:${index}`}><a href={source.url} target="_blank" rel="noopener noreferrer">{source.title || source.url}</a></li>)}</ul>}
  </aside>;
}
