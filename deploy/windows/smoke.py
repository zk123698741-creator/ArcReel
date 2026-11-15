"""Exercise the shipped interpreter, tools, HTTP frontend, auth and SQLite restart."""

import argparse
import json
import os
import socket
import subprocess
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bundle", type=Path, required=True)
    args = parser.parse_args()
    bundle = args.bundle.resolve()
    python = bundle / "python/python.exe"
    env = {k: v for k, v in os.environ.items() if not k.startswith("PYTHON")}
    env["PYTHONUTF8"] = "1"
    env["PYTHONNOUSERSITE"] = "1"
    env["PATH"] = str(Path(os.environ["WINDIR"]) / "System32")
    probe = subprocess.check_output(
        [
            str(python),
            "-c",
            "from lib.infra.ffmpeg import ffmpeg_status; "
            "from claude_agent_sdk._internal.transport.subprocess_cli import SubprocessCLITransport; "
            "s=ffmpeg_status(); assert s.available, s; print(s.version)",
        ],
        env=env,
        text=True,
    )
    print(probe.strip())
    cli = bundle / "python/Lib/site-packages/claude_agent_sdk/_bundled/claude.exe"
    print(subprocess.check_output([str(cli), "--version"], env=env, text=True).strip())
    print(
        subprocess.check_output([str(bundle / "git/bin/bash.exe"), "-lc", "git --version"], env=env, text=True).strip()
    )
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    base = f"http://127.0.0.1:{port}"
    with tempfile.TemporaryDirectory(prefix="ArcReel smoke 中文 ") as tmp:
        home = Path(tmp) / "User Data"
        previous_config = None
        for iteration in range(2):
            with (Path(tmp) / f"startup-{iteration}.log").open("w", encoding="utf-8") as log:
                process = subprocess.Popen(
                    [
                        str(python),
                        "-u",
                        str(bundle / "app/desktop_entry.py"),
                        "--data-home",
                        str(home),
                        "--port",
                        str(port),
                    ],
                    stdin=subprocess.PIPE,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    env=env,
                    cwd=tmp,
                    text=True,
                )
                try:
                    deadline = time.monotonic() + 150
                    while True:
                        try:
                            with opener.open(base + "/health", timeout=2) as response:
                                assert json.load(response)["status"] == "ok"
                            break
                        except (OSError, urllib.error.URLError) as exc:
                            if process.poll() is not None or time.monotonic() > deadline:
                                raise RuntimeError(
                                    (Path(tmp) / f"startup-{iteration}.log").read_text(encoding="utf-8")
                                ) from exc
                            time.sleep(0.5)
                    with opener.open(base, timeout=5) as response:
                        assert b"<html" in response.read().lower()
                    config = (home / "desktop.env").read_text(encoding="utf-8")
                    if previous_config is not None:
                        assert previous_config == config, "Credentials changed after restart"
                    previous_config = config
                    values = dict(line.split("=", 1) for line in config.splitlines() if "=" in line)
                    body = urllib.parse.urlencode(
                        {"username": values["AUTH_USERNAME"], "password": values["AUTH_PASSWORD"]}
                    ).encode()
                    with opener.open(base + "/api/v1/auth/token", data=body, timeout=10) as response:
                        token = json.load(response)["access_token"]
                    request = urllib.request.Request(
                        base + "/api/v1/auth/verify", headers={"Authorization": "Bearer " + token}
                    )
                    with opener.open(request, timeout=5) as response:
                        assert json.load(response)["valid"]
                    print(f"PASS start {iteration + 1}: health, SPA, login, verify, persistent config")
                finally:
                    if process.poll() is None:
                        process.communicate("stop\n", timeout=45)
                assert process.returncode == 0, process.returncode
        assert list((home / "data").rglob("*.db")), "SQLite database missing"
        print("PASS graceful shutdown and SQLite initialization/restart")


if __name__ == "__main__":
    main()
