# Walkthrough: Global Per-Problem Time Limits Architecture

We have designed, implemented, and thoroughly verified a **global per-problem time limits architecture** for the entire DSA problem dataset (3,392 problems) in the DSA Practice Tracker Online Judge.

---

## 1. Key Architectural Changes

### A. Database Models & Migration (`0014`)
- **Added Canonical Fields to `Problem`**:
  - `time_limit_ms` (`models.PositiveIntegerField`, validators: `MinValueValidator(100)`, `MaxValueValidator(15000)`, `null=True`, `blank=True`):
    - Authoritative execution time limit in milliseconds per test case.
  - `memory_limit_mb` (`models.PositiveIntegerField`, validators: `MinValueValidator(16)`, `MaxValueValidator(1024)`, `default=128`):
    - Authoritative memory limit in megabytes.
- **Migration Applied**: `0014_problem_memory_limit_mb_problem_time_limit_ms.py` applied cleanly to the database.

### B. Centralized Judge Configuration (`judge_config.py`)
- **Single Authoritative Source**: `backend/tracker/judge/judge_config.py`.
- **Difficulty-Aware Platform Defaults**:
  - `Easy`: **1,000 ms** (1.0 second base)
  - `Medium`: **2,000 ms** (2.0 seconds base)
  - `Hard`: **3,000 ms** (3.0 seconds base)
- **Centralized Language Execution Policy**:
  - Accounts for interpreter startup and bytecode JVM characteristics so interpreted/bytecode languages are not penalized with false TLEs on legitimate solutions:
    - **C / C++**: Multiplier `1.0x`, Startup `0 ms`
    - **Java**: Multiplier `1.5x`, Startup `150 ms` (JVM boot allowance)
    - **Python**: Multiplier `2.0x`, Startup `80 ms` (Interpreter boot allowance)
- **Dual Timeout Protection**:
  1. **Per-Test-Case Timeout**: Enforced strictly around process communication (`proc.communicate`).
  2. **Cumulative Test Suite Timeout Cap**: `min(total_tests * effective_ms, 30,000ms)` preventing server exhaustion on large test suites.
- **Compilation vs. Runtime Separation**:
  - Compilation (`gcc`, `g++`, `javac`) is run as a separate sandbox step with a generous 30s compilation allowance.
  - Compilation time is **never counted** toward program execution time or TLE verdicts.

### C. Judge Execution Engine Wiring
- **`judge_service.py`**:
  - `run_code_for_user`: Resolves authoritative timing using `resolve_execution_timing(problem, language)`. The client cannot specify or override the time limit.
  - `submit_code`: Resolves authoritative timing with cumulative cap `resolve_execution_timing(problem, language, total_tests=len(test_cases))` and passes `cumulative_time_limit_ms` into `run_against_test_cases`.
  - Both endpoints return `time_limit_ms` in the response for UI transparency.

### D. Dataset Population & Audit Commands
- **`populate_problem_time_limits.py`**:
  - Populated authoritative difficulty-aware limits across all 3,392 problems:
    - Easy: 815 problems (1,000 ms)
    - Medium: 1,802 problems (2,000 ms)
    - Hard: 775 problems (3,000 ms)
- **`audit_problem_dataset.py`**:
  - Expanded to audit execution timing and resource limits across the entire dataset.

### E. Frontend & Serializer Integration
- **`serializers.py`**:
  - Added `time_limit_ms` and `memory_limit_mb` to both `ProblemSerializer` and lightweight `ProblemListSerializer`.
- **`ProblemStatement.jsx`**:
  - Renders visual badges for Time Limit (`Time: 2.0s`) and Memory Limit (`Mem: 128 MB`) in the problem header.
- **`JudgePage.jsx`**:
  - Enhanced verdict banner to render `TIME LIMIT EXCEEDED` with amber styling and Clock icon when TLE occurs.
  - Displays measured time alongside the authoritative limit (`e.g. 94 ms / 3000ms limit`).

---

## 2. Verification & Automated Tests

### A. Automated Test Suite (`test_time_limits.py`)
Ran `manage.py test tracker.tests.test_time_limits`:
```
Found 10 test(s).
..........
----------------------------------------------------------------------
Ran 10 tests in 5.116s
OK
```
1. `test_model_validators_reject_invalid_limits`: Rejects limits < 100ms or > 15,000ms, and memory < 16MB or > 1024MB.
2. `test_difficulty_aware_defaults`: Verifies Easy=1000ms, Medium=2000ms, Hard=3000ms defaults.
3. `test_language_execution_policy`: Verifies Python multiplier (2.0x + 80ms) and Java multiplier (1.5x + 150ms).
4. `test_per_problem_configured_override`: Verifies explicit problem-level override takes precedence over difficulty.
5. `test_frontend_cannot_override_time_limit`: Verifies API ignores client-supplied `time_limit` / `time_limit_ms`.
6. `test_time_limit_exceeded_verdict`: Verifies timeout produces canonical `TLE` verdict and persists correctly.
7. `test_efficient_solution_passes`: Verifies clean solution passes within limit with `ACCEPTED`.
8. `test_hidden_test_cases_respect_time_limit`: Verifies hidden test triggers TLE without leaking inputs/outputs.
9. `test_cumulative_timeout_cap`: Verifies multi-test suites are capped at 30,000ms.
10. `test_serializers_include_time_and_memory_limits`: Verifies serialization in list and detail views.

### B. Full Test Suite Regression (`manage.py test tracker`)
```
Found 77 test(s).
Ran 77 tests in 22.452s
OK
```
All 77 existing and new tests pass with 0 errors.

### C. Problem #25 (Reverse Nodes in k-Group) Verification
- Problem: #25 Reverse Nodes in k-Group (Hard, `time_limit_ms=3000`, effective Python limit: 6,080 ms).
- **Efficient Solution**:
  - Passed 2 / 2 tests in **94 ms**.
  - Verdict: **`ACCEPTED`**.
- **Inefficient Solution (7s Sleep)**:
  - Timed out at **6,110 ms** (exceeded 6,080 ms limit).
  - Verdict: **`TLE`**.

### D. Frontend Build Verification
Ran `npm run build` in `frontend/`:
```
✓ built in 1.68s
```
Build completed with 0 errors and 0 warnings.
