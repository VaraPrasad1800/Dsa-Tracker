"""
Judge language configuration.
Each entry in SUPPORTED_LANGUAGES defines everything needed to compile and
run a submission for that language.  Adding a new language means adding one
entry here — no other judge code needs to change.

Adapter pattern: the executor reads this config; it does not contain
language-specific branching.
"""

import sys

SUPPORTED_LANGUAGES = {
    "python": {
        "display_name": "Python 3",
        "file_extension": "py",
        "compile_cmd": None,              # interpreted — no compile step
        "run_cmd": [sys.executable, "{source}"],
        "timeout_seconds": 5,
        "memory_limit_mb": 128,
        "version_cmd": [sys.executable, "--version"],
    },
    "c": {
        "display_name": "C (GCC)",
        "file_extension": "c",
        "compile_cmd": ["gcc", "-O2", "-o", "{binary}", "{source}", "-lm"],
        "run_cmd": ["{binary}"],
        "timeout_seconds": 3,
        "memory_limit_mb": 64,
        "version_cmd": ["gcc", "--version"],
    },
    "cpp": {
        "display_name": "C++ (G++)",
        "file_extension": "cpp",
        "compile_cmd": ["g++", "-O2", "-std=c++17", "-o", "{binary}", "{source}"],
        "run_cmd": ["{binary}"],
        "timeout_seconds": 3,
        "memory_limit_mb": 128,
        "version_cmd": ["g++", "--version"],
    },
    "java": {
        "display_name": "Java",
        "file_extension": "java",
        "compile_cmd": ["javac", "{source}"],
        "run_cmd": ["java", "-Xmx128m", "-cp", "{workdir}", "{main_class}"],
        "timeout_seconds": 5,
        "memory_limit_mb": 128,
        "version_cmd": ["java", "-version"],
    },
}

# Default complete-program starter code templates shown in the editor when a problem does not
# have a custom per-problem template configured.
DEFAULT_STARTER_CODE = {
    "python": (
        "import sys\n"
        "import json\n\n"
        "def solve():\n"
        "    input_data = [line.strip() for line in sys.stdin.read().splitlines() if line.strip()]\n"
        "    if not input_data:\n"
        "        return\n\n"
        "    # Read input from standard input\n"
        "    # Print output to standard output\n\n"
        "if __name__ == '__main__':\n"
        "    solve()\n"
    ),
    "cpp": (
        "#include <iostream>\n"
        "#include <vector>\n"
        "#include <string>\n"
        "#include <algorithm>\n\n"
        "using namespace std;\n\n"
        "int main() {\n"
        "    ios_base::sync_with_stdio(false);\n"
        "    cin.tie(NULL);\n\n"
        "    // Read input from standard input\n"
        "    // Write output to standard output\n\n"
        "    return 0;\n"
        "}\n"
    ),
    "c": (
        "#include <stdio.h>\n"
        "#include <stdlib.h>\n"
        "#include <string.h>\n"
        "#include <stdbool.h>\n\n"
        "int main() {\n"
        "    // Read input from standard input\n"
        "    // Write output to standard output\n\n"
        "    return 0;\n"
        "}\n"
    ),
    "java": (
        "import java.util.*;\n"
        "import java.io.*;\n\n"
        "public class Main {\n"
        "    public static void main(String[] args) {\n"
        "        Scanner sc = new Scanner(System.in);\n"
        "        // Read input from standard input\n"
        "        // Write output to standard output\n"
        "    }\n"
        "}\n"
    ),
}


def get_language_config(language: str) -> dict:
    """Return config for *language* or raise ValueError if unsupported."""
    if language not in SUPPORTED_LANGUAGES:
        raise ValueError(
            f"Unsupported language: '{language}'. "
            f"Supported: {list(SUPPORTED_LANGUAGES.keys())}"
        )
    return SUPPORTED_LANGUAGES[language]


def list_languages() -> list[dict]:
    """Return safe public-facing language list (no internal paths)."""
    result = []
    for code, cfg in SUPPORTED_LANGUAGES.items():
        result.append({
            "code": code,
            "display_name": cfg["display_name"],
            "file_extension": cfg["file_extension"],
            "default_starter_code": DEFAULT_STARTER_CODE.get(code, ""),
        })
    return result
