"""
clean_judge_data management command.
Sanitizes polluted test case outputs, disables judge readiness on SQL/Database problems,
and refreshes starter code templates and input formats to match canonical STDIN.
"""
import re
from django.core.management.base import BaseCommand
from django.db import transaction
from tracker.models import Problem, TestCase, LanguageTemplate
from tracker.judge.canonical_serialization import clean_raw_output_text, serialize_to_expected_stdout
from tracker.services.problem_contract_service import evaluate_problem_contract
from tracker.services.problem_hydration_service import (
    _build_python,
    _build_cpp,
    _build_java,
    _build_c,
    generate_input_format,
)

# Smart quote pairs (U+201C/U+201D and U+2018/U+2019) — these appear when
# LeetCode/import sources emit curly quotes instead of ASCII quotes.
_SMART_QUOTE_LEFT  = '\u201c'   # "
_SMART_QUOTE_RIGHT = '\u201d'   # "
_SMART_APOS_LEFT   = '\u2018'   # '
_SMART_APOS_RIGHT  = '\u2019'   # '

# Translation table: smart quotes → ASCII equivalents
_SMART_TO_ASCII = str.maketrans({
    _SMART_QUOTE_LEFT:  '"',
    _SMART_QUOTE_RIGHT: '"',
    _SMART_APOS_LEFT:   "'",
    _SMART_APOS_RIGHT:  "'",
})


def _repair_double_encoded_utf8(s: str) -> str:
    """
    Detect and repair double-encoded UTF-8 strings.

    The corruption pattern: UTF-8 multibyte sequences (e.g. e2 80 9c for U+201C)
    were decoded as if they were Latin-1, storing one Unicode codepoint per byte
    (e.g. chr(0xe2), chr(0x80), chr(0x9c)). When re-encoded to UTF-8 by Django/Python,
    these produce double-encoded sequences (c3a2 c280 c29c instead of e2 80 9c).

    Recovery: encode back to Latin-1 bytes (reversing the mis-decoding),
    then decode as UTF-8 to get the original Unicode string.

    After recovery, smart quotes (U+201C/U+201D) are normalised to ASCII " so
    that template stripping logic works correctly.
    """
    if not s:
        return s
    # Quick check: does any codepoint look like a Latin-1 encoded UTF-8 continuation?
    # Latin-1 encoded UTF-8 sequences have pairs like (0xe2, 0x80, ...) or (0xc3, 0xbf, ...)
    # A heuristic: if the string contains chr(0xe2) or chr(0xc3) adjacent to chr(0x80)
    # it is almost certainly double-encoded UTF-8.
    needs_repair = any(
        (ord(c) in (0xe2, 0xc3, 0xc2)) and i + 1 < len(s) and ord(s[i + 1]) in range(0x80, 0xc0)
        for i, c in enumerate(s)
    )
    if not needs_repair:
        return s
    try:
        repaired = s.encode('latin-1').decode('utf-8')
        # Normalise smart quotes to ASCII after repair
        repaired = repaired.translate(_SMART_TO_ASCII)
        return repaired
    except (UnicodeDecodeError, UnicodeEncodeError):
        # Cannot repair — return original (with smart-quote normalisation only)
        return s.translate(_SMART_TO_ASCII)


def _normalize_smart_quotes(s: str) -> str:
    """Replace smart/curly quotes with ASCII equivalents without double-encoding repair."""
    if not s:
        return s
    return s.translate(_SMART_TO_ASCII)


