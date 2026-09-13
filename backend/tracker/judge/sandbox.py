"""
Sandbox — subprocess execution with resource limits.

SECURITY NOTES
--------------
* Every submission runs in a **fresh temporary directory** that is cleaned up
  after execution, regardless of outcome.
* Source code size and stdin size are checked before execution.
* Processes are killed after the time limit — no runaway processes.
* The subprocess inherits a minimal environment (only PATH + essential vars).
  No Django secrets, DB credentials, or API keys are forwarded.
* Network access is NOT blocked at the OS level in local dev mode (that
  requires Docker + network namespaces). In production, the Docker setup
  provides proper network isolation.
* Memory limits on Windows cannot be enforced via resource.setrlimit (POSIX
  only). Memory is monitored post-run via psutil and the verdict is set to
  MLE if exceeded. On Linux/Docker this is kernel-enforced.
* The Django web worker NEVER executes untrusted code directly. All execution
  goes through this module which is called from judge_service.py.

PRODUCTION DIAGNOSTICS
----------------------
Every compiler/runtime invocation emits a DEBUG log line recording:
  - the executable name and its resolved path (shutil.which result)
  - the PATH that the subprocess will see
  - the exit code and elapsed time
If a compiler is missing from the Docker image, an ERROR line is logged
immediately before the FileNotFoundError is raised, making infra problems
trivially identifiable in Render logs without exposing user source code.
"""

import os
import sys
import shutil
import subprocess
import tempfile
import time
import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


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
    """
    Minimal safe environment forwarded to compiler/runtime subprocesses.

    Security: we forward ONLY what compilers and runtimes need to function.
    No Django settings, no database credentials, no API keys are passed.

    PATH     — compilers and runtimes must be locatable (gcc, g++, java, etc.)
    JAVA_HOME — JVM needs this to locate shared libraries on Linux
    HOME     — some tools (e.g. Java) write temp files under HOME
    LANG/LC_ALL — gcc emits UTF-8 error messages only when locale is set
    Windows-only vars (SYSTEMROOT, TEMP, etc.) — required by Windows tools
    """
    env = {}

    # PATH is always forwarded — compilers must be findable.
    if "PATH" in os.environ:
        env["PATH"] = os.environ["PATH"]

    # Linux / Docker: JAVA_HOME lets the JVM locate its shared libraries.
    # Set in the Dockerfile via ENV JAVA_HOME=/usr/lib/jvm/default-java.
    if "JAVA_HOME" in os.environ:
        env["JAVA_HOME"] = os.environ["JAVA_HOME"]

    # HOME: some tools (Java, gcc temp files) reference it on Linux.
    if "HOME" in os.environ:
        env["HOME"] = os.environ["HOME"]

    # Locale: gcc/g++ produce readable UTF-8 error messages when set.
    for key in ("LANG", "LC_ALL", "LC_CTYPE"):
        if key in os.environ:
            env[key] = os.environ[key]

    # Windows-only: required by native Windows tools.
    for key in ("SYSTEMROOT", "SYSTEMDRIVE", "TEMP", "TMP", "USERPROFILE", "PATHEXT", "COMSPEC"):
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


def _log_compiler_discovery(cmd: list, step: str) -> None:
    """
    Emit a structured diagnostic log entry before each subprocess invocation.

    Logged (SAFE — no source code, no secrets):
      step       — 'compile' or 'run'
      executable — first token of the command (e.g. 'g++', 'javac')
      resolved   — absolute path returned by shutil.which, or None if not on PATH
      path       — the PATH the subprocess will use
    """
    exe = cmd[0] if cmd else "<empty>"
    resolved = shutil.which(exe, path=os.environ.get("PATH", ""))
    if resolved is None:
        if os.path.isfile(exe):
            resolved = exe
        elif os.name == 'nt':
            for ext in ('.exe', '.bat', '.cmd'):
                if os.path.isfile(exe + ext):
                    resolved = exe + ext
                    break

    logger.debug(
        "[judge][%s] executable=%r  resolved=%r  PATH=%s",
        step, exe, resolved, os.environ.get("PATH", "<unset>"),
    )
    if resolved is None and not os.path.isabs(exe):
        logger.error(
            "[judge][%s] TOOL NOT FOUND: %r is not on PATH=%s — "
            "this is an infrastructure error, not a user code error. "
            "Check that the Docker image has the required compiler installed.",
            step, exe, os.environ.get("PATH", "<unset>"),
        )


