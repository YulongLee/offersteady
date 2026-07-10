## 1. Spec Reconciliation and Catalog Model

- [x] 1.1 Reconcile the new landing hierarchy with `improve-growth-checkout-and-user-guidance`
- [x] 1.2 Replace the fixed 20-point knowledge rate in `optimize-product-experience-and-distribution`
- [x] 1.3 Reconcile long-pass knowledge allowances with `add-billing-points-and-passes` membership exclusions
- [x] 1.4 Define versioned knowledge minimum, per-1,000-Token rate and eligible-pass allowance fields
- [x] 1.5 Define quote, allowance lock, usage source and settlement protocol types
- [x] 1.6 Add protocol validation tests for catalog, quote and allowance payloads

## 2. Server Knowledge Quote and Pricing

- [x] 2.1 Add server-owned normalized-text Token counting behind a replaceable tokenizer adapter
- [x] 2.2 Implement `max(200, ceil(tokens / 1000) × 20)` using integer arithmetic
- [x] 2.3 Reject empty or unusable parsed text without creating a minimum charge
- [x] 2.4 Create expiring quotes containing Token count, units, points, source and version snapshots
- [x] 2.5 Invalidate quotes when document content, tokenizer, catalog or expiry changes
- [x] 2.6 Prevent client Token counts and point values from affecting trusted quotes
- [x] 2.7 Add boundary tests for 1, 3,000, 10,000, 10,001 and large Token counts
- [x] 2.8 Add empty-text, expired-quote, changed-content and tampered-client regression tests

## 3. Long-Pass Knowledge Allowances

- [x] 3.1 Grant zero knowledge allowances to 3-day and 7-day pass segments
- [x] 3.2 Grant two knowledge allowances when a 15-day or 30-day pass segment becomes active
- [x] 3.3 Keep queued pass allowances unavailable until their corresponding segment starts
- [x] 3.4 Expire unused allowances with their pass segment without converting them to points
- [x] 3.5 Lock one allowance before processing and consume it only after a usable index is delivered
- [x] 3.6 Release locked allowances on parsing, indexing, cancellation and timeout failures
- [x] 3.7 Fall back to the points quote after both allowances are consumed
- [x] 3.8 Keep empty collection creation free and independent from knowledge allowances
- [x] 3.9 Treat changed document content as a new version and new billable indexing usage
- [x] 3.10 Add activation, extension, expiry, success, failure and exhausted-allowance tests

## 4. Idempotent Usage, Migration and Privacy

- [x] 4.1 Use stable quote, document-version and usage identifiers for points and allowance sources
- [x] 4.2 Preserve existing reserve, settle and release semantics for point-funded indexing
- [x] 4.3 Reuse the original result for unchanged content or replayed idempotency keys
- [x] 4.4 Preserve confirmed legacy 20-point quote snapshots through catalog migration
- [x] 4.5 Apply the new formula only to quotes created under the new catalog version
- [x] 4.6 Record allowance consumption as an entitlement usage rather than a fake zero-point purchase
- [x] 4.7 Redact filenames, normalized text and knowledge excerpts from billing and cost logs
- [x] 4.8 Add concurrent reservation, duplicate callback and migration regression tests

## 5. Landing Page Value Messaging

- [x] 5.1 Replace the `CLEAR BOUNDARIES` card with the approved value-led section
- [x] 5.2 Add direct benefits for question understanding, personalized answer structure and flexible use
- [x] 5.3 Keep the value section free of guaranteed-Offer, perfect-answer and absolute-accuracy claims
- [x] 5.4 Move AI-advice, real-experience and data-control language into concise secondary trust copy
- [x] 5.5 Link the secondary trust copy to the existing privacy or usage guidance
- [x] 5.6 Add a landing price summary for “knowledge indexing from 200 points” and long-pass allowances
- [x] 5.7 Add responsive, heading-hierarchy, trust-link and marketing-claim tests

## 6. Billing and Knowledge Library UI

- [x] 6.1 Show the minimum and per-1,000-Token formula in the points consumption explanation
- [x] 6.2 Show two knowledge material allowances on 15-day and 30-day product cards only
- [x] 6.3 Show allowance activation and expiry timing for active and queued pass segments
- [x] 6.4 Add remaining allowance count and usage entries to the authenticated billing page
- [x] 6.5 Replace the knowledge upload fixed-price confirmation with a server quote state
- [x] 6.6 Show Token count, billing units, entitlement source, projected points and projected balance
- [x] 6.7 Handle quote loading, expiry, refresh, insufficient balance and tampered-response states
- [x] 6.8 Keep empty collection creation free and explain that allowances apply to indexed documents
- [x] 6.9 Show allowance release and point release truthfully after failure or cancellation
- [x] 6.10 Add billing-page and knowledge-upload integration tests for every entitlement source

## 7. Documentation, Economics and Verification

- [x] 7.1 Update the billing and knowledge-library in-app guides with formula and examples
- [x] 7.2 Update public pricing copy and FAQ without exposing implementation-only identifiers
- [x] 7.3 Add catalog unit-economics fixtures for the 200-point minimum and long-pass allowances
- [x] 7.4 Verify the new rates and allowances satisfy the configured publication margin threshold
- [x] 7.5 Verify all new fixtures contain only synthetic documents and Token counts
- [x] 7.6 Run protocol, API and Web tests, typechecks and production builds
- [x] 7.7 Run landing and knowledge flows at phone, tablet and desktop widths
- [x] 7.8 Validate this change and every reconciled active OpenSpec change in strict mode
- [x] 7.9 Review every capability scenario against the implemented behavior and recorded tests
