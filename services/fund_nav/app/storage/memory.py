import time
import uuid
from dataclasses import dataclass, field
from typing import Optional

from ..core.config import (
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
    created_at: float
    avatar_url: str | None = None
    must_change_password: bool = False


@dataclass
class Invite:
    code: str
    creator_id: str
    max_uses: int
    used: int = 0
    created_at: float = field(default_factory=lambda: time.time())
    expires_at: float | None = None

    @property
    def remaining(self) -> int:
        return max(0, self.max_uses - self.used)

    def can_use(self) -> bool:
        if self.used >= self.max_uses:
            return False
        if self.expires_at is None:
            return True
        return time.time() < self.expires_at


class MemoryStore:
    def __init__(self) -> None:
        self.users: dict[str, User] = {}
        self.users_by_username: dict[str, str] = {}
        self.invites: dict[str, Invite] = {}
        self.watchlists: dict[str, list[str]] = {}
        self.positions: dict[str, dict[str, dict]] = {}

        if INITIAL_INVITE_CODE:
            expires = time.time() + INVITE_TTL_SEC if INVITE_TTL_SEC > 0 else None
            seed = Invite(
                code=INITIAL_INVITE_CODE,
                creator_id="seed",
                max_uses=max(1, min(INVITE_DEFAULT_USES, INVITE_MAX_USES)),
                expires_at=expires,
            )
            self.invites[seed.code] = seed

    def create_user(self, username: str, password_hash: str, name: str | None = None) -> User:
        user = User(
            id=str(uuid.uuid4()),
            name=name or username,
            username=username,
            password_hash=password_hash,
            created_at=time.time(),
            must_change_password=False,
        )
        self.users[user.id] = user
        self.users_by_username[username] = user.id
        self.watchlists.setdefault(user.id, [])
        return user

    def get_user(self, user_id: str) -> Optional[User]:
        return self.users.get(user_id)

    def get_user_by_username(self, username: str) -> Optional[User]:
        user_id = self.users_by_username.get(username)
        if not user_id:
            return None
        return self.users.get(user_id)

    def update_user(self, user_id: str, name: str | None = None, avatar_url: str | None = None) -> Optional[User]:
        user = self.users.get(user_id)
        if user is None:
            return None
        if name is not None:
            user.name = name
        if avatar_url is not None:
            user.avatar_url = avatar_url
        return user

    def update_password(self, user_id: str, password_hash: str, must_change_password: bool) -> Optional[User]:
        user = self.users.get(user_id)
        if user is None:
            return None
        user.password_hash = password_hash
        user.must_change_password = must_change_password
        return user

    def add_invite(
        self,
        creator_id: str,
        max_uses: Optional[int] = None,
        ttl_sec: Optional[int] = None,
    ) -> Invite:
        code = uuid.uuid4().hex[:10]
        uses = max_uses if max_uses is not None else INVITE_DEFAULT_USES
        uses = max(1, min(int(uses), INVITE_MAX_USES))
        ttl = ttl_sec if ttl_sec is not None else INVITE_TTL_SEC
        expires = time.time() + ttl if ttl and ttl > 0 else None
        invite = Invite(
            code=code,
            creator_id=creator_id,
            max_uses=uses,
            expires_at=expires,
        )
        self.invites[invite.code] = invite
        return invite

    def use_invite(self, code: str) -> bool:
        invite = self.invites.get(code)
        if invite is None or not invite.can_use():
            return False
        invite.used += 1
        return True

    def get_invite(self, code: str) -> Optional[Invite]:
        return self.invites.get(code)

    def list_invites(self, creator_id: str) -> list[Invite]:
        return [i for i in self.invites.values() if i.creator_id == creator_id]

    def add_watch(self, user_id: str, fund_code: str) -> None:
        lst = self.watchlists.setdefault(user_id, [])
        if fund_code not in lst:
            lst.append(fund_code)

    def remove_watch(self, user_id: str, fund_code: str) -> None:
        lst = self.watchlists.setdefault(user_id, [])
        if fund_code in lst:
            lst.remove(fund_code)

    def list_watch(self, user_id: str) -> list[str]:
        return list(self.watchlists.get(user_id, []))

    def get_position(self, user_id: str, fund_code: str) -> Optional[dict]:
        return self.positions.get(user_id, {}).get(fund_code)

    def upsert_position(self, user_id: str, fund_code: str, units: Optional[float], cost: Optional[float]) -> dict:
        user_pos = self.positions.setdefault(user_id, {})
        if units is None:
            units = POSITION_DEFAULT_UNITS
        entry = user_pos.get(fund_code, {})
        entry.update(
            {
                "code": fund_code,
                "units": float(units),
                "cost": float(cost) if cost is not None else entry.get("cost"),
                "updated_at": time.time(),
            }
        )
        user_pos[fund_code] = entry
        return entry

    def list_positions(self, user_id: str) -> list[dict]:
        return list(self.positions.get(user_id, {}).values())
