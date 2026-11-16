"""Assemble a relocatable Windows runtime and compile its Inno Setup installer."""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent


def run(*args, cwd=ROOT):
    print("+", *map(str, args), flush=True)
    return subprocess.check_output(list(map(str, args)), cwd=cwd, text=True, encoding="utf-8").strip()


def copy_tree(source, target):
    shutil.copytree(source, target, dirs_exist_ok=True, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".git"))


def build_desktop(bundle):
    print(run("npm.cmd", "ci", cwd=HERE))
    print(run("node", HERE / "node_modules/electron/install.js"))
    copy_tree(HERE / "node_modules/electron/dist", bundle)
    (bundle / "electron.exe").replace(bundle / "ArcReel.exe")
    copy_tree(HERE / "desktop", bundle / "resources/app")
    return json.loads((HERE / "node_modules/electron/package.json").read_text(encoding="utf-8"))["version"]


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    os.environ["PYTHONUTF8"] = "1"
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--iscc", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    bundle = output / "ArcReel"
    # A fresh destination prevents deleted files from surviving into a later build.
    bundle.mkdir(exist_ok=False)
    print(run("uv", "python", "install", "3.13.14"))
    python = Path(run("uv", "python", "find", "--system", "--managed-python", "3.13.14"))
    print(run("uv", "sync", "--frozen", "--no-dev", "--no-editable", "--no-install-project", "--python", python))
    base = Path(run(python, "-c", "import sys; print(sys.base_prefix)"))
    copy_tree(base, bundle / "python")
    copy_tree(ROOT / ".venv/Lib/site-packages", bundle / "python/Lib/site-packages")
    app = bundle / "app"
    for name in ("lib", "server", "alembic", "scripts", "agent_runtime_profile", "public", "LICENSES"):
        copy_tree(ROOT / name, app / name)
    copy_tree(ROOT / "frontend/dist", app / "frontend/dist")
    for name in ("alembic.ini", "LICENSE", "NOTICE", "pyproject.toml", "uv.lock"):
        shutil.copy2(ROOT / name, app / name)
    shutil.copy2(HERE / "desktop_entry.py", app / "desktop_entry.py")
    # Python skill subprocesses must resolve the same application modules.
    (bundle / "python/Lib/site-packages/arcreel-desktop.pth").write_text("../../../app\n", encoding="utf-8")
    git_exe = Path(shutil.which("git") or "")
    git_root = git_exe.parent.parent
    if not (git_root / "bin/bash.exe").is_file():
        raise RuntimeError(f"Git for Windows with Bash is required at build time: {git_root}")
    native_dir = Path(run(git_exe, "--exec-path")).relative_to(git_root).parts[0]
    for name in ("bin", "cmd", "etc", native_dir, "usr"):
        copy_tree(git_root / name, bundle / "git" / name)
    for name in ("LICENSE.txt", "ReleaseNotes.html"):
        if (git_root / name).is_file():
            shutil.copy2(git_root / name, bundle / "git" / name)
    electron_version = build_desktop(bundle)
    version = json.loads((ROOT / "frontend/package.json").read_text(encoding="utf-8"))["version"]
    manifest = {
        "version": version,
        "commit": run("git", "rev-parse", "HEAD"),
        "python": run(python, "--version"),
        "git": run("git", "--version"),
        "git_native_dir": native_dir,
        "desktop": "embedded-electron",
        "electron": electron_version,
        "default_language": "zh",
    }
    (bundle / "build-info.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(run(python, HERE / "smoke.py", "--bundle", bundle))
    print(run(python, HERE / "desktop_smoke.py", "--bundle", bundle))
    print(
        run(
            args.iscc,
            f"/DAppVersion={version}",
            f"/DBundleDir={bundle}",
            f"/DOutputDirPath={output}",
            HERE / "setup.iss",
        )
    )
    installer = output / f"ArcReel-{version}-windows-x64-Setup.exe"
    digest = hashlib.file_digest(installer.open("rb"), "sha256").hexdigest()
    (output / "SHA256SUMS.txt").write_text(f"{digest}  {installer.name}\n", encoding="utf-8")
    print(json.dumps({"installer": str(installer), "sha256": digest, **manifest}, indent=2))


if __name__ == "__main__":
    main()
