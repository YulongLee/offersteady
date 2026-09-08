import {fixtureAdapter, syntheticState} from '../../apps/web/src/test-state';

// Frozen synthetic English state for capture. No production account or interview data is loaded.
syntheticState.account.displayName = 'Demo User';
syntheticState.account.bindings.forEach((binding) => { binding.displayName = 'Local demo identity'; });
syntheticState.interviews[0] = {...syntheticState.interviews[0], title: 'Senior Frontend Engineer Interview', interviewLanguage: 'en-US', role: 'Senior Frontend Engineer', company: 'Example Labs', updatedAt: 'Today, 6:10 PM'};
syntheticState.interviews[1] = {...syntheticState.interviews[1], title: 'Product Engineer Practice Interview', interviewLanguage: 'en-US', role: 'Product Engineer', updatedAt: 'Yesterday, 9:30 PM'};

const sourceCopy: Record<string, [string, string]> = {
  'resume-frontend': ['Senior Frontend Engineer Resume (Synthetic)', 'Five years in frontend engineering, including a cross-platform workspace and performance work.'],
  'resume-product': ['Product Engineer Resume (Synthetic)', 'Product engineering and end-to-end delivery experience.'],
  'jd-frontend': ['Senior Frontend Engineer Job Description', 'React, TypeScript, engineering systems, and complex product delivery.'],
  'jd-product': ['Product Engineer Job Description', 'End-to-end delivery, user research, and cross-functional collaboration.'],
  'jd-old': ['Archived Frontend Job Description', 'Parsing failed and this source is not used for new guidance.'],
  'kb-performance': ['Frontend Performance Playbook', 'Metrics, diagnosis paths, and optimization reviews.'],
  'kb-microfrontend': ['Microfrontend Project Review', 'Architecture boundaries, isolation, and migration lessons.'],
  'kb-system-design': ['System Design Checklist', 'Capacity, reliability, data, and trade-off checks.'],
  'kb-product': ['Product Methods Notes', 'Disabled and excluded from this interview.'],
};
syntheticState.librarySources.forEach((source) => { const copy = sourceCopy[source.id]; if (copy) [source.displayName, source.summary] = copy; });
syntheticState.knowledgeCollections[0]!.name = 'Frontend Interview Materials';
syntheticState.knowledgeCollections[1]!.name = 'System Design';
syntheticState.knowledgeDocuments.forEach((doc) => { const copy = sourceCopy[doc.id]; if (copy) [doc.displayName, doc.safeSummary] = copy; });
syntheticState.preparation.resources = [
  {...syntheticState.preparation.resources[0]!, name: 'Candidate Resume (Synthetic).pdf', summary: 'Five years in frontend engineering; led workspace and performance improvements.'},
  {...syntheticState.preparation.resources[1]!, name: 'Senior Frontend Engineer Job Description', summary: 'Focuses on React, TypeScript, engineering systems, and complex delivery.'},
  {...syntheticState.preparation.resources[2]!, name: 'Frontend System Design Knowledge Base', summary: 'Eight synthetic notes covering performance, monitoring, and architecture trade-offs.'},
];
syntheticState.preparation.device.displayName = 'This Mac';
syntheticState.review.duration = '42 minutes';
syntheticState.review.summary = 'Guidance focused on project decisions, engineering systems, and collaboration. This review organises the session without scoring the candidate.';
syntheticState.review.title = 'Product Engineer Practice Interview';
syntheticState.review.screenshots[0]!.name = 'System Design Prompt (Synthetic).png';
syntheticState.review.transcripts[0]!.speakerLabel = 'Interviewer';
syntheticState.review.transcripts[0]!.text = 'How did you lead cross-functional collaboration?';
syntheticState.review.transcripts[1]!.speakerLabel = 'Me';
syntheticState.review.transcripts[1]!.text = 'I aligned the team on goals and delivery boundaries, then set a regular communication cadence.';

syntheticState.speaker.pendingQuestion = null;
syntheticState.speaker.transcripts = syntheticState.speaker.transcripts.slice(0, 2);
syntheticState.speaker.transcripts[0]!.text = 'Tell me about the most challenging frontend project you have led.';
syntheticState.speaker.transcripts[1]!.text = 'I will start with the context and the goal.';
syntheticState.questions = syntheticState.questions.slice(0, 1);
const q = syntheticState.questions[0]!;
q.text = 'Tell me about the most challenging frontend project you have led.';
q.advice.outline = ['I led a cross-platform workspace project focused on slow page loads and interaction latency.'];
q.advice.detail = `Simple Answer
I led a cross-platform workspace project focused on slow page loads and interaction latency.

---

Detailed Answer
**Context**
As the workspace grew, initial bundles and long lists became the main bottlenecks.

**My actions**
I traced the bottleneck, then added route splitting, lazy loading, and virtualized lists.

**Trade-offs**
I prioritized high-frequency journeys and used staged releases with monitoring to control risk.`;
q.advice.sourceTypes = ['Resume', 'Job Description', 'Knowledge Base'];
q.advice.inference = 'The role values complex product delivery, so the guidance emphasises decisions and collaboration boundaries.';
q.advice.provenance.usedSources.forEach((source, index) => {
  const copy = sourceCopy[source.sourceId];
  if (copy) source.displayName = copy[0];
  source.contextRole = index === 2 ? 'retrieved' : 'fixed';
});
q.advice.provenance.fixedSourceCount = 2;
q.advice.provenance.retrievedSourceCount = 1;

if (location.search.includes('capture=screenshot')) {
  q.text = 'Design a flash-sale system that prevents overselling under high concurrency.';
  q.input = 'screenshot';
  q.advice.detail = `Simple Answer
Layer rate limiting, atomic inventory reservation, and asynchronous order creation so stock cannot be deducted twice.

---

Detailed Answer
**Traffic control**
Rate-limit at the gateway and reject ineligible requests before they reach core services.

**Inventory consistency**
Reserve stock atomically in Redis, persist orders idempotently, and restore inventory after failures.

**Resilience**
Use a queue to absorb bursts, with monitoring and graceful degradation around the critical path.`;
  q.advice.provenance.usedSources = [];
  q.advice.provenance.fixedSourceCount = 0;
  q.advice.provenance.retrievedSourceCount = 0;
}

export const runtimeConfig = {apiBaseUrl: 'http://127.0.0.1:9', appEnvironment: 'capture'};
export const interviewAppAdapter = fixtureAdapter;
