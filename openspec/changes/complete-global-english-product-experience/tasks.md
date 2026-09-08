## 1. Baseline and inventory

- [x] 1.1 Record the current Global production release/image, route health, and rollback command without modifying any running service
- [x] 1.2 Inventory product-authored copy and interactive states across every supported `apps/web-global` route
- [x] 1.3 Add failing regression fixtures for current generic fallback copy, mixed-language chrome, referral requests, and representative overflow cases

## 2. Copy completeness

- [x] 2.1 Replace the category-fallback generator with an explicit product-copy catalogue that reports missing literal and source location
- [x] 2.2 Add concise context-specific English mappings for public, authentication, navigation, account, help, device, and settings surfaces
- [x] 2.3 Add concise context-specific English mappings for interview creation, preparation, live, answer, completion, and review surfaces
- [x] 2.4 Add concise context-specific English mappings for written-exam creation, preparation, live answer, completion, and review surfaces
- [x] 2.5 Add concise context-specific English mappings for material libraries, documents, uploads, processing, search, and management states
- [x] 2.6 Verify that runtime user material, transcripts, and generated answers are not rewritten by the product-copy system
- [x] 2.7 Replace dynamically composed Resume and Job Description empty-state copy with explicit English labels and add route regression coverage

## 3. Responsive feature-page correction

- [x] 3.1 Correct shared Global shell, navigation, account menu, dialogs, forms, tables, cards, and empty-state responsiveness using existing design tokens and icons
- [x] 3.2 Correct public, authentication, workbench, guide, device, and settings routes at desktop, tablet, and mobile viewport classes
- [x] 3.3 Correct interview and written-exam routes and their loading, success, empty, and error states at the supported viewport classes
- [x] 3.4 Correct material routes and all material-type/state combinations at the supported viewport classes
- [x] 3.5 Remove the domestic external User Manual entry from Global desktop and mobile navigation while retaining the in-product Product Guide

## 4. Global commerce and referral isolation

- [x] 4.1 Remove the Global referral landing route, referral navigation/presentation, persisted referral activation, and automatic referral-status requests
- [x] 4.2 Add safe handling for legacy Global invitation URLs that returns users to the normal public entry flow
- [x] 4.3 Implement a dedicated Global billing surface for credits, active entitlement, usage rules, and ledger history without domestic checkout or catalogue behavior
- [x] 4.4 Add a disabled-by-default Global commerce-provider boundary and document the deferred server-side Creem checkout/webhook contract without adding client secrets

## 5. Verification and release readiness

- [x] 5.1 Add route-level copy and state tests proving meaningful English and absence of generic fallback product copy
- [ ] 5.2 Add responsive structure checks for critical Global routes and complete a real-browser visual pass when browser access is available
- [x] 5.3 Verify that Global billing makes no referral or domestic checkout requests and that legacy invite links do not activate referrals
- [x] 5.4 Run Global copy audit, tests, typecheck, and production build; run relevant Chinese Web regression tests/build and confirm no domestic source or configuration changed
- [x] 5.5 Run strict OpenSpec validation and update Global product/deployment documentation with the verified route and commerce boundary
- [x] 5.6 After explicit deployment approval, deploy only the Global Web release, verify Global and Chinese production health, and retain the recorded rollback release
