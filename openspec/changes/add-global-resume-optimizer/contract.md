# Global Resume Optimizer contract v1

Root approved this contract after complete context review and strict OpenSpec validation on 2026-10-17. This contract records the final user decision: **Global uses valid paid time membership only; no points**. It supersedes earlier draft references to 100-point charging. Root/export owner and backend owner will implement in `/Users/liyulong/.codex/worktrees/global-resume-optimizer/offersteady`, based on the freshly bound actual Global runtime.

## Scope and policy

- Prefix: `/api/v1/resume-optimizer`. Every endpoint requires a current authenticated Global account. No explicit client `userId` is accepted; owner comes from authentication.
- Dedicated deployment flag `global_resume_optimizer_enabled`, default false. Chinese edition never enables work. Disabled capability is visible as `enabled:false`; all other operations return unavailable. Existing Global commerce, mock, minutes, wallet and interview rules do not change.
- Valid time member: authoritative `global_commerce_entitlements` joined to its purchased `global_commerce_plan_versions` by offer/version, status active, starts <= now, ends > now, plan billing mode != free and duration_days >= 1. Active one-day, weekly, monthly and other time plans all qualify; free grants, expired/revoked/future and indefinite free plans do not. No >=7-day practice threshold.
- One job allowance per UTC creation day. Reserve on accepted creation, settle on completed delivery; failed or cancelled unfinished work releases its creation-day reservation exactly once. A late prior-day release never credits the new day. Completed task deletion does not grant a second successful use. Replays, editing, downloading and save-as never reserve again.
- Non-member: HTTP 403 `resume_optimizer_membership_required` with English upgrade guidance. Used/reserved daily allowance: HTTP 429 `resume_optimizer_daily_limit`, wait until 00:00 UTC. No points balance, charge, credit or new wallet.
- One queued/running job per owner; at most 8 unfinished jobs globally, one running provider request globally. Fixed independent runner/claim path, no interview executor reuse. Provider timeout 90 s; queued jobs have a 15-minute admission lifetime; stale running lease fails and releases, never automatic model replay. Retry creates a new idempotency key through normal creation.

## Common responses and errors

All JSON uses existing `ApiEnvelope<T>` with aliases `success,data,error,requestId,meta`. Dates are integer Unix milliseconds; `quotaDay` is `YYYY-MM-DD`, UTC. Error envelope uses existing DomainRequestError handler: client reads `error.details.errorCode`; response messages are safe English. All personal JSON and attachments use `Cache-Control: private, no-store` and no raw input/provider messages in logs.

Expected codes: `resume_optimizer_disabled` (404), `resume_optimizer_membership_required` (403), `resume_optimizer_daily_limit` (429), `resume_optimizer_busy` (429), `resume_optimizer_not_found` (404, including foreign/deleted), `resume_optimizer_source_unavailable` (409), `resume_optimizer_idempotency_conflict` (409), `resume_optimizer_revision_conflict` (409), `resume_optimizer_not_completed` (409), `resume_optimizer_invalid_draft` (422), `resume_optimizer_provider_unconfigured` (503). Failed jobs carry a fixed `errorCode` and fixed English `errorMessage`, not raw exceptions.

## Endpoints

### GET `/capabilities`

`data`:

```json
{
  "enabled": true,
  "eligible": true,
  "dailyLimit": 1,
  "dailyRemaining": 1,
  "quotaDay": "2026-10-17",
  "timezone": "UTC",
  "resetAtMs": 1792281600000,
  "memberRequired": true,
  "exhausted": false,
  "activeJobId": null,
  "limits": {"resumeCharacters":40000,"jdCharacters":12000,"targetRoleCharacters":120,"draftCharacters":60000},
  "exports": ["docx","pdf"]
}
```

`enabled` also requires a configured existing Global text model. `eligible` reflects authoritative membership, not daily availability. No allowance is reserved here. Disabled response reports limits and `enabled:false` without constructing a model client/runner.

### POST `/jobs`

Request:

