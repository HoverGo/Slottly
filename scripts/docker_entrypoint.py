import os
import subprocess
import sys


def main() -> None:
    print("Ожидание PostgreSQL...")
    subprocess.check_call([sys.executable, "scripts/wait_for_db.py"])

    print("Применение миграций...")
    subprocess.check_call(["alembic", "upgrade", "head"])

    reload = os.environ.get("UVICORN_RELOAD", "").lower() in ("1", "true", "yes")
    workers = os.environ.get("WEB_CONCURRENCY", "1")

    cmd = [
        "uvicorn",
        "app.main:app",
        "--host",
        "0.0.0.0",
        "--port",
        "8000",
    ]

    if reload:
        print("Запуск API (reload)...")
        cmd.append("--reload")
    else:
        print(f"Запуск API (workers={workers})...")
        if workers != "1":
            cmd.extend(["--workers", workers])

    os.execvp(cmd[0], cmd)


if __name__ == "__main__":
    main()
