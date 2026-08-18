## Why

The live interview path currently makes users wait for fixed silence windows and a complete synchronous model response before an automatically detected interviewer question becomes visibly answerable. Progressive subtitle animation can also lag behind transcript revisions that the backend has already published, so the experience feels slower than the underlying ASR provider.

## What Changes

- Stream automatically confirmed interviewer answers incrementally instead of waiting for the complete model response.
- Preserve the existing question detection, answer content, billing, history, cancellation, speaker roles, and page layout while moving automatic answer generation off the realtime audio worker.
- Make partial transcripts catch up to the latest backend revision without a fixed two-character animation bottleneck.
- Reduce endpoint silence waiting conservatively for system audio and microphone sources without increasing duplicate or fragmented final transcripts.
- Record and test stage-level latency from final speech activity through visible transcript and answer first chunk.
- Do not persist raw audio or introduce a new model/provider.

## Capabilities

### New Capabilities

- `low-latency-live-audio-answer-path`: Defines bounded silence finalization, immediate transcript visibility, non-blocking automatic question handling, and genuinely streamed automatic answers without changing existing interview behavior.

### Modified Capabilities

None.

## Impact

- Desktop companion speech segmentation and its regression tests.
- Backend realtime speech orchestration, chat streaming integration, task persistence, billing settlement, and SSE events.
- Web realtime transcript and answer-state reconciliation.
- AI answer streaming eval coverage and realtime performance evidence.
- No public route removal, database migration, new client secret, raw-audio persistence, or visual redesign.
