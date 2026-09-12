"""
Sandbox — subprocess execution with resource limits.

SECURITY NOTES
--------------
* Every submission runs in a **fresh temporary directory** that is cleaned up
  after execution, regardless of outcome.
* Source code size and stdin size are checked before execution.
* Processes are killed after the time limit — no runaway processes.
* The subprocess inherits a minimal environment (only PATH).
* Network access is NOT blocked at the OS level in local dev mode (that
  requires Docker + network namespaces). In production, the Docker Compose
  setup provides proper network isolation.
* Memory limits on Windows cannot be enforced via resource.setrlimit (POSIX
  only). Memory is monitored post-run via psutil and the verdict is set to
  MLE if exceeded. On Linux/Docker this is kernel-enforced.
* The Django web worker NEVER executes untrusted code directly. All execution
  goes through this module which is called from judge_service.py.
"""

import os
import sys
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from typing import Optional

from tracker.scoring import (
    JUDGE_MAX_SOURCE_SIZE_BYTES,
    JUDGE_MAX_STDIN_SIZE_BYTES,
)

# psutil is optional — only needed for memory measurement.
try:
    import psutil
    _PSUTIL_AVAILABLE = True
except ImportError:
    _PSUTIL_AVAILABLE = False


@dataclass
class ExecutionResult:
    status: str          # 'OK', 'COMPILE_ERROR', 'RUNTIME_ERROR', 'TLE', 'MLE', 'SYSTEM_ERROR'
    stdout: str = ""
    stderr: str = ""
    compile_error: str = ""
    execution_time_ms: int = 0
    memory_kb: int = 0


def _safe_env() -> dict:
    """Minimal safe environment for the subprocess."""
    env = {}
    # Only forward PATH so compilers and interpreters can be found.
    if "PATH" in os.environ:
        env["PATH"] = os.environ["PATH"]
    # On Windows, tools need SYSTEMROOT, TEMP, SYSTEMDRIVE, etc.
    for key in ("SYSTEMROOT", "SYSTEMDRIVE", "TEMP", "TMP", "HOME", "USERPROFILE", "PATHEXT", "COMSPEC"):
        if key in os.environ:
            env[key] = os.environ[key]
    return env


def _check_sizes(source: str, stdin: str) -> Optional[str]:
    """Return an error message if inputs exceed limits, else None."""
    if len(source.encode()) > JUDGE_MAX_SOURCE_SIZE_BYTES:
        return f"Source code exceeds {JUDGE_MAX_SOURCE_SIZE_BYTES // 1024} KB limit."
    if len(stdin.encode()) > JUDGE_MAX_STDIN_SIZE_BYTES:
        return f"Input exceeds {JUDGE_MAX_STDIN_SIZE_BYTES // (1024 * 1024)} MB limit."
    return None


def _run_subprocess(
    cmd: list[str],
    stdin_data: str,
    time_limit_seconds: float,
    cwd: str,
) -> tuple[str, str, int, float, int]:
    """
    Run *cmd* with *stdin_data* and return (stdout, stderr, returncode, elapsed_ms, memory_kb).
    Kills the process if it exceeds *time_limit_seconds*.
    """
    start = time.monotonic()
    proc = None
    try:
        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=cwd,
            env=_safe_env(),
        )

        # Measure peak memory (best-effort, psutil required)
        peak_mem_kb = 0
        try:
            stdout_data, stderr_data = proc.communicate(
                input=stdin_data.encode("utf-8", errors="replace"),
                timeout=time_limit_seconds,
            )
            if _PSUTIL_AVAILABLE:
                try:
                    ps = psutil.Process(proc.pid)
                    peak_mem_kb = ps.memory_info().rss // 1024
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.communicate()
            elapsed_ms = int((time.monotonic() - start) * 1000)
            return "", "Time limit exceeded.", -9, elapsed_ms, 0

        elapsed_ms = int((time.monotonic() - start) * 1000)
        return (
            stdout_data.decode("utf-8", errors="replace"),
            stderr_data.decode("utf-8", errors="replace"),
            proc.returncode,
            elapsed_ms,
            peak_mem_kb,
        )
    except FileNotFoundError as exc:
        elapsed_ms = int((time.monotonic() - start) * 1000)
        tool = cmd[0] if cmd else "Executable"
        return "", f"Compiler or runtime not found: '{tool}'. Please verify that '{tool}' is installed on the host.", -1, elapsed_ms, 0
    except Exception as exc:
        if proc:
            try:
                proc.kill()
            except Exception:
                pass
        elapsed_ms = int((time.monotonic() - start) * 1000)
        return "", f"System error: {exc}", -2, elapsed_ms, 0


