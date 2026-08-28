# Verification

Verified on 2026-08-28 from the repository root.

- Focused workbench navigation test: `2 passed` (new link plus existing home navigation coverage).
- Full `App.test.tsx`: `26 passed`.
- Full Web suite: `311 passed, 1 failed`. The existing unrelated material-delete test expects `无法连接后端基础服务`, while the unchanged material flow renders `文档不存在。`; this change does not modify that flow or test.
- Web TypeScript check: passed.
- Production Web build with `VITE_APP_ENV=production`, same-origin API, and public version `1.2.11`: passed.
- External destination GET check: responded with a Feishu account-login redirect, confirming the folder URL is recognized; final access remains governed by the folder's Feishu sharing permissions.
- `git diff --check`: passed.
- `openspec validate add-workbench-user-manual-link --strict`: passed.

Only Web navigation, responsive CSS, tests, and OpenSpec artifacts changed for this feature. Backend and desktop deployment are not required.