```json
{
  "idempotencyKey":"client-random-uuid",
  "sourceDocumentId":"document-...",
  "sourceVersionId":"version-...",
  "targetRole":"Backend Engineer",
  "jdDocumentId":null,
  "jdVersionId":null,
  "jdText":"",
  "quotedQuotaDay":"2026-10-17",
  "confirmProcessing":true
}
```

Required nonempty idempotency key <=128; source IDs <=160. Target role optional trimmed <=120. Either owned ready JD document/version pair or pasted JD <=12000, never both. `confirmProcessing` must be true after UI disclosure; `quotedQuotaDay` must match the server UTC creation day or reject 409 `resume_optimizer_quote_changed` before reservation. Matching idempotent replays remain safe across midnight. Resume body <=40000 characters and artifact <=2 MiB; reject oversized source clearly without silently truncating. Inputs must be owner-matched, current exact versions, ready, not deleted; resume kind resume, JD kind job_description. Parsed normalized text is read through existing private storage keys without parser/rerank/embedding/model calls on admission. The existing MinerU normalized artifact may retain HTML tables: only this optimizer input reader uses `HTMLParser` to convert controlled `table/tr/td/th/tbody/thead/tfoot/br` markup into separated plain-text/Markdown rows and cells, decoding character entities and preserving every cell's text, numbers, dates, contact details and order. The same normalized copy is persisted as `sourceText`/JD snapshot, sent to the provider and used for literal evidence/sourceQuote matching and conservative edits. Original uploaded bytes, stored Parser artifact, material versions and session snapshots are never rewritten. Limits apply after controlled normalization; no truncation or silently dropped cells. Unsupported/malformed HTML, scripts/styles or executable/external-resource markup fails admission with a safe actionable English source-content error before allowance reservation/provider work; no script/CSS evaluation, URL fetch or unknown-content stripping is permitted. No raw file/body is accepted in this endpoint. Generic target-role review without JD marks job matching unassessed. Success returns a full `JobDetail`; matching idempotent request returns same job, differing input returns conflict, deleted key returns not found. No second queue admission or allowance is made on replay.

### GET `/jobs`

`data:{"jobs": JobSummary[]}`; newest first, at most 30 non-deleted records. No source/JD/review/draft bodies in summary.

### GET `/jobs/{jobId}`

`data:JobDetail`. Server rechecks source/JD owner/version/deletion before returning personal content. Read does not trigger provider work.

### POST `/jobs/{jobId}/cancel`

No body. `data:JobDetail`. Queued/running become cancelled and release once. Replayed cancellation is safe; completed remains completed (no refund). Active provider request is cancelled promptly where possible; state/claim prevents late completion regardless.

### DELETE `/jobs/{jobId}`

No body. `data:{"deleted":true}`. Removes all input/result/draft content; active work cancelled and allowance released once. Replayed delete by the same owner succeeds without exposing a foreign record. Completed settlement remains minimal audit metadata. Does not delete independent saved material.

### PATCH `/jobs/{jobId}/draft`

Request `{ "expectedRevision":1, "markdown":"# Name\n..." }`. Completed and current revision only; UTF-8 plain text/Markdown <=60000 chars, no NUL/control/script/HTML markup. User explicitly authored text is permitted after UI factual-review notice; AI initial review remains unchanged. `data:JobDetail`; revision increments. Empty or invalid draft rejected. Draft saves make previous save-as result revision-specific; old saved material remains independent.

### POST `/jobs/{jobId}/save-as`

Request `{ "expectedRevision":2, "confirmIndependentCopy":true, "factsConfirmed":true }`. Completed and exact saved draft only. `data:{"document":DocumentRecordResponse}`. Same job/revision replay returns same material. Document/version/object IDs generated deterministically from owner/job/revision; save-as snapshot is committed while holding the per-owner optimizer transaction and current source-row locks. Creates a distinct normal owner resume through the existing private storage/document/processing path; original resume and existing interview selection are untouched. New record initially processing_requested/queued and becomes selectable only through existing processing readiness. Any retry uses the same IDs and does not duplicate objects or parser submissions; no billing/knowledge charge. Separate copy is retained when optimization is deleted. A source/task deletion racing save-as cannot create a previously unconfirmed copy.

