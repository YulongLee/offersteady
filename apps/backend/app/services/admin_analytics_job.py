from __future__ import annotations

import argparse
import json
from datetime import date

from app.core.config import get_settings
from app.services.admin_analytics import AdminAnalyticsService
from app.services.admin_repository import AdminRepository


def main() -> None:
    parser = argparse.ArgumentParser(description="Aggregate OfferSteady admin operations analytics.")
    parser.add_argument("--scheduled", action="store_true")
    parser.add_argument("--all-history", action="store_true")
    parser.add_argument("--start-date")
    parser.add_argument("--end-date")
    args = parser.parse_args()
    service = AdminAnalyticsService(AdminRepository(get_settings()))
    if args.scheduled:
        result = service.run_scheduled()
    elif args.all_history:
        result = service.backfill_all()
    else:
        today = date.today()
        start = date.fromisoformat(args.start_date) if args.start_date else today
        end = date.fromisoformat(args.end_date) if args.end_date else start
        result = service.aggregate_days(start=start, end=end, run_kind="manual")
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()

