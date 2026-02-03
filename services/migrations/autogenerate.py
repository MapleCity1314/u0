import os
import subprocess
import sys
from datetime import datetime


def main() -> int:
    msg = sys.argv[1] if len(sys.argv) > 1 else f"auto_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
    cmd = [
        "alembic",
        "-c",
        "services/migrations/alembic.ini",
        "revision",
        "--autogenerate",
        "-m",
        msg,
    ]
    env = os.environ.copy()
    return subprocess.call(cmd, env=env)


if __name__ == "__main__":
    raise SystemExit(main())
