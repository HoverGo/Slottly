import asyncio
import os
import sys

import asyncpg

MAX_ATTEMPTS = 30
DELAY_SECONDS = 2


def _dsn() -> str:
    url = os.environ.get("DATABASE_URL", "")
    if not url:
        print("DATABASE_URL не задан")
        sys.exit(1)
    return url.replace("postgresql+asyncpg://", "postgresql://")


async def _wait() -> None:
    dsn = _dsn()
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            conn = await asyncpg.connect(dsn)
            await conn.close()
            print("PostgreSQL доступен")
            return
        except (OSError, asyncpg.PostgresError):
            print(f"PostgreSQL недоступен, попытка {attempt}/{MAX_ATTEMPTS}...")
            await asyncio.sleep(DELAY_SECONDS)

    print("Не удалось подключиться к PostgreSQL")
    sys.exit(1)


if __name__ == "__main__":
    asyncio.run(_wait())
