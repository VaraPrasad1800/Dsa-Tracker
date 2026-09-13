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


class Command(BaseCommand):
    help = "Sanitize test cases, exclude SQL problems, and re-generate language templates"

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Report without writing to database')
        parser.add_argument('--question-number', type=int, help='Only process specific problem number')

    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)
        qnum = options.get('question_number')

        self.stdout.write(f"Running clean_judge_data (dry_run={dry_run})...")

        # 1. Sanitize polluted test cases
        cutoff_pattern = re.compile(
            r'(?:\r?\n\s*|\s+)(?:Explanation|Note|Because|Clarification|Example)\s*[:\n][\s\S]*$',
            re.IGNORECASE
        )
        tc_query = TestCase.objects.all()
        if qnum:
            tc_query = tc_query.filter(problem__question_number=qnum)

        cleaned_count = 0
        with transaction.atomic():
            for tc in tc_query.iterator(chunk_size=500):
                orig = tc.expected_output or ''
                if cutoff_pattern.search(orig) or orig.lower().startswith('return '):
                    new_val = serialize_to_expected_stdout(orig, tc.problem.return_type or '')
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
