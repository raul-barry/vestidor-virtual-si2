"""Expire subscriptions and audit first entry into the 30-day warning window."""
import argparse
import json
import sys

def main() -> int:
    parser = argparse.ArgumentParser(description="Process SaaS subscription lifecycle events")
    parser.add_argument("--expiring-within-days", type=int, default=30)
    args = parser.parse_args()
    from app.database.database import SessionLocal
    from app.services.subscription_service import SubscriptionService

    db = SessionLocal()
    try:
        result = SubscriptionService(db).process_lifecycle(expiring_within_days=args.expiring_within_days)
        print(json.dumps(result, sort_keys=True))
        return 0
    except Exception as exc:
        db.rollback()
        print(f"Subscription lifecycle processing failed: {exc}", file=sys.stderr)
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
