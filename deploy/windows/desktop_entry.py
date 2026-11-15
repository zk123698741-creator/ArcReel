"""Run the bundled backend with persistent per-user desktop configuration."""

import argparse
import os
import secrets
import sys
import threading
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-home", type=Path, required=True)
    parser.add_argument("--port", type=int, default=1241)
    args = parser.parse_args()
    home = args.data_home.resolve()
    home.mkdir(parents=True, exist_ok=True)
    config = home / "desktop.env"
    if not config.exists():
        with config.open("x", encoding="utf-8") as stream:
            stream.write(f"AUTH_USERNAME=admin\nAUTH_PASSWORD={secrets.token_urlsafe(24)}\n")

    from dotenv import dotenv_values

    values = dotenv_values(config)
    os.environ.update({
        "AUTH_ENABLED": "true",
        "AUTH_USERNAME": values.get("AUTH_USERNAME") or "admin",
        "AUTH_PASSWORD": values.get("AUTH_PASSWORD") or "",
        "ARCREEL_DATA_DIR": str(home / "data"),
        "CLAUDE_CONFIG_DIR": str(home / "claude"),
        "PYTHON_DOTENV_DISABLED": "1",
        "PYTHONUTF8": "1",
        "PYTHONNOUSERSITE": "1",
        "PYTHONPATH": str(Path(__file__).resolve().parent),
        "ARCREEL_API_BASE": f"http://127.0.0.1:{args.port}/api/v1",
    })
    if not os.environ["AUTH_PASSWORD"]:
        raise ValueError(f"AUTH_PASSWORD is empty in {config}")
    # Desktop always uses its own SQLite database and persisted signing secret.
    os.environ.pop("DATABASE_URL", None)
    os.environ.pop("AUTH_TOKEN_SECRET", None)
    from lib.config.env_keys import PROVIDER_SECRET_KEYS

    for key in PROVIDER_SECRET_KEYS:
        os.environ.pop(key, None)
    root = Path(__file__).resolve().parent.parent
    os.environ["PYTHONTZPATH"] = str(root / "python/Lib/site-packages/pytz/zoneinfo")
    import zoneinfo

    zoneinfo.reset_tzpath()
    import json

    manifest = json.loads((root / "build-info.json").read_text(encoding="utf-8"))
    os.environ["ARCREEL_BUILD_COMMIT"] = manifest["commit"]
    os.environ["PATH"] = os.pathsep.join(str(p) for p in (
        root / "python", root / "git" / "cmd", root / "git" / "bin",
        root / "git" / "usr" / "bin", root / "git" / manifest.get("git_native_dir", "mingw64") / "bin",
    )) + os.pathsep + os.environ.get("PATH", "")
    os.environ["CLAUDE_CODE_GIT_BASH_PATH"] = str(root / "git" / "bin" / "bash.exe")
    os.chdir(Path(__file__).resolve().parent)
    import uvicorn

    server = uvicorn.Server(uvicorn.Config(
        "server.app:app", host="127.0.0.1", port=args.port, log_level="info",
    ))

    def watch_launcher():
        sys.stdin.readline()
        server.should_exit = True

    threading.Thread(target=watch_launcher, daemon=True).start()
    server.run()


if __name__ == "__main__":
    main()
