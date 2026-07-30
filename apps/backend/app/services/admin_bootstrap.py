from __future__ import annotations

import argparse

from app.core.config import get_settings
from app.services.admin_repository import AdminRepository
from app.services.admin_service import AdminService, PERMISSIONS_BY_ROLE


def main() -> None:
    parser = argparse.ArgumentParser(description="Create or rotate an OfferSteady administrator authorization.")
    parser.add_argument("--login-id", required=True)
    parser.add_argument("--role", choices=sorted(PERMISSIONS_BY_ROLE), default="super_admin")
    args = parser.parse_args()
    settings = get_settings()
    service = AdminService(settings, AdminRepository(settings))
    authorization, secret, uri = service.bootstrap(login_id=args.login_id, role=args.role)
    print(f"authorization_id={authorization['authorization_id']}")
    print(f"user_id={authorization['user_id']}")
    print(f"role={authorization['role']}")
    print(f"totp_secret={secret}")
    print(f"provisioning_uri={uri}")
    print("Store the TOTP secret offline. Re-running this command rotates it and revokes prior authorization versions.")


if __name__ == "__main__":
    main()
