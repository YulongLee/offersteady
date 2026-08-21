## 1. v0.1 Release Boundary and Safety

- [x] 1.1 Create a v0.1 release notes document that lists included capabilities, known limitations, deferred hardening, and blocking risks.
- [x] 1.2 Classify current MVP-risk areas, including payment persistence, auth/session persistence, realtime audio, desktop helper permissions, material processing, and RAG readiness.
- [x] 1.3 Decide whether v0.1 allows real paid users or only admin/internal test accounts, and record the decision in release notes.
- [x] 1.4 Confirm `.gitignore` excludes local env files, production secret files, runtime logs, raw user data, and generated sensitive artifacts.
- [x] 1.5 Update `.env.example` and environment documentation so all v0.1 variables are listed without real secret values.

## 2. Local Seal Verification

- [x] 2.1 Run OpenSpec strict validation for this change and any active release-blocking changes.
- [x] 2.2 Run Web typecheck, focused frontend tests, and production build.
- [x] 2.3 Run Backend import/health checks using the project virtual environment.
- [x] 2.4 Run a billing checkout smoke test that creates a signed 码支付 order without exposing the merchant key.
- [x] 2.5 Record validation commands and outcomes in the v0.1 release notes.

## 3. GitHub Upload Preparation

- [x] 3.1 Inspect pending working tree changes and separate release changes from unrelated local experiments.
- [x] 3.2 Confirm no `.env`, provider key, payment secret, OSS secret, SMS secret, model key, real resume, real screenshot, or raw private document is staged.
- [x] 3.3 Create or update the GitHub remote repository target and document whether it is private or public.
- [x] 3.4 Push the approved v0.1 branch or tag to GitHub.
- [x] 3.5 If the repository is public or externally shared, run a secret scan or equivalent manual secret-history audit before announcing the release candidate.

## 4. Server Deployment Configuration

- [x] 4.1 Prepare Ubuntu 24.04 server prerequisites: Docker, Docker Compose plugin, Git, firewall/security group ports, and a deploy directory.
- [x] 4.2 Pull the GitHub repository on the server and select the approved v0.1 branch or tag.
- [x] 4.3 Create server-only environment file with database, OSS, SMS, MinerU, Chat, Vision, Embedding, Rerank, ASR, JWT, and 码支付 variables.
- [x] 4.4 Configure `OFFERSTEADY_PUBLIC_WEB_BASE_URL`, CORS allowed origins, `VITE_API_BASE_URL`, `OFFERSTEADY_MZFPAY_NOTIFY_URL`, and `OFFERSTEADY_MZFPAY_RETURN_URL` for the server host.
- [x] 4.5 Ensure the Compose deployment persists PostgreSQL data and does not bake secrets into images.
- [x] 4.6 Start Web, Backend, PostgreSQL/pgvector, and Nginx through Docker Compose.

## 5. Server Smoke and Payment Callback Verification

- [x] 5.1 Verify the deployed Web page loads from the server host.
- [x] 5.2 Verify Backend `/healthz` and `/api/v1/billing/status` from outside the server.
- [x] 5.3 Verify the login page, material library page, interview page, billing page, and screenshot answer entry remain reachable.
- [ ] 5.4 Click a billing product in the deployed Web page and verify it opens a 码支付 link for the selected product amount.
- [ ] 5.5 Verify 码支付 can reach the public `notify_url` and the Backend handles signature verification without using `127.0.0.1`.
- [ ] 5.6 Confirm successful payment notification credits points or activates a pass exactly once, or mark automatic settlement as not ready if callback cannot be verified.

## 6. Operations, Rollback, and Handoff

- [x] 6.1 Document commands for viewing Compose logs, restarting services, stopping services, and checking service health.
- [x] 6.2 Document how to update server environment variables and restart affected services without committing secrets.
- [x] 6.3 Document rollback to the previous known-good branch/tag or local-only operation if deployment fails.
- [x] 6.4 Record the final v0.1 commit/tag, server host, exposed ports, validation status, and known limitations.
- [x] 6.5 Provide the user with final frontend and backend URLs for acceptance testing.

## 7. Production Web Build Guard

- [x] 7.1 Add a production-only Vite configuration guard that rejects missing, non-production, or loopback API settings.
- [x] 7.2 Add regression tests for valid same-origin production configuration and rejected localhost production configuration.
- [x] 7.3 Emit a public production build manifest and extend the deployment smoke test to verify Web state and reject loopback configuration.

## 8. PostgreSQL Automated Backup

- [x] 8.1 Add a credential-safe PostgreSQL backup script with archive validation, checksum generation, locking, and bounded retention.
- [x] 8.2 Add systemd service/timer units and document installation, status checks, manual execution, restore verification, and retention.
- [x] 8.3 Install the timer on the production server, create and validate an initial backup, and confirm the next scheduled run.
- [x] 8.4 Run shell checks, focused Web tests/build checks, and strict OpenSpec validation.
