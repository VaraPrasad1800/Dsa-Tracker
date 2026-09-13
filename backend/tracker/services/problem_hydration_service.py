"""
Universal Problem Contract Hydration Service.

Automatically transforms unconfigured / empty problems into fully configured,
JUDGE_READY problems with:
1. Rich problem description, structured examples, constraints
2. Canonical function signature (class_name, function_name, parameters_meta, return_type)
3. Visible and hidden TestCase records
4. Multi-language starter code templates and execution harnesses (Python, C++, Java, C)
5. Canonical contract evaluation and readiness synchronization

Works completely generically across the dataset without question-specific hardcoding.
"""
import re
import json
import logging
from typing import Optional, Tuple, Dict, Any, List

from django.db import transaction
from tracker.models import Problem, TestCase, LanguageTemplate, Solution
from tracker.scraper import fetch_solution
from tracker.services.problem_contract_service import (
    extract_signature_from_code,
    evaluate_problem_contract,
)

logger = logging.getLogger(__name__)


def extract_input_arguments(raw_input: str) -> str:
    """
    Parses problem statement example input into newline-separated stdin arguments.
    Handles 'param1 = val1, param2 = val2' assignments as well as single arguments.
    """
    raw = (raw_input or '').strip()
    if not raw:
        return ""

    if '=' in raw:
        pattern = r'(?:^|,\s*)([a-zA-Z_][a-zA-Z0-9_]*)\s*='
        splits = list(re.finditer(pattern, raw))
        if splits:
            values = []
            for i, match in enumerate(splits):
                start = match.end()
                end = splits[i + 1].start() if i + 1 < len(splits) else len(raw)
                val = raw[start:end].strip().rstrip(',').strip()
                values.append(val)
            return '\n'.join(values)

    return raw


def clean_output_value(raw_output: str) -> str:
    """Normalizes output string to pure return value."""
    from tracker.judge.canonical_serialization import clean_raw_output_text
    return clean_raw_output_text(raw_output)


INLINE_EXAMPLE_PATTERN = re.compile(
    r'Input:\s*(?P<input>.*?)\s*Output:\s*(?P<output>.*?)(?=(?:Explanation\s*[:\n]|Example\s*\d*:|Input\s*:|Constraints\s*:|$))',
    re.IGNORECASE | re.DOTALL
)


def extract_examples_from_description(text: str) -> List[Dict[str, str]]:
    """
    Extracts structured examples from unstructured problem descriptions
    matching standard 'Input: ... Output: ...' sections.
    """
    if not text:
        return []
    matches = list(INLINE_EXAMPLE_PATTERN.finditer(text))
    extracted = []
    for m in matches:
        raw_inp = m.group('input').strip()
        raw_out = m.group('output').strip()
        if raw_inp and raw_out:
            extracted.append({
                'input': raw_inp,
                'output': raw_out,
                'explanation': '',
            })
    return extracted


def generate_input_format(meta: dict, examples: list) -> str:
    """Generates human-readable specification of standard input format."""
    params = meta.get('parameters_meta') or []
    if not params:
        if examples and examples[0].get('input'):
            raw = examples[0]['input'].strip()
            return f"Input is provided via standard input (stdin) matching the problem examples:\n{raw}"
        return "Input is provided via standard input (stdin) as specified in the problem examples."

    lines = ["Standard Input contains:"]
    line_num = 1
    for p in params:
        name = p.get('name', f'arg{line_num}')
        ptype = p.get('type', 'value').lower()
        if 'list[list' in ptype or 'vector<vector' in ptype:
            lines.append(f"- Line {line_num}: `R C` (number of rows and columns for `{name}`)")
            line_num += 1
            lines.append(f"- Next `R` lines: row elements of `{name}`")
        elif 'list' in ptype or 'vector' in ptype:
            lines.append(f"- Line {line_num}: `N` (size of array `{name}`)")
            line_num += 1
            lines.append(f"- Line {line_num}: `{name}` ({p.get('type', 'array')}, space-separated elements)")
            line_num += 1
        elif 'str' in ptype:
            lines.append(f"- Line {line_num}: `{name}` (string)")
            line_num += 1
        elif 'int' in ptype:
            lines.append(f"- Line {line_num}: `{name}` (integer)")
            line_num += 1
        elif 'bool' in ptype:
            lines.append(f"- Line {line_num}: `{name}` (boolean: `true` or `false`)")
            line_num += 1
        elif 'float' in ptype or 'double' in ptype:
            lines.append(f"- Line {line_num}: `{name}` (floating-point number)")
            line_num += 1
        else:
            lines.append(f"- Line {line_num}: `{name}`")
            line_num += 1

    return "\n".join(lines)


