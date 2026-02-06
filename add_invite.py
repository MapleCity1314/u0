#!/usr/bin/env python3
"""Script to create test invite codes."""

import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone

# Add services to path
ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT / "services"))

from core.database import SessionLocal
from users.models.invite import Invite


def create_invite(code: str, max_uses: int = 10, days: int = 365):
    """Create a new invite code."""
    db = SessionLocal()
    try:
        # Check if invite already exists
        existing = db.query(Invite).filter(Invite.code == code).first()
        if existing:
            print(f"Invite code '{code}' already exists")
            print(f"  Status: {existing.status}")
            print(f"  Expires: {existing.expires_at}")
            print(f"  Used: {existing.used_count}/{existing.max_uses}")

            # Update if expired or used up
            if existing.status != "active" or existing.expires_at < datetime.now(timezone.utc):
                existing.status = "active"
                existing.expires_at = datetime.now(timezone.utc) + timedelta(days=days)
                existing.used_count = 0
                existing.max_uses = max_uses
                db.commit()
                print(f"  Updated to active!")
            return existing

        # Create new invite
        invite = Invite(
            code=code,
            max_uses=max_uses,
            used_count=0,
            expires_at=datetime.now(timezone.utc) + timedelta(days=days),
            status="active",
            owner_id=None,  # System invite
        )
        db.add(invite)
        db.commit()
        db.refresh(invite)

        print(f"Created invite code: {code}")
        print(f"  Max uses: {max_uses}")
        print(f"  Expires: {invite.expires_at}")
        return invite
    finally:
        db.close()


if __name__ == "__main__":
    # Create some test invite codes
    codes = [
        ("PRESTO", 100, 365),
        ("ILOVEW", 100, 365),
        ("TEST2024", 50, 365),
        ("WELCOME", 100, 365),
    ]

    print("Creating test invite codes...\n")
    for code, max_uses, days in codes:
        create_invite(code, max_uses, days)
        print()

    print("Done!")
