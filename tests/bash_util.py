"""Git Bash / WSL path helpers for shell script tests on Windows."""

from __future__ import annotations

import os
import re
import shlex
import shutil
import subprocess
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping

_WIN_ABS = re.compile(r"^([A-Za-z]):[\\/]")

_GIT_BASH_CANDIDATES = (
    Path(r"C:\Program Files\Git\bin\bash.exe"),
    Path(r"C:\Program Files (x86)\Git\bin\bash.exe"),
)


@lru_cache(maxsize=1)
def _resolve_bash() -> tuple[str, str] | None:
    """Return (executable path, kind) where kind is 'git' or 'wsl'."""
    for candidate in _GIT_BASH_CANDIDATES:
        if candidate.is_file():
            return str(candidate), "git"
    found = shutil.which("bash")
    if not found:
        return None
    exe = found
    try:
        proc = subprocess.run(
            [exe, "-c", "uname -r 2>/dev/null || echo native"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        kind = "wsl" if "microsoft" in (proc.stdout or "").lower() else "git"
    except (OSError, subprocess.TimeoutExpired):
        kind = "git"
    return exe, kind


def _bash_kind() -> str:
    resolved = _resolve_bash()
    return resolved[1] if resolved else ""


def bash_available() -> bool:
    resolved = _resolve_bash()
    if not resolved:
        return False
    exe, _kind = resolved
    try:
        proc = subprocess.run(
            [exe, "-c", "echo advoi-bash-ok"],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    out = (proc.stdout or "") + (proc.stderr or "")
    if proc.returncode != 0:
        return False
    if "0x8007072c" in out or "RPC call" in out:
        return False
    return "advoi-bash-ok" in out


def bash_script_path(path: Path | str) -> str:
    """Convert a path to a form bash accepts on Windows (WSL or Git Bash)."""
    resolved = Path(path).resolve()
    if os.name != "nt":
        return str(resolved)
    posix = str(resolved).replace("\\", "/")
    match = re.match(r"^([A-Za-z]):/(.*)", posix)
    if not match:
        return posix
    drive, rest = match.group(1).lower(), match.group(2)
    if _bash_kind() == "wsl":
        return f"/mnt/{drive}/{rest}"
    return f"/{drive}/{rest}"


def _maybe_convert_arg(arg: str) -> str:
    if _WIN_ABS.match(arg):
        return bash_script_path(Path(arg))
    return arg


def _repo_root_for_script(script: Path) -> Path:
    """advoi-system scripts live under <repo>/scripts/*.sh."""
    return script.resolve().parent.parent


def _venv_scripts_path(repo_root: Path) -> str | None:
    scripts = repo_root / ".venv" / "Scripts"
    if scripts.is_dir():
        return bash_script_path(scripts)
    return None


def bash_env(
    env: Mapping[str, str] | None,
    *,
    script: Path | str | None = None,
) -> dict[str, str]:
    """Copy env, convert Windows paths, and set repo root overrides for tests."""
    out = dict(os.environ)
    if env:
        out.update(env)
    kind = _bash_kind()
    repo_root: Path | None = None
    if script is not None:
        repo_root = _repo_root_for_script(Path(script))
        root = bash_script_path(repo_root)
        out.setdefault("FM_AETHER_PROJECT_ROOT", root)
        out.setdefault("ADVOI_REPO_ROOT", root)
        py_path = f"{root}:{out.get('PYTHONPATH', '')}".rstrip(":")
        out["PYTHONPATH"] = py_path
    if os.name == "nt":
        if kind == "wsl":
            # Avoid Windows uv.exe RPC failures when bash is WSL.
            out["PATH"] = "/usr/local/bin:/usr/bin:/bin"
        elif kind == "git" and repo_root is not None:
            venv_scripts = _venv_scripts_path(repo_root)
            path_parts = [
                p
                for p in out.get("PATH", "").split(":")
                if p and "WindowsApps" not in p and "system32" not in p.lower()
            ]
            if venv_scripts:
                path_parts = [venv_scripts, *path_parts]
            out["PATH"] = ":".join(dict.fromkeys(path_parts))
        for key, value in list(out.items()):
            if isinstance(value, str) and _WIN_ABS.match(value):
                out[key] = bash_script_path(Path(value))
    return out


def _python3_shim_preamble(repo_root: Path, env: Mapping[str, str]) -> str:
    venv_scripts = _venv_scripts_path(repo_root)
    if not venv_scripts:
        return ""
    temp = env.get("TEMP") or env.get("TMP") or env.get("TMPDIR") or "/tmp"
    shim_dir = f"{temp.rstrip('/')}/advoi-bin"
    python_exe = f"{venv_scripts}/python"
    return (
        f'mkdir -p {shlex.quote(shim_dir)} && '
        f'printf "%s\\n" "#!/usr/bin/env bash" "exec \\"{python_exe}\\" \\"\\$@\\"" '
        f"> {shlex.quote(shim_dir)}/python3 && "
        f"chmod +x {shlex.quote(shim_dir)}/python3 && "
        f'export PATH="{shim_dir}:{venv_scripts}:$PATH" && '
    )


def run_bash(
    script: Path | str,
    *args: str,
    **kwargs: Any,
) -> subprocess.CompletedProcess[str]:
    """Run a bash script with POSIX paths and LF-only content on Windows."""
    resolved = _resolve_bash()
    if not resolved:
        raise RuntimeError("bash not available")
    exe, kind = resolved

    script_path = Path(script).resolve()
    converted = [_maybe_convert_arg(a) for a in args]
    env = bash_env(kwargs.get("env"), script=script_path)
    kwargs = {**kwargs, "env": env}

    runner = bash_script_path(script_path)
    arg_str = " ".join(shlex.quote(a) for a in converted)
    repo_root = _repo_root_for_script(script_path)

    if kind == "git":
        preamble = _python3_shim_preamble(repo_root, env)
        inner = f"{preamble}bash {shlex.quote(runner)} {arg_str}"
        return subprocess.run([exe, "-c", inner], **kwargs)

    # WSL: strip CRLF via tr, execute from /tmp so set -o pipefail works.
    inner = (
        f"tmp=$(mktemp /tmp/advoi-sh.XXXXXX) && "
        f"tr -d '\\r' < {shlex.quote(runner)} > \"$tmp\" && "
        f"bash \"$tmp\" {arg_str}; "
        f"rc=$?; rm -f \"$tmp\"; exit $rc"
    )
    return subprocess.run([exe, "-c", inner], **kwargs)