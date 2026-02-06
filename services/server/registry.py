import importlib
import logging
import os
from typing import Iterable

from fastapi import FastAPI

logger = logging.getLogger(__name__)

DEFAULT_MODULES = [
    "services.fund_nav.module",
    "services.news.module",
    "services.logs.module",
    "services.users.module",
    "services.agent.module",
]


def _parse_modules(value: str | None) -> list[str]:
    if not value:
        return DEFAULT_MODULES
    return [item.strip() for item in value.split(",") if item.strip()]


def load_modules(app: FastAPI, modules: Iterable[str] | None = None) -> None:
    module_list = list(modules) if modules is not None else _parse_modules(os.getenv("SERVICES_MODULES"))
    for path in module_list:
        try:
            module = importlib.import_module(path)
            if hasattr(module, "register"):
                module.register(app)
                continue
            if hasattr(module, "create_router"):
                app.include_router(module.create_router())
                continue
            raise RuntimeError(f"Module {path} missing register() or create_router()")
        except Exception as e:
            logger.warning(f"Failed to load module {path}: {e}")
            continue
