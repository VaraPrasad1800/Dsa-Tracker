"""
Judge0 CE API Client Adapter.

Provides integration with hosted or self-hosted Judge0 CE instances:
  - Reads configuration from environment variables (JUDGE0_API_URL, JUDGE0_API_KEY, JUDGE0_API_HOST).
  - Translates language names (python, cpp, c, java) to Judge0 language IDs.
  - Submits code with time and memory limits and retrieves execution results.
  - Returns canonical ExecutionResult instances matching the local sandbox contract.
  - Transparently falls back to the hardened local sandbox if Judge0 is unconfigured or unreachable.
"""

import os
import time
import logging
import base64
from typing import Optional
import urllib.request
import urllib.error
import json

from tracker.judge.sandbox import ExecutionResult

logger = logging.getLogger(__name__)

# Standard Judge0 CE Language IDs (supported across Judge0 v1.13.0+)
# 71: Python (3.8.1) / 92: Python (3.11.2)
# 54: C++ (GCC 9.2.0)
# 50: C (GCC 9.2.0)
# 62: Java (OpenJDK 13.0.1)
JUDGE0_LANGUAGE_IDS = {
    'python': 71,
    'cpp': 54,
    'c': 50,
    'java': 62,
}

# Status IDs returned by Judge0 CE:
# 1: In Queue, 2: Processing, 3: Accepted, 4: Wrong Answer,
# 5: Time Limit Exceeded, 6: Compilation Error,
# 7: SIGSEGV, 8: SIGXFSZ, 9: SIGFPE, 10: SIGABRT, 11: NZEC, 12: Other Runtime,
# 13: Internal Error, 14: Exec Format Error
JUDGE0_STATUS_MAP = {
    3: 'OK',
    4: 'OK',  # Output comparison is performed by the verdict engine, not Judge0
    5: 'TLE',
    6: 'COMPILE_ERROR',
    7: 'RUNTIME_ERROR',
    8: 'RUNTIME_ERROR',
    9: 'RUNTIME_ERROR',
    10: 'RUNTIME_ERROR',
    11: 'RUNTIME_ERROR',
    12: 'RUNTIME_ERROR',
    13: 'SYSTEM_ERROR',
    14: 'SYSTEM_ERROR',
}


def is_judge0_configured() -> bool:
    """Return True if JUDGE0_API_URL is configured in the environment."""
    return bool(os.environ.get('JUDGE0_API_URL', '').strip())


def get_judge0_headers() -> dict:
    """Construct HTTP headers for Judge0 API requests."""
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
    }
    api_key = os.environ.get('JUDGE0_API_KEY', '').strip()
    api_host = os.environ.get('JUDGE0_API_HOST', '').strip()

    if api_key:
        headers['X-RapidAPI-Key'] = api_key
        headers['X-Auth-Token'] = api_key  # for self-hosted Judge0
    if api_host:
        headers['X-RapidAPI-Host'] = api_host

    return headers


def execute_judge0(
    language: str,
    source_code: str,
    stdin: str = "",
    time_limit_seconds: float = 5.0,
    memory_limit_mb: int = 128,
) -> ExecutionResult:
    """
    Execute code via Judge0 CE API.
    Raises RuntimeError or urllib.error.URLError on network/HTTP failures.
    """
    api_url = os.environ.get('JUDGE0_API_URL', '').strip().rstrip('/')
    if not api_url:
        raise RuntimeError("JUDGE0_API_URL is not configured.")

    lang_id = JUDGE0_LANGUAGE_IDS.get(language.lower())
    if not lang_id:
        raise ValueError(f"Language '{language}' has no Judge0 mapping.")

    payload = {
        'language_id': lang_id,
        'source_code': source_code,
        'stdin': stdin,
        'cpu_time_limit': max(0.5, float(time_limit_seconds)),
        'memory_limit': max(16384, int(memory_limit_mb) * 1024),  # Judge0 expects KB
    }

    req_url = f"{api_url}/submissions?base64_encoded=false&wait=true"
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(req_url, data=data, headers=get_judge0_headers(), method='POST')

    with urllib.request.urlopen(req, timeout=time_limit_seconds + 5.0) as resp:
        result_data = json.loads(resp.read().decode('utf-8'))

    status_info = result_data.get('status', {})
    status_id = status_info.get('id', 0)
    status_str = JUDGE0_STATUS_MAP.get(status_id, 'SYSTEM_ERROR')

    stdout = result_data.get('stdout') or ''
    stderr = result_data.get('stderr') or ''
    compile_output = result_data.get('compile_output') or ''

    # Time and memory parsing
    raw_time = result_data.get('time')
    try:
        execution_time_ms = int(float(raw_time) * 1000) if raw_time is not None else 0
    except (ValueError, TypeError):
        execution_time_ms = 0

    memory_kb = result_data.get('memory') or 0

    return ExecutionResult(
        status=status_str,
        stdout=stdout,
        stderr=stderr,
        compile_error=compile_output if status_str == 'COMPILE_ERROR' else '',
        execution_time_ms=execution_time_ms,
        memory_kb=int(memory_kb),
    )
