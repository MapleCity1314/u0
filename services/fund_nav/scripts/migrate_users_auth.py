import os
import sqlite3
import sys

from services.fund_nav.app.core.security import hash_password


def main() -> None:
    db_path = os.environ.get("FUND_NAV_DB_PATH")
    if not db_path:
        raise SystemExit("FUND_NAV_DB_PATH is required")
    default_password = os.environ.get("FUND_NAV_DEFAULT_PASSWORD", "change-me-123")
    if not os.path.exists(db_path):
        raise SystemExit(f"db not found: {db_path}")

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        columns = {
            row["name"]
            for row in conn.execute("PRAGMA table_info(users)").fetchall()
        }
        if "username" not in columns:
            conn.execute("ALTER TABLE users ADD COLUMN username TEXT")
        if "password_hash" not in columns:
            conn.execute("ALTER TABLE users ADD COLUMN password_hash TEXT")
        if "must_change_password" not in columns:
            conn.execute(
                "ALTER TABLE users ADD COLUMN must_change_password INTEGER DEFAULT 0"
            )
        conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_users_username ON users(username)"
        )
        rows = conn.execute(
            "SELECT id, name, username, password_hash FROM users"
        ).fetchall()
        updates = 0
        seen = set()
        for row in rows:
            base_username = row["username"] or row["name"]
            if not base_username:
                continue
            username = base_username
            if username in seen:
                suffix = 1
                while f"{base_username}{suffix}" in seen:
                    suffix += 1
                username = f"{base_username}{suffix}"
            original_hash = row["password_hash"] or ""
            password_hash = original_hash or hash_password(default_password)
            conn.execute(
                "UPDATE users SET username = ?, password_hash = ?, must_change_password = ? WHERE id = ?",
                (username, password_hash, 1 if not original_hash else 0, row["id"]),
            )
            seen.add(username)
            updates += 1
        conn.commit()
        print(f"migrated {updates} users")
        if updates > 0:
            print(f"default_password={default_password}")
    finally:
        conn.close()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(1)
