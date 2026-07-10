const candidateUrls = [
  { url: "http://127.0.0.1:4173", source: "preview" },
  { url: "http://127.0.0.1:5173", source: "dev" },
];

const normalizeUrl = (value) => value ? value.replace(/\/+$/, "") : value;

export async function probeUrl(url) {
  try {
    const response = await fetch(url, { redirect: "follow" });
    const text = await response.text();
    return {
      url,
      ok: response.ok && /<div id="root"><\/div>|<div id="root">/i.test(text),
      status: response.status,
      reason: response.ok ? null : `HTTP ${response.status}`,
    };
  } catch (error) {
    return {
      url,
      ok: false,
      status: null,
      reason: error instanceof Error ? error.message : String(error),
    };
  }
}

export async function resolveLocalWebUrl(preferredUrl = process.env.OFFERSTEADY_REVIEW_URL) {
  const normalizedPreferred = normalizeUrl(preferredUrl);
  const queue = normalizedPreferred
    ? [{ url: normalizedPreferred, source: "env" }, ...candidateUrls.filter(item => item.url !== normalizedPreferred)]
    : candidateUrls;

  const results = [];
  for (const candidate of queue) {
    const result = await probeUrl(candidate.url);
    results.push({ ...candidate, ...result });
    if (result.ok) return { selected: candidate.url, selectedSource: candidate.source, results };
  }
  return { selected: null, selectedSource: null, results };
}
