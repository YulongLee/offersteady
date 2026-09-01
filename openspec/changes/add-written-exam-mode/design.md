## Context

OfferSteady currently models every session as an audio-capable interview. The preparation page confirms materials and binds a desktop companion; the live page then mounts realtime speech, quick/manual answers and screenshot answers. The screenshot service and desktop screenshot event stream are already independent of ASR, so the new mode can reuse those stable boundaries without cloning the vision pipeline.

The change crosses Web, FastAPI, PostgreSQL, billing and the Electron companion. The primary constraint is zero behavioral change for existing interviews. The production source and backend/Web images at `36c3310` are retained as the rollback baseline.

## Goals / Non-Goals

**Goals:**

- Add an explicit, durable `interview | written` session mode with `interview` as the compatibility default.
- Make companion connection the only mandatory written-exam preparation check.
- Keep screenshot capture and answer delivery working while proving that audio, ASR, transcript and chat paths are never started for written sessions.
- Charge 30 wallet points exactly once for successful written-exam entry, independently of each screenshot answer charge.
- Preserve single-active-session, recovery, history, privacy and rollback behavior.

**Non-Goals:**

- Changing interview-mode preparation, audio, ASR, quick answer, auto answer, materials or rates.
- Changing the screenshot model, prompt, capture protocol or screenshot-answer price.
- Building a proctoring system, exam timer, question bank, browser lock, anti-cheat behavior or hidden capture.
- Adding new mandatory written-exam settings beyond desktop connection.

## Decisions

### 1. Persist mode on the authoritative session

Add `session_mode` to the session record and API, constrained to `interview` or `written`, with a database default of `interview`. Mode becomes immutable after creation. A UI-only toggle was rejected because backend authorization, billing and desktop capture must enforce the same boundary.

### 2. Reuse the session and screenshot pipelines

Written exams use the existing session ID, desktop binding, session event stream, remote capture request, inline image delivery, vision gateway, task stream and history records. A separate written-exam service was rejected because it would duplicate mature retry, billing and privacy logic.

### 3. Auto-confirm an empty material scope

The backend creates written sessions with an explicitly confirmed empty material binding. The Web does not mount the material picker. Screenshot generation already operates from current screenshot evidence only; mode validation adds defense in depth. Treating the material set as merely unconfirmed was rejected because it confuses intentional absence with incomplete preparation.

### 4. Make runtime capability-deny authoritative

Mode checks live at backend command boundaries. Written sessions reject realtime publisher creation, frame ingestion, capture resume, quick/manual answers and auto answer. The desktop binding/snapshot payload includes mode so the Electron renderer can keep device/screenshot connectivity while skipping getUserMedia, loopback capture and publisher creation. Merely hiding controls was rejected because it would still consume resources and request unnecessary permissions.

### 5. Charge entry with an idempotent session-stable usage

Use billable kind `written_exam_entry`, rate key `writtenExamPoints=30`, and usage ID `written-exam-entry:{session_id}`. Start orchestration reserves before activation, activates the session, then settles. Insufficient balance stops activation; activation failure releases the reservation. Retries read the existing reservation/session state and never double-charge.

The 30-point entry fee always uses wallet points and is not waived by a time pass. Existing screenshot answers retain their current pass/points behavior and fee. Folding the fee into the first screenshot was rejected because users could enter without being charged, retries would be ambiguous, and session activation could not enforce balance.

### 6. Use separate top-level mode entries and a dedicated constrained workspace

The Web exposes 面试模式 and 笔试模式 as separate sidebar destinations. Each destination owns its list and creation page, and the route fixes the session mode; the interview creation page therefore remains identical to the pre-feature flow and contains no mode selector. The written workspace still reuses the same header, answer renderer, screenshot action and end-session behavior, but does not mount transcript consumers, manual/quick/auto controls or audio lifecycle effects. This keeps the two product journeys explicit while avoiding condition-heavy mutations inside the stable interview workspace.

### 7. Deploy additively with explicit rollback assets

Apply the additive database migration before new application containers. Deploy backend first, then Web and companion if its protocol changes. Old clients omit mode and remain interviews. Rollback uses Git tag and retained backend/Web images; the additive column can remain because old code ignores it.

## Risks / Trade-offs

- [A missed endpoint could start audio or charge an unsupported action] → Centralize a session-mode guard and cover every realtime/chat entrypoint with negative integration tests.
- [Start succeeds but billing settlement fails] → Keep the reservation idempotent, return a retriable start error, and reconcile only the same session-stable usage; never create a second charge.
- [Old companion does not understand mode] → Backend denies written audio regardless; require a compatible companion version for written mode or send a backward-compatible screenshot-only capability flag.
- [Two simultaneous start requests race] → Use the existing billing advisory lock plus repository conditional session transition and stable usage ID.
- [Users interpret 30 points as including screenshot answers] → Show “进入笔试 30 点；截屏回答按现有费率” before start and in billing disclosures.
- [Rollback leaves written sessions in the database] → Prior code sees additive rows but cannot safely continue them; rollout disables entry before rollback and support ends any active written sessions. Existing interview rows remain unaffected.

## Migration Plan

1. Record and push Git tag `baseline-before-written-exam-mode-20260902`; retain corresponding production backend/Web images.
2. Add the nullable-safe/defaulted `session_mode` migration and billing rate contract; verify all existing rows resolve to `interview`.
3. Deploy backend with mode-aware APIs and authorization while the old Web still creates only interviews.
4. Deploy the compatible Web and companion assets, then enable written-mode entry.
5. Verify one synthetic insufficient-balance start, one paid start, repeated start idempotency, screenshot answer and zero audio/ASR activity.
6. Roll back by restoring the recorded images and disabling the written entry; the additive migration remains in place.

## Open Questions

- None for the approved first release. Optional written-exam language or programming-language controls remain non-blocking and are not added in this change.
