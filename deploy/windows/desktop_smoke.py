"""Verify the shipped desktop window with an isolated Chinese user profile."""

import argparse
import json
import os
import subprocess
import tempfile
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    bundle = args.bundle.resolve()
    env = {k: v for k, v in os.environ.items() if not k.startswith(("PYTHON", "ELECTRON"))}
    env["PATH"] = str(Path(os.environ["WINDIR"]) / "System32")
    with tempfile.TemporaryDirectory(prefix="ArcReel desktop 中文 ") as tmp:
        report = args.report.resolve() if args.report else bundle.parent / "desktop-smoke.json"
        command = [
            str(bundle / "ArcReel.exe"),
            "--desktop-smoke-home",
            str(Path(tmp) / "User Data"),
            "--desktop-smoke-report",
            str(report),
        ]
        process = subprocess.Popen(command, env=env, cwd=tmp)
        try:
            code = process.wait(timeout=240)
        except subprocess.TimeoutExpired:
            subprocess.run(
                [str(Path(os.environ["WINDIR"]) / "System32/taskkill.exe"), "/PID", str(process.pid), "/T", "/F"],
                check=False,
            )
            raise
        result = json.loads(report.read_text(encoding="utf-8"))
        if code != 0 or not result.get("passed"):
            raise RuntimeError(f"Desktop smoke failed ({code}): {result}")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        # A clean exit must release the actual HTTP listener.
        import socket
        from urllib.parse import urlsplit

        with socket.socket() as sock:
            assert sock.connect_ex(("127.0.0.1", urlsplit(result["base"]).port)) != 0
        print("PASS: embedded desktop, Chinese login/dashboard/menu, isolated renderer, clean shutdown")


if __name__ == "__main__":
    main()