def generate_output_format(meta: dict, examples: list) -> str:
    """Generates human-readable specification of standard output format."""
    ret_type = (meta.get('return_type') or '').lower()
    if 'bool' in ret_type:
        return "Print `true` or `false` to standard output (stdout)."
    if 'list' in ret_type or 'vector' in ret_type:
        return "Print the resulting array to standard output (stdout), formatted as a JSON array (e.g. `[0, 1]`) or space-separated elements."
    if 'str' in ret_type:
        return "Print the string result to standard output (stdout)."
    if 'int' in ret_type or 'long' in ret_type:
        return "Print the integer result to standard output (stdout)."
    if 'float' in ret_type or 'double' in ret_type:
        return "Print the numeric result to standard output (stdout)."

    if examples and examples[0].get('output'):
        out_ex = examples[0]['output'].strip()
        return f"Print the expected result to standard output (stdout) matching example format: `{out_ex}`"

    return "Print the result to standard output (stdout)."


# ---------------------------------------------------------------------------
# Template & Harness Builders (Complete Programs for STDIN / STDOUT)
# ---------------------------------------------------------------------------

def _build_python(meta: dict, code_by_lang: dict) -> Tuple[str, str]:
    cls_name = meta.get('class_name') or 'Solution'
    fn_name = meta.get('function_name') or 'solve'
    params = meta.get('parameters_meta') or []

    code_lines = [
        "import sys",
        "",
        "def solve():",
        "    tokens = sys.stdin.read().split()",
        "    if not tokens:",
        "        return",
        "",
    ]

    if not params:
        code_lines.extend([
            "    # Read input from standard input",
            "    # Write output to standard output",
            "",
        ])
    elif len(params) == 1:
        p0 = params[0]
        pname = p0.get('name', 's')
        ptype = p0.get('type', '').lower()
        if 'str' in ptype:
            code_lines.extend([
                f"    {pname} = tokens[0]",
                f"    if {pname}.startswith('\"') and {pname}.endswith('\"') and len({pname}) >= 2:",
                f"        {pname} = {pname}[1:-1]",
                "",
                "    # TODO: Implement your solution here",
                "    # print(result)",
                "",
            ])
        elif 'list' in ptype or 'vector' in ptype:
            code_lines.extend([
                "    n = int(tokens[0])",
                f"    {pname} = [int(x) for x in tokens[1:n + 1]]",
                "",
                "    # TODO: Implement your solution here",
                "    # print(result)",
                "",
            ])
        elif 'int' in ptype:
            code_lines.extend([
                f"    {pname} = int(tokens[0])",
                "",
                "    # TODO: Implement your solution here",
                "    # print(result)",
                "",
            ])
        elif 'float' in ptype or 'double' in ptype:
            code_lines.extend([
                f"    {pname} = float(tokens[0])",
                "",
                "    # TODO: Implement your solution here",
                "    # print(result)",
                "",
            ])
        else:
            code_lines.extend([
                f"    {pname} = tokens[0]",
                "",
                "    # TODO: Implement your solution here",
                "",
            ])
    else:
        code_lines.extend([
            "    it = 0",
            "    # Parse inputs",
        ])
        for i, p in enumerate(params):
            pname = p.get('name', f'arg{i+1}')
            ptype = p.get('type', '').lower()
            if 'list[list' in ptype or 'vector<vector' in ptype:
                code_lines.extend([
                    f"    r_{pname} = int(tokens[it]); c_{pname} = int(tokens[it + 1]); it += 2",
                    f"    {pname} = [[int(tokens[it + r_idx * c_{pname} + c_idx]) for c_idx in range(c_{pname})] for r_idx in range(r_{pname})]",
                    f"    it += r_{pname} * c_{pname}",
                ])
            elif 'list' in ptype or 'vector' in ptype:
                code_lines.extend([
                    f"    n_{pname} = int(tokens[it]); it += 1",
                    f"    {pname} = [int(tokens[it + i]) for i in range(n_{pname})]; it += n_{pname}",
                ])
            elif 'int' in ptype:
                code_lines.append(f"    {pname} = int(tokens[it]); it += 1")
            elif 'float' in ptype or 'double' in ptype:
                code_lines.append(f"    {pname} = float(tokens[it]); it += 1")
            elif 'bool' in ptype:
                code_lines.append(f"    {pname} = tokens[it].lower() == 'true'; it += 1")
            elif 'str' in ptype:
                code_lines.extend([
                    f"    {pname} = tokens[it]; it += 1",
                    f"    if {pname}.startswith('\"') and {pname}.endswith('\"') and len({pname}) >= 2:",
                    f"        {pname} = {pname}[1:-1]",
                ])
            else:
                code_lines.append(f"    {pname} = tokens[it]; it += 1")

        code_lines.extend([
            "",
            "    # TODO: Implement your solution here",
            "    # print(result)",
            "",
        ])

    code_lines.extend([
        "if __name__ == '__main__':",
        "    solve()",
        "",
    ])
    starter = "\n".join(code_lines)

    harness_parse_blocks = []
    if not params:
        harness_parse_blocks.append("    args = [l.strip() for l in raw.splitlines() if l.strip()]")
    else:
        harness_parse_blocks.append("    it = 0")
        harness_parse_blocks.append("    args = []")
        for i, p in enumerate(params):
            pname = p.get('name', f'arg{i+1}')
            ptype = p.get('type', '').lower()
            if 'list[list' in ptype or 'vector<vector' in ptype:
                harness_parse_blocks.extend([
                    "    r = int(tokens[it]); c = int(tokens[it + 1]); it += 2",
                    "    args.append([[int(tokens[it + r_i * c + c_j]) for c_j in range(c)] for r_i in range(r)])",
                    "    it += r * c",
                ])
            elif 'list' in ptype or 'vector' in ptype:
                harness_parse_blocks.extend([
                    "    n = int(tokens[it]); it += 1",
                    "    args.append([int(tokens[it + k]) for k in range(n)])",
                    "    it += n",
                ])
            elif 'int' in ptype:
                harness_parse_blocks.append("    args.append(int(tokens[it])); it += 1")
            elif 'float' in ptype or 'double' in ptype:
                harness_parse_blocks.append("    args.append(float(tokens[it])); it += 1")
            elif 'bool' in ptype:
                harness_parse_blocks.append("    args.append(tokens[it].lower() == 'true'); it += 1")
            elif 'str' in ptype:
                harness_parse_blocks.extend([
                    "    s_val = tokens[it]; it += 1",
                    "    if s_val.startswith('\"') and s_val.endswith('\"') and len(s_val) >= 2: s_val = s_val[1:-1]",
                    "    args.append(s_val)",
                ])
            else:
                harness_parse_blocks.append("    args.append(tokens[it]); it += 1")

    harness_parse_code = "\n".join(harness_parse_blocks)

    harness = (
        f"if __name__ == '__main__':\n"
        f"    import sys, json\n\n"
        f"    raw = sys.stdin.read().strip()\n"
        f"    if not raw:\n"
        f"        sys.exit(0)\n"
        f"    tokens = raw.split()\n"
        f"    sol = {cls_name}()\n"
        f"    fn = getattr(sol, '{fn_name}', None)\n"
        f"    if fn is None:\n"
        f"        sys.exit(0)\n"
        f"{harness_parse_code}\n"
        f"    res = fn(*args)\n"
        f"    if res is True:\n"
        f"        print('true')\n"
        f"    elif res is False:\n"
        f"        print('false')\n"
        f"    elif res is None:\n"
        f"        print('null')\n"
        f"    elif isinstance(res, list):\n"
        f"        if res and isinstance(res[0], list):\n"
        f"            for row in res: print(' '.join(str(x) for x in row))\n"
        f"        else:\n"
        f"            print(' '.join(str(x) for x in res))\n"
        f"    elif isinstance(res, dict):\n"
        f"        print(json.dumps(res, separators=(',', ':')))\n"
        f"    else:\n"
        f"        print(res)\n"
    )
    return starter, harness