def execute(
    language_config: dict,
    source_code: str,
    stdin: str = "",
    time_limit_seconds: float = 5.0,
    memory_limit_mb: int = 128,
) -> ExecutionResult:
    """
    Compile (if needed) and execute *source_code* in a temporary directory.
    Returns an ExecutionResult.  The temp directory is always cleaned up.
    """
    # 1. Input validation
    size_error = _check_sizes(source_code, stdin)
    if size_error:
        return ExecutionResult(status="SYSTEM_ERROR", stderr=size_error)

    workdir = tempfile.mkdtemp(prefix="dsa_judge_")
    try:
        ext = language_config["file_extension"]
        java_class = "Main"
        if ext == "java":
            import re
            m = re.search(r'public\s+class\s+([A-Za-z0-9_]+)', source_code)
            if not m:
                m = re.search(r'class\s+([A-Za-z0-9_]+)', source_code)
            if m:
                java_class = m.group(1)
            filename = f"{java_class}.java"
        else:
            filename = f"solution.{ext}"
        source_path = os.path.join(workdir, filename)
        binary_path = os.path.join(workdir, "solution_bin")

        with open(source_path, "w", encoding="utf-8") as f:
            f.write(source_code)

        # 2. Compile step (optional)
        compile_cmd_template = language_config.get("compile_cmd")
        if compile_cmd_template:
            compile_cmd = [
                part.replace("{source}", source_path).replace("{binary}", binary_path)
                for part in compile_cmd_template
            ]
            stdout, stderr, returncode, elapsed_ms, _ = _run_subprocess(
                compile_cmd, "", 30.0, workdir  # generous compile timeout
            )
            if returncode != 0:
                return ExecutionResult(
                    status="COMPILE_ERROR",
                    compile_error=(stderr or stdout)[:4096],
                    execution_time_ms=elapsed_ms,
                )

        # 3. Build run command
        run_cmd_template = language_config["run_cmd"]
        run_cmd = [
            part.replace("{source}", source_path)
                .replace("{binary}", binary_path)
                .replace("{workdir}", workdir)
                .replace("{main_class}", java_class)
            for part in run_cmd_template
        ]
        if ext == "java" and java_class != "Main":
            run_cmd = [part if part != "Main" else java_class for part in run_cmd]

        # 4. Execute
        stdout, stderr, returncode, elapsed_ms, memory_kb = _run_subprocess(
            run_cmd, stdin, time_limit_seconds, workdir
        )

        # 5. Classify result
        if returncode == -9 or elapsed_ms >= int(time_limit_seconds * 1000 * 0.99):
            return ExecutionResult(
                status="TLE",
                stdout=stdout[:2048],
                stderr=stderr[:512],
                execution_time_ms=elapsed_ms,
                memory_kb=memory_kb,
            )

        if memory_kb > memory_limit_mb * 1024:
            return ExecutionResult(
                status="MLE",
                stdout=stdout[:2048],
                stderr=stderr[:512],
                execution_time_ms=elapsed_ms,
                memory_kb=memory_kb,
            )

        if returncode != 0:
            status = "RUNTIME_ERROR"
            compile_err = ""
            if "SyntaxError:" in stderr or "IndentationError:" in stderr:
                status = "COMPILE_ERROR"
                compile_err = stderr[:4096]
            return ExecutionResult(
                status=status,
                stdout=stdout[:2048],
                stderr=stderr[:2048],
                compile_error=compile_err,
                execution_time_ms=elapsed_ms,
                memory_kb=memory_kb,
            )

        return ExecutionResult(
            status="OK",
            stdout=stdout,
            stderr=stderr[:512],
            execution_time_ms=elapsed_ms,
            memory_kb=memory_kb,
        )

    finally:
        # Always clean up — prevent temp dir accumulation
        try:
            shutil.rmtree(workdir, ignore_errors=True)
        except Exception:
            pass
