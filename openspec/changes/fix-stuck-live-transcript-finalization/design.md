## Context

The live pipeline publishes incremental transcript revisions keyed by source and segment. Automatic answers are triggered only by final system-audio transcripts. Production trace evidence captured an ordering where a system partial was visible, a microphone echo finalized first, and the later system final was discarded by cross-channel deduplication. The stored system partial therefore remained non-final forever and the answer trigger never ran.

The fix must preserve dual-channel capture, the current ASR provider, bounded Redis runtime state, and the rule that candidate speech never automatically triggers an answer.

## Goals / Non-Goals

**Goals:**

- Ensure a system-audio final is authoritative over a near-simultaneous microphone duplicate.
- Ensure every received final frame closes any existing partial for the same segment, including suppressed finals.
- Prevent an abandoned partial from visually claiming to be actively transcribing forever.
- Reproduce the production event ordering with synthetic regression tests.

**Non-Goals:**

- Replace the ASR model or desktop capture architecture.
- Persist raw audio or extend transcript retention.
- Automatically answer arbitrary incomplete partial text.
- Redesign the full conversation or answer workspace.

## Decisions

### Prefer system audio for cross-channel duplicates

Cross-channel deduplication will not suppress a system final merely because a matching microphone final was published first. The system channel represents the interviewer role and is the only automatic-answer source, so chronological arrival order must not override channel semantics.

Alternative considered: keep the first final regardless of source. This is the current behavior and is rejected because speaker leakage makes arrival order nondeterministic and can convert interviewer speech into candidate speech.

### Finalize the matching visible segment before returning from suppression

When a final frame is intentionally suppressed for filler, nearby duplicate, or cross-channel echo, the service will reconcile an existing partial with the same segment ID into a terminal display record. Suppression still prevents question detection, context insertion, usage duplication, and answer generation for that suppressed record.

Alternative considered: delete the partial. This avoids a stuck row but causes visible text to disappear and makes the transcript jump. Terminal reconciliation preserves what the user already saw while clearly ending the active state.

### Treat stale partial presentation as abandoned, not final

The web conversation panel will stop animating and replace “transcribing” with “recognition incomplete” once a non-final row has received no revision for a bounded interval. It will not reinterpret that text as provider-final or trigger billing. The authoritative fix remains backend final reconciliation; this UI guard handles transport loss and provider-final absence.

Alternative considered: automatically promote stale partials to final and answer them. This is rejected because an incomplete question could generate an incorrect, billable answer.

## Risks / Trade-offs

- [A microphone echo may remain visible until the system final arrives] → Keep the change focused on correctness; regression tests verify that the system final still triggers one answer.
- [A stale but legitimate long pause may be labeled incomplete] → Base the guard on time since the latest published revision and use a conservative timeout.
- [Suppressed-final reconciliation could accidentally trigger business behavior] → Persist it through a dedicated helper that emits only a terminal transcript update and bypasses context, question detection, and billing.

## Migration Plan

1. Deploy backend behavior and regression tests first; no data migration is required.
2. Deploy the web stale-partial presentation guard.
3. Verify a synthetic echo ordering and a normal system-only question end to end.
4. Roll back application containers if regressions appear; stored transcript schema and public API remain compatible.

## Open Questions

None.
