## 1. Shared upload contracts and configuration

- [x] 1.1 Define a canonical material-upload format registry shared by frontend and backend for `pdf/docx/doc/txt/md`
- [x] 1.2 Add backend configuration fields for Aliyun OSS bucket, endpoint, region, key prefix and upload-intent expiry
- [x] 1.3 Extend shared protocol/domain types with upload intent, upload completion payloads and processing states

## 2. Backend upload foundation

- [x] 2.1 Expand the storage port from placeholder URI reservation to explicit upload-intent, object-confirmation and delete capabilities
- [x] 2.2 Implement an Aliyun OSS storage adapter that signs short-lived upload parameters without exposing long-lived secrets to clients
- [x] 2.3 Add backend schemas and validation helpers for material kind, filename, extension, MIME type and upload method
- [x] 2.4 Introduce a shared material-ingestion service that creates upload intents and registers uploaded material sources

## 3. Material APIs and status lifecycle

- [x] 3.1 Replace the placeholder resume upload endpoint with file-upload intent and completion APIs
- [x] 3.2 Replace the placeholder job-description upload endpoint with file-upload intent, completion APIs and a separate pasted-text creation API
- [x] 3.3 Replace the placeholder knowledge upload flow with file-upload intent, completion APIs and collection/source registration
- [x] 3.4 Ensure uploaded materials enter explicit non-ready processing states and are never exposed as interview-ready before processing succeeds

## 4. Frontend integration without changing the prototype flow

- [x] 4.1 Add a material-upload API adapter in `apps/web` that supports request-intent → direct upload → complete-confirmation flow
- [x] 4.2 Reuse the shared format registry to drive file pickers, client-side validation and user-facing error copy in the library page
- [x] 4.3 Integrate resume, JD and knowledge upload dialogs with the new API flow while preserving current page structure and interaction model
- [x] 4.4 Keep JD text paste as a separate submission path that reuses the same material status presentation

## 5. Verification and safeguards

- [x] 5.1 Add backend tests for supported-format validation, expired/invalid upload intents and material registration ownership checks
- [x] 5.2 Add frontend tests for successful upload initiation, unsupported-file rejection and non-ready material status rendering
- [x] 5.3 Verify that preparation and selection flows still treat only `ready` materials as selectable after the upload changes
- [x] 5.4 Document local setup assumptions, synthetic test data requirements and the OSS-related environment variables for this feature
- [x] 5.5 Run `openspec validate implement-material-library-upload-with-oss --strict`
