## Why

The live interview workspace currently stacks below 1051px. Narrowing a desktop browser therefore removes both the familiar left/right layout and its divider even though the window still has enough room for compact columns.

## What Changes

- Keep conversation and answer side by side down to 721px.
- Keep the draggable and keyboard-accessible divider in compact desktop windows.
- Use smaller readable panel minimums below 900px.
- Reserve the stacked layout for phone viewports at 720px and below.
- Preserve all existing interview, audio, answer, and screenshot behavior.

## Capabilities

### Modified Capabilities

- `resizable-live-interview-workspace`: distinguish compact desktop windows from phone layouts.

## Impact

- Affected code: live workspace breakpoint detection, split bounds, responsive CSS, and focused live tests.
- APIs and persistence: unchanged.
