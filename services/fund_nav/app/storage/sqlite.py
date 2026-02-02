import os
import sqlite3
import time
import uuid
from dataclasses import dataclass
from typing import Optional

from ..core.config import (
    DB_PATH,
    INITIAL_INVITE_CODE,
    INVITE_DEFAULT_USES,
    INVITE_MAX_USES,
    INVITE_TTL_SEC,
    POSITION_DEFAULT_UNITS,
)


@dataclass
class User:
    id: str
    name: str
    username: str
    password_hash: str
    avatar_url: str | None
    must_change_password: bool
    created_at: float


@dataclass
class Invite:
    code: str
    creator_id: str
    max_uses: int
    used: int
    created_at: float
    expires_at: float | None

    @property
    def remaining(self) -> int:
        return max(0, self.max_uses - self.used)

    def can_use(self) -> bool:
        if self.used >= self.max_uses:
            return False
        if self.expires_at is None:
            return True
        return time.time() < self.expires_at


class SQLiteStore:
    def __init__(self, path: str | None = None) -> None:
        self.path = path or DB_PATH
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    username TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    avatar_url TEXT,
                    must_change_password INTEGER NOT NULL DEFAULT 0,
                    created_at REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS invites (
                    code TEXT PRIMARY KEY,
                    creator_id TEXT NOT NULL,
                    max_uses INTEGER NOT NULL,
                    used INTEGER NOT NULL,
                    created_at REAL NOT NULL,
                    expires_at REAL
                );
                CREATE TABLE IF NOT EXISTS watchlists (
                    user_id TEXT NOT NULL,
                    fund_code TEXT NOT NULL,
                    PRIMARY KEY (user_id, fund_code)
                );
                CREATE TABLE IF NOT EXISTS positions (
                    user_id TEXT NOT NULL,
                    fund_code TEXT NOT NULL,
                    units REAL NOT NULL,
                    cost REAL,
                    updated_at REAL NOT NULL,
                    PRIMARY KEY (user_id, fund_code)
                );
                """
            )
        self._ensure_user_columns()

        if INITIAL_INVITE_CODE:
            with self._connect() as conn:
                cur = conn.execute(
                    "SELECT code FROM invites WHERE code = ?",
                    (INITIAL_INVITE_CODE,),
                )
                if cur.fetchone() is None:
                    expires = time.time() + INVITE_TTL_SEC if INVITE_TTL_SEC > 0 else None
                    conn.execute(
                        """
                        INSERT INTO invites (code, creator_id, max_uses, used, created_at, expires_at)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (
                            INITIAL_INVITE_CODE,
                            "seed",
                            max(1, min(INVITE_DEFAULT_USES, INVITE_MAX_USES)),
                            0,
                            time.time(),
                            expires,
                        ),
                    )

    def create_user(self, username: str, password_hash: str, name: str | None = None) -> User:
        user = User(
            id=str(uuid.uuid4()),
            name=name or username,
            username=username,
            password_hash=password_hash,
            avatar_url=None,
            must_change_password=False,
            created_at=time.time(),
        )
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO users (id, name, username, password_hash, avatar_url, must_change_password, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    user.id,
                    user.name,
                    user.username,
                    user.password_hash,
                    user.avatar_url,
                    1 if user.must_change_password else 0,
                    user.created_at,
                ),
            )
        return user

    def get_user(self, user_id: str) -> Optional[User]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        if row is None:
            return None
        return User(
            id=row["id"],
            name=row["name"],
            username=row["username"],
            password_hash=row["password_hash"],
            avatar_url=row["avatar_url"],
            must_change_password=bool(row["must_change_password"]),
            created_at=row["created_at"],
        )

    def get_user_by_username(self, username: str) -> Optional[User]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        if row is None:
            return None
        return User(
            id=row["id"],
            name=row["name"],
            username=row["username"],
            password_hash=row["password_hash"],
            avatar_url=row["avatar_url"],
            must_change_password=bool(row["must_change_password"]),
            created_at=row["created_at"],
        )

    def update_user(self, user_id: str, name: str | None = None, avatar_url: str | None = None) -> Optional[User]:
        if name is None and avatar_url is None:
            return self.get_user(user_id)
        with self._connect() as conn:
            if name is not None and avatar_url is not None:
                conn.execute(
                    "UPDATE users SET name = ?, avatar_url = ? WHERE id = ?",
                    (name, avatar_url, user_id),
                )
            elif name is not None:
                conn.execute("UPDATE users SET name = ? WHERE id = ?", (name, user_id))
            else:
                conn.execute("UPDATE users SET avatar_url = ? WHERE id = ?", (avatar_url, user_id))
        return self.get_user(user_id)

    def update_password(self, user_id: str, password_hash: str, must_change_password: bool) -> Optional[User]:
        with self._connect() as conn:
            conn.execute(
                "UPDATE users SET password_hash = ?, must_change_password = ? WHERE id = ?",
                (password_hash, 1 if must_change_password else 0, user_id),
            )
        return self.get_user(user_id)

    def _ensure_user_columns(self) -> None:
        with self._connect() as conn:
            columns = {row["name"] for row in conn.execute("PRAGMA table_info(users)").fetchall()}
            if "username" not in columns:
                conn.execute("ALTER TABLE users ADD COLUMN username TEXT")
            if "password_hash" not in columns:
                conn.execute("ALTER TABLE users ADD COLUMN password_hash TEXT")
            if "avatar_url" not in columns:
                conn.execute("ALTER TABLE users ADD COLUMN avatar_url TEXT")
            if "must_change_password" not in columns:
                conn.execute("ALTER TABLE users ADD COLUMN must_change_password INTEGER DEFAULT 0")
            if "username" in columns:
                conn.execute("UPDATE users SET username = name WHERE username IS NULL")
            if "password_hash" in columns:
                conn.execute("UPDATE users SET password_hash = '' WHERE password_hash IS NULL")
            if "must_change_password" in columns:
                conn.execute(
                    "UPDATE users SET must_change_password = 0 WHERE must_change_password IS NULL"
                )
            conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_username ON users(username)")

    def add_invite(self, creator_id: str, max_uses: Optional[int] = None, ttl_sec: Optional[int] = None) -> Invite:
        code = uuid.uuid4().hex[:10]
        uses = max_uses if max_uses is not None else INVITE_DEFAULT_USES
        uses = max(1, min(int(uses), INVITE_MAX_USES))
        ttl = ttl_sec if ttl_sec is not None else INVITE_TTL_SEC
        expires_at = time.time() + ttl if ttl and ttl > 0 else None
        created_at = time.time()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO invites (code, creator_id, max_uses, used, created_at, expires_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (code, creator_id, uses, 0, created_at, expires_at),
            )
        return Invite(
            code=code,
            creator_id=creator_id,
            max_uses=uses,
            used=0,
            created_at=created_at,
            expires_at=expires_at,
        )

    def use_invite(self, code: str) -> bool:
        now = time.time()
        with self._connect() as conn:
            row = conn.execute(
                "SELECT max_uses, used, expires_at FROM invites WHERE code = ?",
                (code,),
            ).fetchone()
            if row is None:
                return False
            expires_at = row["expires_at"]
            if expires_at is not None and now >= expires_at:
                return False
            if row["used"] >= row["max_uses"]:
                return False
            res = conn.execute(
                """
                UPDATE invites
                SET used = used + 1
                WHERE code = ? AND used < max_uses
                """,
                (code,),
            )
            return res.rowcount == 1

    def get_invite(self, code: str) -> Optional[Invite]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM invites WHERE code = ?", (code,)).fetchone()
        if row is None:
            return None
        return Invite(
            code=row["code"],
            creator_id=row["creator_id"],
            max_uses=row["max_uses"],
            used=row["used"],
            created_at=row["created_at"],
            expires_at=row["expires_at"],
        )

    def list_invites(self, creator_id: str) -> list[Invite]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM invites WHERE creator_id = ? ORDER BY created_at DESC",
                (creator_id,),
            ).fetchall()
        return [
            Invite(
                code=row["code"],
                creator_id=row["creator_id"],
                max_uses=row["max_uses"],
                used=row["used"],
                created_at=row["created_at"],
                expires_at=row["expires_at"],
            )
            for row in rows
        ]

    def add_watch(self, user_id: str, fund_code: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO watchlists (user_id, fund_code) VALUES (?, ?)",
                (user_id, fund_code),
            )

    def remove_watch(self, user_id: str, fund_code: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "DELETE FROM watchlists WHERE user_id = ? AND fund_code = ?",
                (user_id, fund_code),
            )

    def list_watch(self, user_id: str) -> list[str]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT fund_code FROM watchlists WHERE user_id = ?",
                (user_id,),
            ).fetchall()
        return [row["fund_code"] for row in rows]

    def get_position(self, user_id: str, fund_code: str) -> Optional[dict]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM positions WHERE user_id = ? AND fund_code = ?",
                (user_id, fund_code),
            ).fetchone()
        if row is None:
            return None
        return {
            "code": row["fund_code"],
            "units": row["units"],
            "cost": row["cost"],
            "updated_at": row["updated_at"],
        }

    def upsert_position(self, user_id: str, fund_code: str, units: Optional[float], cost: Optional[float]) -> dict:
        if units is None:
            units = POSITION_DEFAULT_UNITS
        now = time.time()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO positions (user_id, fund_code, units, cost, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(user_id, fund_code)
                DO UPDATE SET units=excluded.units, cost=COALESCE(excluded.cost, positions.cost), updated_at=excluded.updated_at
                """,
                (user_id, fund_code, float(units), cost, now),
            )
        return {"code": fund_code, "units": float(units), "cost": cost, "updated_at": now}

    def list_positions(self, user_id: str) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT fund_code, units, cost, updated_at FROM positions WHERE user_id = ?",
                (user_id,),
            ).fetchall()
        return [
            {
                "code": row["fund_code"],
                "units": row["units"],
                "cost": row["cost"],
                "updated_at": row["updated_at"],
            }
            for row in rows
        ]
