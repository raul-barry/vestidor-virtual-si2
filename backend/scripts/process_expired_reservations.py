"""Daily operational command to expire due reservations and release stock."""
import argparse
import json
import sys


def main() -> int:
    parser = argparse.ArgumentParser(description="Expire due reservations and release held stock")
    parser.add_argument("--batch-size", type=int, default=500)
    args = parser.parse_args()
    from app.database.database import SessionLocal
    from app.services.reservation_expiration_service import ReservationExpirationService

    db = SessionLocal()
    try:
        result = ReservationExpirationService(db).process_expired(batch_size=args.batch_size)
        print(json.dumps(result, sort_keys=True))
        return 0 if result["inconsistencias_inventario"] == 0 else 2
    except Exception as exc:
        db.rollback()
        print(f"Reservation expiration processing failed: {exc}", file=sys.stderr)
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