def _build_cpp(meta: dict, code_by_lang: dict) -> Tuple[str, str]:
    params = meta.get('parameters_meta') or []

    code_lines = [
        "#include <iostream>",
        "#include <vector>",
        "#include <string>",
        "#include <algorithm>",
        "",
        "using namespace std;",
        "",
        "int main() {",
        "    ios_base::sync_with_stdio(false);",
        "    cin.tie(NULL);",
        "",
    ]

    if not params:
        code_lines.extend([
            "    // Read input from standard input",
            "    // Write output to standard output",
            "",
            "    return 0;",
            "}",
            "",
        ])
    elif len(params) == 1:
        p0 = params[0]
        pname = p0.get('name', 's')
        ptype = p0.get('type', '').lower()
        if 'list[list' in ptype or 'vector<vector' in ptype:
            code_lines.extend([
                "    int r, c;",
                "    if (cin >> r >> c) {",
                f"        vector<vector<int>> {pname}(r, vector<int>(c));",
                "        for (int i = 0; i < r; ++i) {",
                "            for (int j = 0; j < c; ++j) {",
                f"                cin >> {pname}[i][j];",
                "            }",
                "        }",
                "",
                "        // TODO: Implement your solution here",
                "",
                "    }",
                "    return 0;",
                "}",
                "",
            ])
        elif 'list' in ptype or 'vector' in ptype:
            code_lines.extend([
                "    int n;",
                "    if (cin >> n) {",
                f"        vector<int> {pname}(n);",
                f"        for (int i = 0; i < n; ++i) cin >> {pname}[i];",
                "",
                "        // TODO: Implement your solution here",
                "",
                "    }",
                "    return 0;",
                "}",
                "",
            ])
        elif 'str' in ptype:
            code_lines.extend([
                f"    string {pname};",
                f"    if (cin >> {pname}) {{",
                f"        if ({pname}.size() >= 2 && {pname}.front() == '\"' && {pname}.back() == '\"') {{",
                f"            {pname} = {pname}.substr(1, {pname}.size() - 2);",
                f"        }}",
                "        // TODO: Implement your solution here",
                "",
                "    }",
                "    return 0;",
                "}",
                "",
            ])
        elif 'int' in ptype:
            code_lines.extend([
                f"    int {pname};",
                f"    if (cin >> {pname}) {{",
                "        // TODO: Implement your solution here",
                "",
                "    }",
                "    return 0;",
                "}",
                "",
            ])
        elif 'float' in ptype or 'double' in ptype:
            code_lines.extend([
                f"    double {pname};",
                f"    if (cin >> {pname}) {{",
                "        // TODO: Implement your solution here",
                "",
                "    }",
                "    return 0;",
                "}",
                "",
            ])
        else:
            code_lines.extend([
                f"    string {pname};",
                f"    if (cin >> {pname}) {{",
                "        // TODO: Implement your solution here",
                "",
                "    }",
                "    return 0;",
                "}",
                "",
            ])
    else:
        code_lines.append("    // Parse inputs")
        for i, p in enumerate(params):
            pname = p.get('name', f'arg{i+1}')
            ptype = p.get('type', '').lower()
            if 'list[list' in ptype or 'vector<vector' in ptype:
                code_lines.extend([
                    f"    int r_{pname}, c_{pname};",
                    f"    if (!(cin >> r_{pname} >> c_{pname})) return 0;",
                    f"    vector<vector<int>> {pname}(r_{pname}, vector<int>(c_{pname}));",
                    f"    for (int i = 0; i < r_{pname}; ++i) for (int j = 0; j < c_{pname}; ++j) cin >> {pname}[i][j];",
                ])
            elif 'list' in ptype or 'vector' in ptype:
                code_lines.extend([
                    f"    int n_{pname};",
                    f"    if (!(cin >> n_{pname})) return 0;",
                    f"    vector<int> {pname}(n_{pname});",
                    f"    for (int i = 0; i < n_{pname}; ++i) cin >> {pname}[i];",
                ])
            elif 'int' in ptype:
                code_lines.append(f"    int {pname}; if (!(cin >> {pname})) return 0;")
            elif 'float' in ptype or 'double' in ptype:
                code_lines.append(f"    double {pname}; if (!(cin >> {pname})) return 0;")
            elif 'str' in ptype:
                code_lines.extend([
                    f"    string {pname}; if (!(cin >> {pname})) return 0;",
                    f"    if ({pname}.size() >= 2 && {pname}.front() == '\"' && {pname}.back() == '\"') {pname} = {pname}.substr(1, {pname}.size() - 2);",
                ])
            elif 'bool' in ptype:
                code_lines.extend([
                    f"    string raw_{pname}; if (!(cin >> raw_{pname})) return 0;",
                    f"    bool {pname} = (raw_{pname} == \"true\" || raw_{pname} == \"1\");",
                ])
            else:
                code_lines.append(f"    string {pname}; if (!(cin >> {pname})) return 0;")

        code_lines.extend([
            "",
            "    // TODO: Implement your solution here",
            "",
            "    return 0;",
            "}",
            "",
        ])

    starter = "\n".join(code_lines)
    return starter, ""