class Command(BaseCommand):
    help = "Sanitize test cases, exclude SQL problems, and re-generate language templates"

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Report without writing to database')
        parser.add_argument('--question-number', type=int, help='Only process specific problem number')

    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)
        qnum = options.get('question_number')

        self.stdout.write(f"Running clean_judge_data (dry_run={dry_run})...")

        tc_query = TestCase.objects.all()
        if qnum:
            tc_query = tc_query.filter(problem__question_number=qnum)

        # 0. Repair double-encoded UTF-8 and normalise smart quotes in test case fields.
        #    This fixes corruption where UTF-8 bytes (e.g. e2 80 9c for U+201C) were
        #    stored as raw Latin-1 codepoints, producing garbage when sent to the judge.
        #    Also strips surrounding quotes from string arguments and expected outputs.
        encoding_repaired = 0
        with transaction.atomic():
            for tc in tc_query.iterator(chunk_size=500):
                raw_in = tc.input_text or ''
                raw_out = tc.expected_output or ''
                new_input = _normalize_smart_quotes(_repair_double_encoded_utf8(raw_in))
                new_output = _normalize_smart_quotes(_repair_double_encoded_utf8(raw_out))

                # Strip surrounding quotes from lines in input_text (e.g. "cabaa" -> cabaa)
                in_lines = new_input.splitlines()
                clean_in_lines = []
                for line in in_lines:
                    s = line.strip()
                    if len(s) >= 2 and ((s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'"))):
                        s = s[1:-1]
                    clean_in_lines.append(s)
                new_input = '\n'.join(clean_in_lines)

                # Strip surrounding quotes from expected_output (e.g. "cbcabaaaaa" -> cbcabaaaaa)
                s_out = new_output.strip()
                if len(s_out) >= 2 and ((s_out.startswith('"') and s_out.endswith('"')) or (s_out.startswith("'") and s_out.endswith("'"))):
                    new_output = s_out[1:-1]

                if new_input != raw_in or new_output != raw_out:
                    encoding_repaired += 1
                    if not dry_run:
                        tc.input_text = new_input
                        tc.expected_output = new_output
                        tc.save(update_fields=['input_text', 'expected_output'])

        self.stdout.write(f"Repaired encoding/quotes in {encoding_repaired} test cases.")

        # 0b. Repair problem examples
        prob_query = Problem.objects.all()
        if qnum:
            prob_query = prob_query.filter(question_number=qnum)

        examples_repaired = 0
        with transaction.atomic():
            for p in prob_query.iterator(chunk_size=200):
                if not p.examples:
                    continue
                changed = False
                new_examples = []
                for ex in p.examples:
                    new_ex = {}
                    for k, v in ex.items():
                        if isinstance(v, str):
                            fixed_v = _normalize_smart_quotes(_repair_double_encoded_utf8(v))
                            if fixed_v != v:
                                changed = True
                            new_ex[k] = fixed_v
                        else:
                            new_ex[k] = v
                    new_examples.append(new_ex)
                if changed:
                    examples_repaired += 1
                    if not dry_run:
                        p.examples = new_examples
                        p.save(update_fields=['examples'])

        self.stdout.write(f"Repaired double-encoded UTF-8 in examples for {examples_repaired} problems.")

        # 1. Sanitize polluted test cases (Explanation/Note blocks in expected_output)
        cutoff_pattern = re.compile(
            r'(?:\r?\n\s*|\s+)(?:Explanation|Note|Because|Clarification|Example)\s*[:\n][\s\S]*$',
            re.IGNORECASE
        )
        tc_query2 = TestCase.objects.all()
        if qnum:
            tc_query2 = tc_query2.filter(problem__question_number=qnum)

        cleaned_count = 0
        with transaction.atomic():
            for tc in tc_query2.iterator(chunk_size=500):
                orig = tc.expected_output or ''
                if cutoff_pattern.search(orig) or orig.lower().startswith('return '):
                    new_val = serialize_to_expected_stdout(orig)
                    if new_val != orig:
                        cleaned_count += 1
                        if not dry_run:
                            tc.expected_output = new_val
                            tc.save(update_fields=['expected_output'])

        self.stdout.write(f"Sanitized {cleaned_count} polluted test cases.")

        # 2. Exclude SQL/Database problems
        sql_problems = Problem.objects.filter(
            tags__name__iexact='Database'
        ) | Problem.objects.filter(
            test_cases__expected_output__contains='+---'
        )
        sql_problems = sql_problems.distinct()
        if qnum:
            sql_problems = sql_problems.filter(question_number=qnum)

        sql_disabled = 0
        for p in sql_problems:
            if p.is_judge_ready:
                sql_disabled += 1
                if not dry_run:
                    p.is_judge_ready = False
                    p.judge_readiness_status = 'NON_ALGORITHMIC_SQL'
                    p.missing_configuration = [
                        "Relational Database/SQL problem: algorithmic code execution is not supported"
                    ]
                    p.save(update_fields=['is_judge_ready', 'judge_readiness_status', 'missing_configuration'])

        self.stdout.write(f"Disabled judge readiness on {sql_disabled} SQL problems.")

        # 3. Re-generate starter code templates and input formats
        ready_problems = Problem.objects.filter(is_judge_ready=True)
        if qnum:
            ready_problems = ready_problems.filter(question_number=qnum)

        template_updated = 0
        for p in ready_problems.iterator(chunk_size=200):
            sig_meta = {
                'class_name': p.class_name or 'Solution',
                'function_name': p.function_name or 'solve',
                'parameters_meta': p.parameters_meta or [],
                'return_type': p.return_type or '',
            }
            new_input_fmt = generate_input_format(sig_meta, p.examples or [])
            py_s, py_h = _build_python(sig_meta, {})
            cpp_s, cpp_h = _build_cpp(sig_meta, {})
            java_s, java_h = _build_java(sig_meta, {})
            c_s, c_h = _build_c(sig_meta, {})

            if not dry_run:
                p.input_format = new_input_fmt
                p.save(update_fields=['input_format'])

                LanguageTemplate.objects.update_or_create(
                    problem=p, language='python',
                    defaults={'starter_code': py_s, 'harness_code': py_h}
                )
                LanguageTemplate.objects.update_or_create(
                    problem=p, language='cpp',
                    defaults={'starter_code': cpp_s, 'harness_code': cpp_h}
                )
                LanguageTemplate.objects.update_or_create(
                    problem=p, language='java',
                    defaults={'starter_code': java_s, 'harness_code': java_h}
                )
                LanguageTemplate.objects.update_or_create(
                    problem=p, language='c',
                    defaults={'starter_code': c_s, 'harness_code': c_h}
                )
            template_updated += 1

        self.stdout.write(f"Updated templates for {template_updated} problems.")
        self.stdout.write("clean_judge_data finished successfully.")
