"""
Problem Contract Service
========================
Defines and evaluates the Canonical Problem Contract for the Online Judge.

Canonical Problem Contract Rules:
A problem is JUDGE_READY if and only if:
1. execution_mode is defined ('FUNCTION' or 'STDIN_STDOUT').
2. For 'FUNCTION' mode:
   - function_name is non-empty.
   - class_name is non-empty (default 'Solution').
3. At least one visible test case exists (TestCase with is_hidden=False).
4. At least one hidden test case exists (TestCase with is_hidden=True).
5. Starter code templates exist for Python and C++ (or Java) with non-empty starter_code,
   and for FUNCTION mode, non-empty harness_code.

If any prerequisite is missing, the problem is classified as CONFIGURATION_REQUIRED
with an explicit, human-readable list of missing prerequisites in missing_configuration.
"""

import re
import logging
from typing import Dict, Any, List, Optional
from tracker.models import Problem, TestCase, LanguageTemplate

logger = logging.getLogger(__name__)


def evaluate_problem_contract(problem: Problem, save: bool = False) -> Dict[str, Any]:
    """
    Evaluates a problem's readiness for the Online Judge against the canonical contract.
    Updates `is_judge_ready`, `judge_readiness_status`, and `missing_configuration`.
    """
    missing = []

    # 1. Execution mode & specification validation
    mode = getattr(problem, 'execution_mode', 'STDIN_STDOUT') or 'STDIN_STDOUT'
    if mode == 'FUNCTION':
        if not getattr(problem, 'function_name', '') or not problem.function_name.strip():
            missing.append("Missing target function signature")
    elif mode == 'STDIN_STDOUT':
        if not getattr(problem, 'input_format', '').strip():
            missing.append("Missing input format specification")
        if not getattr(problem, 'output_format', '').strip():
            missing.append("Missing output format specification")
    else:
        missing.append(f"Unsupported execution mode: {mode}")

    # 2. Test case validation
    visible_tests_count = TestCase.objects.filter(problem=problem, is_hidden=False).count()
    hidden_tests_count = TestCase.objects.filter(problem=problem, is_hidden=True).count()

    if visible_tests_count == 0:
        missing.append("Missing visible test cases")
    if hidden_tests_count == 0:
        missing.append("Missing hidden test cases")

    # 3. Language template validation
    templates = {
        tmpl.language: tmpl
        for tmpl in LanguageTemplate.objects.filter(problem=problem)
    }

    required_langs = ['python', 'cpp']
    missing_langs = [l for l in required_langs if l not in templates or not templates[l].starter_code.strip()]
    if missing_langs:
        missing.append(f"Missing language starter templates ({', '.join(missing_langs)})")

    if mode == 'FUNCTION':
        missing_harnesses = [
            l for l in required_langs
            if l in templates and not templates[l].harness_code.strip()
        ]
        if missing_harnesses:
            missing.append(f"Missing execution harness ({', '.join(missing_harnesses)})")

    # 4. Check for SQL/Database non-algorithmic problems
    is_database_problem = False
    if problem.tags.filter(name__iexact='Database').exists():
        is_database_problem = True
    elif TestCase.objects.filter(problem=problem, expected_output__contains='+---').exists():
        is_database_problem = True
    elif (problem.description or '').startswith('Table: ') or 'Create table If Not Exists' in (problem.description or ''):
        is_database_problem = True

    if is_database_problem:
        missing.append("Relational Database/SQL problem: algorithmic code execution is not supported")

    is_ready = len(missing) == 0
    if is_database_problem:
        status = 'NON_ALGORITHMIC_SQL'
    elif is_ready:
        status = 'JUDGE_READY'
    else:
        status = 'CONFIGURATION_REQUIRED'

    problem.is_judge_ready = is_ready
    problem.judge_readiness_status = status
    problem.missing_configuration = missing

    if save:
        problem.save(update_fields=['is_judge_ready', 'judge_readiness_status', 'missing_configuration'])

    return {
        'problem_id': str(problem.id),
        'question_number': problem.question_number,
        'title': problem.title,
        'is_judge_ready': is_ready,
        'judge_readiness_status': status,
        'missing_configuration': missing,
        'visible_tests': visible_tests_count,
        'hidden_tests': hidden_tests_count,
        'templates_available': list(templates.keys()),
    }


