## Decisions

1. Keep final transcript-render acknowledgements and one non-final sample per five-second session window. This preserves completion and representative rendering latency without making the browser wait for telemetry.
2. Cache only a successful transcript-render session ownership check for 60 seconds by default. Answer and screenshot acknowledgements retain the existing full ownership lookup.
3. Keep the cache process-local, bounded to 4096 sessions and cleared on process restart. It is diagnostic authorization state, not a source of truth for session lifecycle.
4. Downgrade the per-ack log event to DEBUG. Aggregate request metrics and the new cache counters remain available to operations.

## Non-Goals

- No change to ASR framing, answer prompts, provider selection, billing, session state or desktop companion protocol.
- No change to the authoritative session repository or persisted interview history.
