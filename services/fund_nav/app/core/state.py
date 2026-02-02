from .config import STORE_BACKEND
from .security import TokenIssuer
from ..storage.memory import MemoryStore
from ..storage.sqlite import SQLiteStore


def build_store():
    if STORE_BACKEND == "memory":
        return MemoryStore()
    return SQLiteStore()


store = build_store()
issuer = TokenIssuer()