### GET `/jobs/{jobId}/export?format=docx|pdf&expectedRevision=2&factsConfirmed=true`

Binary response from completed current saved draft. Requires `factsConfirmed=true` after the UI factual-review notice. Must pass owner/source/revision guards before render and again before response. Unsupported formats rejected. Correct MIME and Content-Disposition UTF-8 attachment filename; private/no-store, nosniff. No public storage link or cached export object. Root-owned `app.services.resume_optimizer_export.render_resume_export(markdown: str, format: str) -> tuple[bytes, str, str]` returns bytes, MIME, filename. Export owner handles real DOCX/PDF content/fonts/pagination; module has no storage/authorization/provider side effects.

## Wire types

`JobSummary`:

```json
{
  "jobId":"resume-opt-...","status":"queued","revision":1,
  "sourceDocumentId":"document-...","sourceVersionId":"version-...",
  "sourceDisplayName":"Resume.pdf","targetRole":"Backend Engineer",
  "hasJd":false,"quotaDay":"2026-10-17","allowanceStatus":"reserved",
  "createdAtMs":0,"updatedAtMs":0,"completedAtMs":null,
  "errorCode":null,"errorMessage":null,"savedDocumentId":null,"savedVersionId":null
}
```

Status enum `queued|running|completed|failed|cancelled`; allowance enum `reserved|settled|released`. All optional fields are returned null, strings are English except original user content/name.

`JobDetail` extends summary:

```json
{
  "sourceText":"optimizer-normalized parsed resume",
  "jdText":"",
  "jdDocumentId":null,"jdVersionId":null,
  "review":null,
  "initialDraftMarkdown":null,
  "draftMarkdown":null,
  "promptVersion":"resume-optimizer-en-v1",
  "scoreVersion":"resume-reference-v1"
}
```

`review` on completed:

```json
{
  "overallScore":75,
  "roleMatchingAssessed":false,
  "dimensions":[
    {"key":"completeness","score":75,"reason":"English explanation","evidence":[{"source":"resume","quote":"exact source excerpt"}]},
    {"key":"impact","score":70,"reason":"English explanation","evidence":[{"source":"resume","quote":"exact source excerpt"}]},
    {"key":"clarity","score":80,"reason":"English explanation","evidence":[{"source":"resume","quote":"exact source excerpt"}]},
    {"key":"structure","score":75,"reason":"English explanation","evidence":[{"source":"resume","quote":"exact source excerpt"}]}
  ],
  "suggestions":[{"priority":"high","title":"Explain impact","explanation":"...","recommendation":"...","evidence":[{"source":"resume","quote":"exact excerpt"}]}],
  "missingFacts":["Add a measurable result only if you can verify it."],
  "disclaimer":"Reference evaluation under OfferSteady's resume rubric, not a hiring probability. Verify all facts before use."
}
```

With JD, add required fifth dimension `roleMatch`, with at least one real JD evidence plus resume evidence. Four or five dimensions have equal weights and overallScore is server-computed rounded arithmetic mean (no arbitrary model overall). Scores strict integers 0–100. Reasons <=600 chars; suggestions 1–12 with explanations/recommendation <=1200; missingFacts <=12, each <=600. Evidence source `resume|jd`; quotes nonempty <=600 and must occur literally in that source. Personal material is always untrusted input. English explanatory content is required; source excerpts and source-preserving draft may keep original characters.

## Provider / factual-rewrite contract

Model output contains `{dimensions,suggestions,missingFacts,edits}`; no trusted overall score or full replacement resume. `edits` is a bounded list <=24 of `{sourceQuote,replacement}`; source quote 1–2000 chars, replacement 1–2500 chars. Each quote must occur exactly once in the optimizer-normalized source resume; edits cannot overlap. Server constructs the optimized draft from that same optimizer-normalized source copy plus validated replacements so omitted experiences, contact details and unchanged sections survive.

