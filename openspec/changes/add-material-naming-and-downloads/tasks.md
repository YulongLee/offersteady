## 1. Document service behavior

- [x] 1.1 Add duplicate-name generation and stable historical-name disambiguation with backend regression tests
- [x] 1.2 Add owner-scoped persistent material rename API with validation and authorization tests
- [x] 1.3 Add owner-scoped original-file download API with filename, content-type, deleted-file, missing-object, and authorization tests

## 2. Web material management

- [x] 2.1 Extend the protocol and material adapter with rename and authenticated Blob download operations
- [x] 2.2 Connect persistent rename and download controls for resume, JD, and knowledge materials in the library page
- [x] 2.3 Add a download control to interview-preparation material rows without changing their selected state

## 3. Verification and documentation

- [x] 3.1 Add web regression tests for duplicate labels, persistent rename, download, and selection isolation
- [x] 3.2 Update material documentation with naming and download privacy behavior
- [x] 3.3 Run focused tests, full backend/web/protocol tests, production build, and strict OpenSpec validation