def _build_java(meta: dict, code_by_lang: dict) -> Tuple[str, str]:
    params = meta.get('parameters_meta') or []
    code_lines = [
        "import java.util.*;",
        "import java.io.*;",
        "",
        "public class Main {",
        "    public static void main(String[] args) {",
        "        Scanner sc = new Scanner(System.in);",
        "        if (!sc.hasNext()) return;",
        "",
    ]
    if not params:
        code_lines.extend([
            "        // Read input from standard input",
            "        // Write output to standard output",
            "    }",
            "}",
            "",
        ])
    elif len(params) == 1:
        p0 = params[0]
        pname = p0.get('name', 's')
        ptype = p0.get('type', '').lower()
        if 'list[list' in ptype or 'vector<vector' in ptype:
            code_lines.extend([
                "        int r = sc.nextInt();",
                "        int c = sc.nextInt();",
                f"        int[][] {pname} = new int[r][c];",
                "        for (int i = 0; i < r; i++) {",
                "            for (int j = 0; j < c; j++) {",
                f"                {pname}[i][j] = sc.nextInt();",
                "            }",
                "        }",
                "",
                "        // TODO: Implement your solution here",
                "    }",
                "}",
                "",
            ])
        elif 'list' in ptype or 'vector' in ptype:
            code_lines.extend([
                "        int n = sc.nextInt();",
                f"        int[] {pname} = new int[n];",
                f"        for (int i = 0; i < n; i++) {pname}[i] = sc.nextInt();",
                "",
                "        // TODO: Implement your solution here",
                "    }",
                "}",
                "",
            ])
        elif 'str' in ptype:
            code_lines.extend([
                f"        String {pname} = sc.next().trim();",
                f"        if ({pname}.startsWith(\"\\\"\") && {pname}.endsWith(\"\\\"\") && {pname}.length() >= 2) {{",
                f"            {pname} = {pname}.substring(1, {pname}.length() - 1);",
                "        }",
                "",
                "        // TODO: Implement your solution here",
                "    }",
                "}",
                "",
            ])
        elif 'int' in ptype:
            code_lines.extend([
                f"        int {pname} = sc.nextInt();",
                "",
                "        // TODO: Implement your solution here",
                "    }",
                "}",
                "",
            ])
        elif 'float' in ptype or 'double' in ptype:
            code_lines.extend([
                f"        double {pname} = sc.nextDouble();",
                "",
                "        // TODO: Implement your solution here",
                "    }",
                "}",
                "",
            ])
        else:
            code_lines.extend([
                f"        String {pname} = sc.next();",
                "",
                "        // TODO: Implement your solution here",
                "    }",
                "}",
                "",
            ])
    else:
        code_lines.append("        // Parse inputs")
        for i, p in enumerate(params):
            pname = p.get('name', f'arg{i+1}')
            ptype = p.get('type', '').lower()
            if 'list[list' in ptype or 'vector<vector' in ptype:
                code_lines.extend([
                    f"        int r_{pname} = sc.nextInt(); int c_{pname} = sc.nextInt();",
                    f"        int[][] {pname} = new int[r_{pname}][c_{pname}];",
                    f"        for (int i = 0; i < r_{pname}; i++) for (int j = 0; j < c_{pname}; j++) {pname}[i][j] = sc.nextInt();",
                ])
            elif 'list' in ptype or 'vector' in ptype:
                code_lines.extend([
                    f"        int n_{pname} = sc.nextInt();",
                    f"        int[] {pname} = new int[n_{pname}];",
                    f"        for (int i = 0; i < n_{pname}; i++) {pname}[i] = sc.nextInt();",
                ])
            elif 'int' in ptype:
                code_lines.append(f"        int {pname} = sc.nextInt();")
            elif 'float' in ptype or 'double' in ptype:
                code_lines.append(f"        double {pname} = sc.nextDouble();")
            elif 'str' in ptype:
                code_lines.extend([
                    f"        String {pname} = sc.next();",
                    f"        if ({pname}.startsWith(\"\\\"\") && {pname}.endsWith(\"\\\"\") && {pname}.length() >= 2) {pname} = {pname}.substring(1, {pname}.length() - 1);",
                ])
            elif 'bool' in ptype:
                code_lines.append(f"        boolean {pname} = sc.next().equalsIgnoreCase(\"true\");")
            else:
                code_lines.append(f"        String {pname} = sc.next();")

        code_lines.extend([
            "",
            "        // TODO: Implement your solution here",
            "    }",
            "}",
            "",
        ])

    starter = "\n".join(code_lines)
    return starter, ""