def _run_subprocess(
    cmd: list[str],
    stdin_data: str,
    time_limit_seconds: float,
    cwd: str,
    step: str = "run",
) -> tuple[str, str, int, float, int]:
    """
    Run *cmd* with *stdin_data* and return (stdout, stderr, returncode, elapsed_ms, memory_kb).
    Kills the process if it exceeds *time_limit_seconds*.

    *step* is 'compile' or 'run' — used only in diagnostic log messages.
    """
    _log_compiler_discovery(cmd, step)

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
            logger.info("[judge][%s] TLE after %dms (limit=%.1fs)", step, elapsed_ms, time_limit_seconds)
            return "", "Time limit exceeded.", -9, elapsed_ms, 0

        elapsed_ms = int((time.monotonic() - start) * 1000)
        logger.debug("[judge][%s] exit_code=%d  elapsed_ms=%d", step, proc.returncode, elapsed_ms)
        return (
            stdout_data.decode("utf-8", errors="replace"),
            stderr_data.decode("utf-8", errors="replace"),
            proc.returncode,
            elapsed_ms,
            peak_mem_kb,
        )
    except FileNotFoundError:
        elapsed_ms = int((time.monotonic() - start) * 1000)
        tool = cmd[0] if cmd else "Executable"
        logger.error(
            "[judge][%s] FileNotFoundError: %r not found. PATH=%s — "
            "Docker image is missing a required compiler/runtime.",
            step, tool, os.environ.get("PATH", "<unset>"),
        )
        return (
            "",
            f"Compiler or runtime not found: '{tool}'. Please verify that '{tool}' is installed on the host.",
            -1,
            elapsed_ms,
            0,
        )
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
                compile_cmd, "", 30.0, workdir, step="compile"  # generous compile timeout
            )
            if returncode != 0:
                return ExecutionResult(
                    status="COMPILE_ERROR",
                    compile_error=(stderr or stdout)[:4096],
                    execution_time_ms=elapsed_ms,
                )

        # 3. Build run command
        binary_to_run = binary_path
        if os.name == 'nt' and os.path.exists(binary_path + '.exe'):
            binary_to_run = binary_path + '.exe'

        run_cmd_template = language_config["run_cmd"]
        run_cmd = [
            part.replace("{source}", source_path)
                .replace("{binary}", binary_to_run)
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


class BatchExecutionSandbox:
    """
    Sandboxed execution session for a single multi-test judge operation.
    Compiles source code ONCE on the first test case and re-uses the compiled binary
    for subsequent test cases in the same submission.
    Guarantees:
      - Single compilation per submission for compiled languages (C++, C, Java)
      - Zero cross-user / cross-submission reuse (isolated tempdir per instance)
      - Complete cleanup of executables and temporary files when done
      - Intact per-test execution resource limits (timeout, memory, stdin size)
    """

    def __init__(
        self,
        language_config: dict,
        time_limit_seconds: float = 5.0,
        memory_limit_mb: int = 128,
    ):
        self.language_config = language_config
        self.time_limit_seconds = float(time_limit_seconds)
        self.memory_limit_mb = int(memory_limit_mb)
        self.workdir = None
        self.is_compiled = False
        self.compile_result = None
        self.source_path = None
        self.binary_to_run = None
        self.java_class = "Main"
        self.cleaned_up = False

    def cleanup(self):
        if self.cleaned_up:
            return
        self.cleaned_up = True
        if self.workdir and os.path.exists(self.workdir):
            try:
                shutil.rmtree(self.workdir, ignore_errors=True)
            except Exception:
                pass
            self.workdir = None

    def __del__(self):
        self.cleanup()

    def __call__(self, source_code: str, stdin: str = "") -> ExecutionResult:
        compile_cmd_template = self.language_config.get("compile_cmd")

        # Interpreted languages (e.g. Python): delegate directly to execute
        if not compile_cmd_template:
            return execute(
                language_config=self.language_config,
                source_code=source_code,
                stdin=stdin,
                time_limit_seconds=self.time_limit_seconds,
                memory_limit_mb=self.memory_limit_mb,
            )

        # Compiled languages: compile once on first call
        if not self.is_compiled:
            size_error = _check_sizes(source_code, stdin)
            if size_error:
                return ExecutionResult(status="SYSTEM_ERROR", stderr=size_error)

            self.workdir = tempfile.mkdtemp(prefix="dsa_batch_")
            ext = self.language_config["file_extension"]
            self.java_class = "Main"
            if ext == "java":
                import re
                m = re.search(r'public\s+class\s+([A-Za-z0-9_]+)', source_code)
                if not m:
                    m = re.search(r'class\s+([A-Za-z0-9_]+)', source_code)
                if m:
                    self.java_class = m.group(1)
                filename = f"{self.java_class}.java"
            else:
                filename = f"solution.{ext}"

            self.source_path = os.path.join(self.workdir, filename)
            binary_path = os.path.join(self.workdir, "solution_bin")

            with open(self.source_path, "w", encoding="utf-8") as f:
                f.write(source_code)

            compile_cmd = [
                part.replace("{source}", self.source_path).replace("{binary}", binary_path)
                for part in compile_cmd_template
            ]
            stdout, stderr, returncode, elapsed_ms, _ = _run_subprocess(
                compile_cmd, "", 30.0, self.workdir, step="compile"
            )
            if returncode != 0:
                self.compile_result = ExecutionResult(
                    status="COMPILE_ERROR",
                    compile_error=(stderr or stdout)[:4096],
                    execution_time_ms=elapsed_ms,
                )
                self.is_compiled = True
                return self.compile_result

            self.binary_to_run = binary_path
            if os.name == 'nt' and os.path.exists(binary_path + '.exe'):
                self.binary_to_run = binary_path + '.exe'

            self.is_compiled = True

        # If earlier compilation failed, return the cached compile error immediately
        if self.compile_result is not None:
            return self.compile_result

        # Validate stdin size for this test
        size_error = _check_sizes("", stdin)
        if size_error:
            return ExecutionResult(status="SYSTEM_ERROR", stderr=size_error)

        ext = self.language_config["file_extension"]
        run_cmd_template = self.language_config["run_cmd"]
        run_cmd = [
            part.replace("{source}", self.source_path)
                .replace("{binary}", self.binary_to_run)
                .replace("{workdir}", self.workdir)
                .replace("{main_class}", self.java_class)
            for part in run_cmd_template
        ]
        if ext == "java" and self.java_class != "Main":
            run_cmd = [part if part != "Main" else self.java_class for part in run_cmd]

        stdout, stderr, returncode, elapsed_ms, memory_kb = _run_subprocess(
            run_cmd, stdin, self.time_limit_seconds, self.workdir
        )

        if returncode == -9 or elapsed_ms >= int(self.time_limit_seconds * 1000 * 0.99):
            return ExecutionResult(
                status="TLE",
                stdout=stdout[:2048],
                stderr=stderr[:512],
                execution_time_ms=elapsed_ms,
                memory_kb=memory_kb,
            )

        if memory_kb > self.memory_limit_mb * 1024:
            return ExecutionResult(
                status="MLE",
                stdout=stdout[:2048],
                stderr=stderr[:512],
                execution_time_ms=elapsed_ms,
                memory_kb=memory_kb,
            )

        if returncode != 0:
            status_str = "RUNTIME_ERROR"
            compile_err = ""
            if "SyntaxError:" in stderr or "IndentationError:" in stderr:
                status_str = "COMPILE_ERROR"
                compile_err = stderr[:4096]
            return ExecutionResult(
                status=status_str,
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

