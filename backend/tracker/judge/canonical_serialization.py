"""
Canonical Data Serialization & Output Validation Rules
======================================================
Generic, dataset-wide utilities for converting problem example data into:
1. Clean Standard Input (STDIN) without LeetCode JSON brackets or comma pollution.
2. Canonical Standard Output (STDOUT) matching the problem output specification.
3. Appropriate output validation strategy (e.g. ORDER_INSENSITIVE_ARRAY vs ARRAY).
"""

import re
import json
from typing import Any, Tuple, List, Optional


def parse_raw_value(val_str: str, type_hint: str = "") -> Any:
    """
    Safely parses a string value into a typed Python object (list, int, float, bool, str).
    """
    s = val_str.strip()
    if not s:
        return ""

    # JSON lists/dicts (e.g. "[2,7,11,15]", "[[1,2],[3,4]]")
    if s.startswith('[') and s.endswith(']'):
        try:
            return json.loads(s)
        except Exception:
            # Fallback: remove brackets and parse space/comma separated numbers
            inner = s[1:-1].replace(',', ' ')
            tokens = inner.split()
            parsed = []
            for t in tokens:
                try:
                    parsed.append(int(t))
                except ValueError:
                    try:
                        parsed.append(float(t))
                    except ValueError:
                        parsed.append(t.strip('"\''))
            return parsed

    # Boolean
    if s.lower() in ('true', 'false'):
        return s.lower() == 'true'

    # Quoted string
    if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
        return s[1:-1]

    # Integer
    try:
        return int(s)
    except ValueError:
        pass

    # Float
    try:
        return float(s)
    except ValueError:
        pass

    return s


def parse_example_arguments(raw_input: str) -> List[Tuple[str, Any]]:
    """
    Parses problem statement example input (e.g. 'nums = [2,7,11,15], target = 9')
    into a list of (param_name, parsed_value).
    """
    raw = (raw_input or '').strip()
    if not raw:
        return []

    if '=' in raw:
        pattern = r'(?:^|,\s*)([a-zA-Z_][a-zA-Z0-9_]*)\s*='
        splits = list(re.finditer(pattern, raw))
        if splits:
            params = []
            for i, match in enumerate(splits):
                pname = match.group(1)
                start = match.end()
                end = splits[i + 1].start() if i + 1 < len(splits) else len(raw)
                val_str = raw[start:end].strip().rstrip(',').strip()
                val = parse_raw_value(val_str)
                params.append((pname, val))
            return params

    # If no '=' assignment, treat as a single value or newline-separated values
    lines = raw.splitlines()
    if len(lines) > 1:
        return [(f"arg{idx+1}", parse_raw_value(l)) for idx, l in enumerate(lines) if l.strip()]
    return [("arg1", parse_raw_value(raw))]


def serialize_to_stdin(args: List[Tuple[str, Any]]) -> str:
    """
    Converts structured arguments into clean, standard input (STDIN).
    Formats:
    - 1D Array / List: length N on first line, elements space-separated on second line.
    - 2D Array / Matrix: rows R and cols C on first line, followed by rows.
    - Primitives (int, float, bool, str): single line value.
    """
    lines = []
    for pname, val in args:
        if isinstance(val, list):
            if val and isinstance(val[0], list):
                # 2D Array / Matrix
                r = len(val)
                c = len(val[0]) if r > 0 else 0
                lines.append(f"{r} {c}")
                for row in val:
                    lines.append(" ".join(str(x) for x in row))
            else:
                # 1D Array / Linked list
                n = len(val)
                lines.append(str(n))
                if n > 0:
                    lines.append(" ".join(str(x) for x in val))
                else:
                    lines.append("")
        elif isinstance(val, bool):
            lines.append("true" if val else "false")
        else:
            lines.append(str(val))

    return "\n".join(lines).strip()


def clean_raw_output_text(raw_output: str) -> str:
    """
    Strips trailing explanation, note, or clarification blocks from raw output strings.
    """
    s = (raw_output or '').strip()
    if not s:
        return ""

    # Cut off Explanation, Note, Because, Clarification, Example
    cutoff_pattern = re.compile(
        r'(?:\r?\n\s*|\s+)(?:Explanation|Note|Because|Clarification|Example)\s*[:\n][\s\S]*$',
        re.IGNORECASE
    )
    s = cutoff_pattern.sub('', s).strip()

    # Handle 'Return X, and...' patterns
    ret_match = re.match(r'^return\s+([^\s,]+)', s, re.IGNORECASE)
    if ret_match and (ret_match.group(1).isdigit() or ret_match.group(1).lower() in ('true', 'false')):
        return ret_match.group(1)

    return s


def serialize_to_expected_stdout(raw_output: str, type_hint: str = "") -> str:
    """
    Converts raw example output (e.g. '[0, 1]' or 'true') into canonical expected STDOUT.
    - 1D array: space-separated elements (e.g. '0 1', '2 1 4 3 5')
    - boolean: 'true' or 'false'
    - primitive: stripped string
    """
    cleaned = clean_raw_output_text(raw_output)
    val = parse_raw_value(cleaned, type_hint)
    if isinstance(val, list):
        if val and isinstance(val[0], list):
            # 2D array
            return "\n".join(" ".join(str(x) for x in row) for row in val)
        return " ".join(str(x) for x in val)
    if isinstance(val, bool):
        return "true" if val else "false"
    return str(val).strip()


def determine_output_checker(problem_desc: str, return_type: str = "", examples: list = None) -> str:
    """
    Determines the appropriate output validation strategy from problem semantics.
    """
    desc_lower = (problem_desc or "").lower()
    ret_lower = (return_type or "").lower()

    # If problem description explicitly permits any order:
    if "in any order" in desc_lower or "any order" in desc_lower or "return the answer in any order" in desc_lower:
        return "ORDER_INSENSITIVE_ARRAY"

    if "bool" in ret_lower:
        return "BOOLEAN"

    if "float" in ret_lower or "double" in ret_lower:
        return "FLOAT_WITH_TOLERANCE"

    if "list" in ret_lower or "vector" in ret_lower:
        return "ARRAY"

    if "int" in ret_lower or "long" in ret_lower:
        return "INTEGER"

    # Infer from example output if return_type is empty
    if examples and examples[0].get('output'):
        out_s = examples[0]['output'].strip()
        if out_s.startswith('[') and out_s.endswith(']'):
            return "ARRAY"
        if out_s.lower() in ('true', 'false'):
            return "BOOLEAN"
        try:
            int(out_s)
            return "INTEGER"
        except ValueError:
            pass

    return "NORMALIZED_TEXT"
