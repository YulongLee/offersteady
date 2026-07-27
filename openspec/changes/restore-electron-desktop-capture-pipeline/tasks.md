## 1. Architecture and ownership

- [x] 1.1 Change the desktop realtime publisher to open microphone and Electron system-loopback adapters directly
- [x] 1.2 Remove native Helper startup and native frame subscription from the production publisher path
- [x] 1.3 Keep idle source monitoring mutually exclusive with the live publisher

## 2. Permission and packaging

- [x] 2.1 Route screen and system-audio permission checks through the Electron main application
- [x] 2.2 Stop packaging and signing the Swift capture Helper in the current macOS arm64 bundle
- [x] 2.3 Expose an explicit Electron single-owner runtime identity in desktop diagnostics

## 3. Regression coverage

- [x] 3.1 Add tests for the Electron capture policy and absence of native production ownership
- [x] 3.2 Add tests for system-loopback media-track handling and dual-channel speech segmentation
- [x] 3.3 Validate the OpenSpec change in strict mode

## 4. Build and end-to-end verification

- [x] 4.1 Run desktop typecheck and automated tests
- [x] 4.2 Build the macOS arm64 assistant and verify the package contains no Swift capture Helper
- [x] 4.3 Run synthetic backend dual-channel publishing and role-mapping regression tests
- [x] 4.4 Install and launch the rebuilt assistant for user verification

## 5. Release

- [x] 5.1 Update the desktop release manifest and downloadable package
- [ ] 5.2 Commit and push the completed change to Git
- [ ] 5.3 Deploy the updated production services and verify public health endpoints