def _build_c(meta: dict, code_by_lang: dict) -> Tuple[str, str]:
    params = meta.get('parameters_meta') or []
    code_lines = [
        "#include <stdio.h>",
        "#include <stdlib.h>",
        "#include <string.h>",
        "#include <stdbool.h>",
        "",
        "int main() {",
    ]
    if not params:
        code_lines.extend([
            "    // Read input from standard input",
            "    // Write output to standard output",
            "    return 0;",
            "}",
            "",
        ])
    elif len(params) == 1:
        p0 = params[0]
        pname = p0.get('name', 's')
        ptype = p0.get('type', '').lower()
        if 'list' in ptype or 'vector' in ptype:
            code_lines.extend([
                "    int n;",
                "    if (scanf(\"%d\", &n) != 1) return 0;",
                f"    int *{pname} = (int *)malloc(n * sizeof(int));",
                f"    for (int i = 0; i < n; i++) scanf(\"%d\", &{pname}[i]);",
                "",
                "    // TODO: Implement your solution here",
                "",
                f"    free({pname});",
                "    return 0;",
                "}",
                "",
            ])
        elif 'str' in ptype:
            code_lines.extend([
                f"    char {pname}[65536];",
                f"    if (scanf(\"%s\", {pname}) != 1) return 0;",
                f"    char *p = {pname};",
                "    if (*p == '\"') {",
                "        p++;",
                "        int len = strlen(p);",
                "        if (len > 0 && p[len - 1] == '\"') p[len - 1] = '\\0';",
                "    }",
                "",
                "    // TODO: Implement your solution here",
                "",
                "    return 0;",
                "}",
                "",
            ])
        elif 'int' in ptype:
            code_lines.extend([
                f"    int {pname};",
                f"    if (scanf(\"%d\", &n) != 1) return 0;",
                "",
                "    // TODO: Implement your solution here",
                "",
                "    return 0;",
                "}",
                "",
            ])
        else:
            code_lines.extend([
                "    // Read input from standard input",
                "    // Write output to standard output",
                "    return 0;",
                "}",
                "",
            ])
    else:
        arrays_to_free = []
        for i, p in enumerate(params):
            pname = p.get('name', f'arg{i+1}')
            ptype = p.get('type', '').lower()
            if 'list' in ptype or 'vector' in ptype:
                code_lines.extend([
                    f"    int n_{pname};",
                    f"    if (scanf(\"%d\", &n_{pname}) != 1) return 0;",
                    f"    int *{pname} = (int *)malloc(n_{pname} * sizeof(int));",
                    f"    for (int i = 0; i < n_{pname}; i++) scanf(\"%d\", &{pname}[i]);",
                ])
                arrays_to_free.append(pname)
            elif 'int' in ptype:
                code_lines.append(f"    int {pname}; scanf(\"%d\", &{pname});")
            elif 'float' in ptype or 'double' in ptype:
                code_lines.append(f"    double {pname}; scanf(\"%lf\", &{pname});")
            elif 'str' in ptype:
                code_lines.extend([
                    f"    char {pname}[65536]; scanf(\"%s\", {pname});",
                    f"    if ({pname}[0] == '\"') {{",
                    f"        int len = strlen({pname});",
                    f"        if (len > 1 && {pname}[len - 1] == '\"') {pname}[len - 1] = '\\0';",
                    f"        memmove({pname}, {pname} + 1, len);",
                    f"    }}",
                ])
            else:
                code_lines.append(f"    char {pname}[65536]; scanf(\"%s\", {pname});")

        code_lines.extend([
            "",
            "    // TODO: Implement your solution here",
            "",
        ])
        for arr in arrays_to_free:
            code_lines.append(f"    free({arr});")
        code_lines.extend([
            "    return 0;",
            "}",
            "",
        ])

    starter = "\n".join(code_lines)
    return starter, ""


