## Why

Companion 1.2.3 regressed from the previously approved transparent RGBA icon to an opaque white-canvas asset, and its connection action deep-links into the bound interview instead of the Web workspace. Physical ARM testing additionally confirms avoidable live-start polling delay, long system-audio turns, sticky recovered transport errors, and a Web “重新诊断” action that does not perform a diagnosis.

## What Changes

- Release the next desktop patch as version 1.2.4 for macOS arm64, macOS Intel x64, and Windows x64.
- Restore the text-free transparent-corner shield/microphone/check icon for packaging and the in-app brand mark.
- Regenerate macOS `.icns` and Windows `.ico` assets from the approved transparent source and add regressions that require a real alpha channel.
- Replace the bound-state “进入当前面试” action with a stable website/workspace action that always opens the configured `/app` workspace instead of `/app/interviews/{sessionId}/live`.
- Reduce companion binding-state detection from a ten-second idle poll boundary and avoid blocking interview entry on the full ASR prewarm wait.
- Bound system-audio turns more aggressively while retaining overlap-safe incremental transcription, and measure user-perceived stop latency from the last meaningful speech sample.
- Clear recovered transport errors when healthy frames/ACKs resume so stale `publisher-transport-missing` or `audio-gap` values do not poison later health reports.
- Refresh runtime health after device-status changes and make “重新诊断” fetch authoritative runtime state instead of changing only local UI state.
- Preserve device identity, screenshot behavior, layout, signing identity, production endpoints, privacy behavior, and protocol compatibility.
- Do not change the public homepage footer action or automatically start, resume, end, or switch an interview.

## Capabilities

### New Capabilities

- `companion-release-1-2-4`: Defines the cross-platform 1.2.4 icon identity and safe Web-workspace navigation behavior.

### Modified Capabilities


## Impact

- Desktop renderer: connection action label/target, in-app icon asset, binding polling, endpointing, and recovered health state.
- Web/Backend: runtime health refresh, diagnosis behavior, live-entry/prewarm boundary, and user-perceived endpointing telemetry.
- Desktop packaging: shared source icon, generated macOS/Windows icon containers, package version, artifact metadata, and icon regression tests.
- Distribution: new macOS arm64, macOS Intel x64, and Windows x64 artifacts and release manifest entries.
- No database schema, prompt, raw-audio persistence, transcript persistence, screenshot persistence, or personal-data behavior changes.
