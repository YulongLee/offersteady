## 1. Content-based quote foundation

- [x] 1.1 Add a deterministic normalized-Markdown Token estimator and regression tests proving binary container bytes are excluded.
- [x] 1.2 Add parser support for creating and loading the normalized pre-quote artifact without invoking the binary parser twice.
- [x] 1.3 Add billing quote lookup and validation that binds user, quote ID, and document version.

## 2. Backend two-stage upload protocol

- [x] 2.1 Add knowledge-upload quote request/response schemas and a pre-quote API that parses the confirmed upload before creating a quote.
- [x] 2.2 Require the matching service quote when confirming a new Web upload, then reserve and submit indexing without recalculating from raw file size.
- [x] 2.3 Replace retry raw-byte pricing with normalized-content pricing and preserve release/settlement idempotency.
- [x] 2.4 Add backend regression coverage for equivalent PDF/MD content, empty content, mismatched quotes, cached parse reuse, and retry pricing.

## 3. Web quote experience

- [x] 3.1 Extend protocol and the material upload adapter with prepare-quote and confirm-index steps.
- [x] 3.2 Update the knowledge upload dialog to show server parsing state and only enable confirmation after the final service quote is visible.
- [x] 3.3 Add Web tests proving PDF size is never shown as Token usage and the confirmed request carries the matching quote ID.

## 4. Verification and documentation

- [x] 4.1 Update the commercial material RAG documentation with the content-based two-stage quote flow.
- [x] 4.2 Run focused backend and Web tests after each layer, then run full backend tests, Web tests, Web build, and strict OpenSpec validation.