# ---------------------------------------------------------------------------
# Core Hydration Pipeline
# ---------------------------------------------------------------------------

@transaction.atomic
def hydrate_problem_contract(problem: Problem, force: bool = False, fetched_data: Optional[dict] = None) -> Tuple[Problem, bool, str]:
    """
    Hydrate a problem's contract, description, examples, test cases, and multi-language templates.

    Returns:
        (problem, success: bool, message: str)
    """
    if problem.is_judge_ready and not force:
        return problem, True, "Already judge ready"

    if not problem.leetcode_id:
        contract_info = evaluate_problem_contract(problem)
        return problem, False, f"Missing leetcode_id: {contract_info.get('missing_configuration')}"

    # 1. Fetch solution & statement data (or reuse pre-fetched or existing local DB data)
    if fetched_data is not None:
        fetched = fetched_data
    else:
        existing_sol = Solution.objects.filter(problem=problem).first()
        if problem.description and existing_sol:
            fetched = {
                'title': problem.title,
                'description': problem.description,
                'examples': problem.examples or [],
                'constraints': problem.constraints or [],
                'code': existing_sol.code or '',
                'code_by_language': existing_sol.code_by_language or {},
                'language': existing_sol.language or 'python',
                'explanation': existing_sol.explanation or '',
                'time_complexity': existing_sol.time_complexity or '',
                'space_complexity': existing_sol.space_complexity or '',
                'source_url': existing_sol.source_url or '',
                'solution_source_url': existing_sol.solution_source_url or '',
                'question_number': existing_sol.question_number or problem.question_number,
            }
        else:
            fetched = fetch_solution(problem.leetcode_id)

    if not fetched:
        contract_info = evaluate_problem_contract(problem)
        return problem, False, f"External solution unavailable: {contract_info.get('missing_configuration')}"

    # Update description & title if missing
    if fetched.get('description'):
        problem.description = fetched['description']
    if fetched.get('examples'):
        problem.examples = fetched['examples']
    if fetched.get('constraints'):
        problem.constraints = fetched['constraints']
    if fetched.get('title') and (not problem.title or problem.title.startswith('LeetCode ')):
        problem.title = fetched['title']

    # 2. Persist / Update Solution record
    code_by_lang = fetched.get('code_by_language') or {}
    Solution.objects.update_or_create(
        problem=problem,
        defaults={
            'question_number': fetched.get('question_number') or problem.leetcode_id or problem.question_number,
            'title': problem.title,
            'description': problem.description,
            'code': fetched.get('code') or '',
            'code_by_language': code_by_lang,
            'language': fetched.get('language') or 'python',
            'explanation': fetched.get('explanation') or '',
            'time_complexity': fetched.get('time_complexity') or '',
            'space_complexity': fetched.get('space_complexity') or '',
            'fetch_failed': False,
            'source_url': fetched.get('source_url') or '',
            'solution_source_url': fetched.get('solution_source_url') or '',
        }
    )

    # 3. Extract Signature across languages
    sig_meta = extract_signature_from_code(code_by_lang)
    fn_name = sig_meta.get('function_name')
    if not fn_name:
        # Fallback: if signature could not be extracted from code tabs, try to extract from description
        pass

    if fn_name:
        problem.class_name = sig_meta.get('class_name') or 'Solution'
        problem.function_name = fn_name
        problem.parameters_meta = sig_meta.get('parameters_meta') or []
        problem.return_type = sig_meta.get('return_type') or ''

    # Fallback to inline examples from description if structured examples are empty or invalid
    has_valid_examples = any(
        (ex.get('input') or '').strip() and (ex.get('output') or '').strip()
        for ex in (problem.examples or [])
    )
    if not has_valid_examples and problem.description:
        extracted_inline = extract_examples_from_description(problem.description)
        if extracted_inline:
            problem.examples = extracted_inline

    problem.execution_mode = 'STDIN_STDOUT'
    problem.input_format = generate_input_format(sig_meta, problem.examples)
    problem.output_format = generate_output_format(sig_meta, problem.examples)

    # 4. Generate TestCases from parsed examples using canonical serialization
    raw_examples = problem.examples or []
    if raw_examples:
        from tracker.judge.canonical_serialization import (
            parse_example_arguments,
            serialize_to_stdin,
            serialize_to_expected_stdout,
            determine_output_checker,
        )

        # Determine output_checker strategy from problem semantics
        checker_strategy = determine_output_checker(
            problem_desc=problem.description or '',
            return_type=sig_meta.get('return_type', ''),
            examples=raw_examples,
        )
        problem.output_checker = checker_strategy

        # Clear existing test cases to replace with fresh structured ones
        TestCase.objects.filter(problem=problem).delete()

        created_cases = []
        for idx, ex in enumerate(raw_examples):
            raw_inp = ex.get('input', '')
            raw_out = ex.get('output', '')

            # Canonical STDIN: parse named arguments, serialize without brackets
            try:
                args = parse_example_arguments(raw_inp)
                inp_text = serialize_to_stdin(args) if args else raw_inp.strip()
            except Exception:
                inp_text = raw_inp.strip()

            # Canonical STDOUT: parse and serialize to space-separated
            try:
                out_text = serialize_to_expected_stdout(raw_out, sig_meta.get('return_type', ''))
            except Exception:
                out_text = raw_out.strip()

            if not inp_text or not out_text:
                continue

            # If 2 examples: idx 0 visible, idx 1 hidden
            # If >= 3 examples: idx 0, 1 visible, idx >= 2 hidden
            cutoff = 1 if len(raw_examples) == 2 else 2
            is_hidden = idx >= cutoff
            tc = TestCase(
                problem=problem,
                input_text=inp_text,
                expected_output=out_text,
                is_hidden=is_hidden,
                order=len(created_cases) + 1,
            )
            created_cases.append(tc)

        # If only 1 example exists, synthesize a hidden variation using same I/O
        if len(created_cases) == 1:
            first_case = created_cases[0]
            first_case.is_hidden = False
            created_cases.append(
                TestCase(
                    problem=problem,
                    input_text=first_case.input_text,
                    expected_output=first_case.expected_output,
                    is_hidden=True,
                    order=2,
                )
            )
        elif created_cases:
            has_visible = any(not c.is_hidden for c in created_cases)
            has_hidden = any(c.is_hidden for c in created_cases)
            if not has_hidden:
                created_cases[-1].is_hidden = True
            if not has_visible:
                created_cases[0].is_hidden = False

        # Bulk create test cases
        if created_cases:
            TestCase.objects.bulk_create(created_cases)

    # 5. Generate Language Templates (Python, C++, Java, C)
    py_starter, py_harness = _build_python(sig_meta, code_by_lang)
    LanguageTemplate.objects.update_or_create(
        problem=problem, language='python',
        defaults={'starter_code': py_starter, 'harness_code': py_harness}
    )

    cpp_starter, cpp_harness = _build_cpp(sig_meta, code_by_lang)
    LanguageTemplate.objects.update_or_create(
        problem=problem, language='cpp',
        defaults={'starter_code': cpp_starter, 'harness_code': cpp_harness}
    )

    java_starter, java_harness = _build_java(sig_meta, code_by_lang)
    LanguageTemplate.objects.update_or_create(
        problem=problem, language='java',
        defaults={'starter_code': java_starter, 'harness_code': java_harness}
    )

    c_starter, c_harness = _build_c(sig_meta, code_by_lang)
    LanguageTemplate.objects.update_or_create(
        problem=problem, language='c',
        defaults={'starter_code': c_starter, 'harness_code': c_harness}
    )

    # 6. Set default time and memory limits if not present
    if problem.time_limit_ms is None:
        from tracker.judge.judge_config import DEFAULT_TIME_LIMIT_BY_DIFFICULTY
        problem.time_limit_ms = DEFAULT_TIME_LIMIT_BY_DIFFICULTY.get(problem.difficulty, 2000)
    if problem.memory_limit_mb is None:
        from tracker.judge.judge_config import PLATFORM_DEFAULT_MEMORY_LIMIT_MB
        problem.memory_limit_mb = PLATFORM_DEFAULT_MEMORY_LIMIT_MB

    # 7. Evaluate and commit Problem contract
    contract_info = evaluate_problem_contract(problem)
    problem.is_judge_ready = contract_info['is_judge_ready']
    problem.judge_readiness_status = contract_info['judge_readiness_status']
    problem.missing_configuration = contract_info['missing_configuration']
    problem.save()

    status_msg = "Successfully hydrated and verified JUDGE_READY" if problem.is_judge_ready else f"Hydrated with pending requirements: {problem.missing_configuration}"
    return problem, problem.is_judge_ready, status_msg
