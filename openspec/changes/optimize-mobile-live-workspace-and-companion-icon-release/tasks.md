## 1. Mobile workspace structure

- [x] 1.1 Add phone-only answer/conversation tab state without changing desktop workspace state
- [x] 1.2 Add compact mobile header and move low-frequency actions into an accessible more menu
- [x] 1.3 Add bottom mobile question bar wired to the existing quick-answer and screenshot handlers
- [x] 1.4 Auto-select the answer tab when an answer task starts or a new answer arrives

## 2. Responsive presentation

- [x] 2.1 Replace the phone stacked layout with independently scrollable tab panels
- [x] 2.2 Keep the mobile action bar above browser and device safe areas
- [x] 2.3 Remove the duplicate phone session footer while preserving the desktop footer

## 3. Regression coverage

- [x] 3.1 Add phone tests for default answer tab, transcript switching and state preservation
- [x] 3.2 Add phone tests for compact actions, automatic answer focus and more-menu controls
- [x] 3.3 Run web tests, typecheck and production build

## 4. Companion release

- [x] 4.1 Replace companion package and renderer icons with transparent text-free assets
- [x] 4.2 Add icon resource and packaging regression tests
- [x] 4.3 Increment the companion version and remove hard-coded old package paths
- [x] 4.4 Build and validate macOS arm64, macOS x64 and Windows x64 release artifacts
- [x] 4.5 Publish artifacts and update the backend desktop release manifest

## 5. Delivery

- [x] 5.1 Validate the OpenSpec change strictly and review scoped diffs
- [x] 5.2 Commit and push the approved files without including unrelated local changes
- [ ] 5.3 Deploy the web/backend release and verify health plus all desktop download entries