Every replacement must preserve original numeric/date/contact/URL tokens and cannot introduce new ones; novel capitalized/acronym technical/company/education entities unsupported by original resume are rejected. JD terms alone never become candidate facts. To avoid overstating what syntax checks can prove, semantic factual fidelity remains a dedicated Prompt/eval/review boundary and user must verify the result; unsupported semantic factual additions are failures in evaluation. Missing metrics, skills, employers or degrees belong only in `missingFacts`, not in the rewritten candidate facts. No source-dependent score/suggestion without literal evidence. Invalid JSON/schema/English/evidence/length/numeric/entity output fails the job and releases the allowance; no partial successful draft is exposed. Prompt injection text is never system instructions.

Provider uses current Global `chat_qwen_model/base_url/api_key` via a separate bounded async HTTP client, no automatic request retries, max response 256 KiB and strict stop finish_reason. It does not invoke ChatService, real-time prompts, usage adapter, ASR, retrieval, embeddings or wallets. Input/provider payload/exception strings are never logged or persisted beyond explicitly needed task snapshots and validated result.

## Persistence, concurrency and deletion

Additive migration `0053_global_resume_optimizer.sql` introduces only `global_resume_optimizer_jobs`, `global_resume_optimizer_usage`, and optional save-as metadata inside the job; applies using existing checksum migration mechanism and remains compatible with old application images. No modification of old billing/material/session tables beyond an explicitly confirmed independent new resume.

Owner advisory lock serializes admission/reserve/cancel/delete/edit/save-as; global optimizer advisory lock serializes bounded capacity and running claim. Lock order is always global then owner where both are needed. Model/storage I/O never runs under a global lock or database row lock. Completion and export/save-as authorization recheck current source rows and state; completion compares running claim token/revision, never saves after cancel/delete/source change. Save-as necessarily performs bounded private object creation under owner lock only, not provider I/O or global lock. Stored inputs/results/draft clear to empty/null on task/source deletion (physical field clearing, not UI hiding); only minimal owner/job/day/status/idempotency/quota metadata retained. No export files persist.

Source deletion integration is a minimal Global-only DocumentService hook that performs the source soft-delete and all linked optimizer cancellations/content purges in the same PostgreSQL transaction when production durable storage is used. Existing deletion/cleanup jobs still run. This prevents a worker or export from observing a deleted source with retained readable derived content. In-memory tests use the same visible behavior via injected repository hook. Saved independent documents are not linked as deletion dependents. Failure retains inputs for owner-visible troubleshooting/retry until explicit deletion, but has no partial review/draft.

Startup launches runner only for enabled Global with configured model and durable repository; independent task loop owns bounded claim/poll and async cancellation. On startup/periodic cleanup stale running lease and expired queued work fail/refund without re-invocation. Shutdown cancels runner and its active generation, settles the active record as safe interrupted failure/refund under shielded cleanup. Cross-process global running claim is checked in PG; deployment must not create multiple provider workers beyond one.


## Controlled parsed-table normalization (approved implementation refinement)

MinerU may represent a resume/JD table as inert HTML in normalized Markdown. The optimizer reader alone uses Python HTMLParser to convert table/tr/td/th/thead/tbody/tfoot and br into plain text: cells retain their complete visible text/numbers/contact details, columns use ` | ` and rows use newlines. Only inert layout attributes are accepted; no scripts/styles/handlers/remote resources are executed, fetched or rendered. Unknown tags/attributes, comments/declarations, malformed/unbalanced nesting or non-whitespace table content outside a cell are rejected **before allowance reservation/model work** with HTTP 422 `resume_optimizer_source_markup_unsupported`; no fact is silently discarded. HTML entity decoding follows visible-text semantics. The original stored file and old parser pipeline are untouched.

The job sourceText/jdText, evidence quotes, model input and initial draft use this same controlled normalized copy, so citations remain literal and comparison is labelled as parsed text with tables simplified. Input length is bounded after this normalization, while original artifact bytes retain the 2 MiB limit. Wire fields/types do not change. Pasted JD follows the same safe text boundary. The template keeps content rather than original visual layout; this is disclosed in the English UI.
