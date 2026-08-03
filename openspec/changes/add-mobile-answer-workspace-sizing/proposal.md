## Why

The phone layout places conversation, manual input, answer, and actions in one vertical flow, but the answer workspace has no useful minimum height or size control. Long questions and answers therefore show too little content at once.

## What Changes

- Give the mobile answer workspace a larger default visible height.
- Add a mobile-only control to expand the answer workspace and restore its default height.
- Keep answer history, streaming state, and content mounted while the size changes.
- Leave desktop split resizing unchanged.

## Capabilities

### Modified Capabilities

- `resizable-live-interview-workspace`: add a phone-specific answer-height control.

## Impact

- Affected code: `AnswerWorkspace`, mobile live-workspace CSS, and focused live tests.
- APIs, persistence, audio, screenshots, and answer generation: unchanged.
