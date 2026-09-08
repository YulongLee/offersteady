# Global password authentication release checks

This release changes only Global customer authentication. Domestic phone/SMS login and Global Admin authentication remain unchanged.

## Pre-deployment

- Back up the isolated Global PostgreSQL database.
- Keep `OFFERSTEADY_PRODUCT_EDITION=global` and the verified SMTP configuration enabled.
- Build the Backend with the declared `argon2-cffi` dependency.
- Apply `0041_global_password_authentication.sql`; it only adds the email challenge purpose and an index.
- Retain the previous Global Backend and Web image tags for rollback.

## Smoke tests

- Register a synthetic new email by code and password.
- Sign out and sign in again with email and password without requesting a code.
- Migrate a synthetic legacy code-login account through “Set a password” and confirm its user ID is unchanged.
- Reset a password by email and verify older refresh sessions no longer work.
- Change a password from Settings and verify the current session remains usable while another session is revoked.
- Confirm domestic SMS login and Global Admin email-code login are unchanged.

## Rollback

Restore the previous Global Backend and Web image tags. The additive migration may remain in place. Existing accounts and their data are not deleted; the legacy email-code endpoint remains available to the previous Web release.