def extract_signature_from_code(code_by_language: Dict[str, str]) -> Dict[str, Any]:
    """
    Extracts class name, function name, parameter types/names, and return type
    from existing solution code (Python, C++, Java).
    """
    meta = {
        'class_name': 'Solution',
        'function_name': '',
        'parameters_meta': [],
        'return_type': '',
    }

    # 1. Try Python
    py_code = code_by_language.get('python', '')
    if py_code:
        # First try matching explicitly class Solution
        match = re.search(
            r'^[ \t]*class\s+Solution[\s\S]*?def\s+(?!__init__|__new__)([a-zA-Z_][a-zA-Z0-9_]*)\s*\(\s*self\s*(?:,\s*([^)]*))?\)\s*(?:->\s*([^:]+))?:',
            py_code,
            re.MULTILINE
        )
        if match:
            cls_name = 'Solution'
            fn_name, params_str, ret_type = match.groups()
        else:
            match = re.search(
                r'^[ \t]*class\s+([A-Za-z0-9_]+)[\s\S]*?def\s+(?!__init__|__new__)([a-zA-Z_][a-zA-Z0-9_]*)\s*\(\s*self\s*(?:,\s*([^)]*))?\)\s*(?:->\s*([^:]+))?:',
                py_code,
                re.MULTILINE
            )
            if match:
                cls_name, fn_name, params_str, ret_type = match.groups()
            else:
                match = re.search(
                    r'def\s+(?!__init__|__new__)([a-zA-Z_][a-zA-Z0-9_]*)\s*\(\s*self\s*(?:,\s*([^)]*))?\)\s*(?:->\s*([^:]+))?:',
                    py_code
                )
                if match:
                    fn_name, params_str, ret_type = match.groups()
                    cls_name = 'Solution'
                else:
                    cls_name = fn_name = params_str = ret_type = None

        if fn_name:
            meta['class_name'] = cls_name or 'Solution'
            meta['function_name'] = fn_name
            meta['return_type'] = (ret_type or '').strip()

            params = []
            if params_str:
                raw_params = re.split(r',\s*(?![^\[]*\])', params_str)
                for p in raw_params:
                    p = p.strip()
                    if not p:
                        continue
                    if ':' in p:
                        pname, ptype = p.split(':', 1)
                        params.append({'name': pname.strip(), 'type': ptype.strip()})
                    else:
                        params.append({'name': p, 'type': 'Any'})
            meta['parameters_meta'] = params
            return meta

    # 2. Try C++
    cpp_code = code_by_language.get('cpp', '')
    if cpp_code:
        match = re.search(
            r'^[ \t]*class\s+Solution[\s\S]*?public:\s*([\w<>:*&]+)\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(([^)]*)\)',
            cpp_code,
            re.MULTILINE
        )
        if not match:
            match = re.search(
                r'class\s+([A-Za-z0-9_]+)[\s\S]*?public:\s*([\w<>:*&]+)\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(([^)]*)\)',
                cpp_code
            )
        if match:
            if len(match.groups()) == 3:
                cls_name = 'Solution'
                ret_type, fn_name, params_str = match.groups()
            else:
                cls_name, ret_type, fn_name, params_str = match.groups()
            meta['class_name'] = cls_name or 'Solution'
            meta['function_name'] = fn_name
            meta['return_type'] = ret_type.strip()
            params = []
            if params_str:
                for p in params_str.split(','):
                    p = p.strip()
                    if p:
                        parts = p.split()
                        if len(parts) >= 2:
                            pname = parts[-1].lstrip('*&')
                            ptype = ' '.join(parts[:-1])
                            params.append({'name': pname, 'type': ptype})
                        else:
                            params.append({'name': p, 'type': 'auto'})
            meta['parameters_meta'] = params
            return meta

    # 3. Try Java
    java_code = code_by_language.get('java', '')
    if java_code:
        match = re.search(
            r'class\s+([A-Za-z0-9_]+)[\s\S]*?public\s+([\w<>\[\]]+)\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(([^)]*)\)',
            java_code
        )
        if match:
            cls_name, ret_type, fn_name, params_str = match.groups()
            meta['class_name'] = cls_name or 'Solution'
            meta['function_name'] = fn_name
            meta['return_type'] = ret_type.strip()
            params = []
            if params_str:
                for p in params_str.split(','):
                    p = p.strip()
                    if p:
                        parts = p.split()
                        if len(parts) >= 2:
                            pname = parts[-1]
                            ptype = ' '.join(parts[:-1])
                            params.append({'name': pname, 'type': ptype})
            meta['parameters_meta'] = params
            return meta

    return meta


def sync_all_problem_contracts(batch_size: int = 500) -> Dict[str, Any]:
    """
    Evaluates and synchronizes contract readiness across all problems in the database.
    Does NOT fabricate missing test cases or function signatures.
    """
    total = 0
    judge_ready_count = 0
    config_required_count = 0
    missing_breakdown: Dict[str, int] = {}

    problems = Problem.objects.all().order_by('question_number')
    to_update = []

    for problem in problems.iterator(chunk_size=batch_size):
        total += 1
        res = evaluate_problem_contract(problem, save=False)
        if res['is_judge_ready']:
            judge_ready_count += 1
        else:
            config_required_count += 1
            for reason in res['missing_configuration']:
                missing_breakdown[reason] = missing_breakdown.get(reason, 0) + 1

        to_update.append(problem)
        if len(to_update) >= batch_size:
            Problem.objects.bulk_update(
                to_update,
                ['is_judge_ready', 'judge_readiness_status', 'missing_configuration'],
                batch_size=batch_size
            )
            to_update = []

    if to_update:
        Problem.objects.bulk_update(
            to_update,
            ['is_judge_ready', 'judge_readiness_status', 'missing_configuration'],
            batch_size=batch_size
        )

    return {
        'total_problems': total,
        'judge_ready': judge_ready_count,
        'configuration_required': config_required_count,
        'missing_reasons_breakdown': missing_breakdown,
    }
