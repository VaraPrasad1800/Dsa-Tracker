"""
normalize_judge_data — Dataset-wide Online Judge Data Normalization Pipeline
============================================================================

This management command scans ALL problems in the dataset and:

1. For every problem that has at least one example AND has been fetched (i.e.
   it has a Solution record or existing examples): normalizes test case
   input_text and expected_output to the canonical STDIN/STDOUT format,
   determines the correct output_checker strategy, and marks the problem
   JUDGE_READY if it satisfies the full contract.

2. For every problem that lacks the minimum required data (no examples, no
   test cases, no function signature): marks it CONFIGURATION_REQUIRED and
   records which prerequisites are missing — but does NOT fabricate any data.

Usage:
    python manage.py normalize_judge_data
    python manage.py normalize_judge_data --batch-size 500
    python manage.py normalize_judge_data --problem-id <uuid>
    python manage.py normalize_judge_data --question-number 1
    python manage.py normalize_judge_data --dry-run
    python manage.py normalize_judge_data --force   (re-normalizes already-ready problems)

Key guarantees:
    - NO hardcoded answers for any specific problem number.
    - NO fabricated test data — if reliable data cannot be extracted, mark CONFIGURATION_REQUIRED.
    - NO external HTTP requests — operates entirely on data already in the database.
    - Idempotent: safe to run repeatedly.
"""

import logging
import traceback
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Normalize judge data for all problems: canonical STDIN/STDOUT, output_checker, readiness status."

    def add_arguments(self, parser):
        parser.add_argument(
            '--batch-size', type=int, default=200,
            help='Number of problems to process per DB transaction (default: 200)',
        )
        parser.add_argument(
            '--problem-id', type=str, default=None,
            help='Normalize a single problem by UUID (for targeted testing)',
        )
        parser.add_argument(
            '--question-number', type=int, default=None,
            help='Normalize a single problem by its question number',
        )
        parser.add_argument(
            '--dry-run', action='store_true', default=False,
            help='Report what would change without actually writing anything',
        )
        parser.add_argument(
            '--force', action='store_true', default=False,
            help='Re-normalize even problems already marked JUDGE_READY',
        )
        parser.add_argument(
            '--verbose', action='store_true', default=False,
            help='Print per-problem details (slow for large datasets)',
        )

    def handle(self, *args, **options):
        from tracker.models import Problem, TestCase, LanguageTemplate
        from tracker.judge.canonical_serialization import (
            parse_example_arguments,
            serialize_to_stdin,
            serialize_to_expected_stdout,
            determine_output_checker,
        )
        from tracker.services.problem_contract_service import evaluate_problem_contract

        batch_size = options['batch_size']
        dry_run = options['dry_run']
        force = options['force']
        verbose = options['verbose']
        problem_id = options.get('problem_id')
        question_number = options.get('question_number')

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN — no changes will be written."))

        # --- Build queryset ---
        qs = Problem.objects.all().order_by('question_number', 'id')
        if problem_id:
            qs = qs.filter(id=problem_id)
        elif question_number is not None:
            qs = qs.filter(question_number=question_number)

        if not force:
            # Skip already-ready problems unless --force was given
            qs = qs.exclude(is_judge_ready=True)

        total = qs.count()
        self.stdout.write(f"Processing {total} problems (batch_size={batch_size}, dry_run={dry_run}, force={force})")

        # --- Counters ---
        stats = {
            'normalized': 0,
            'already_ready': 0,
            'marked_config_required': 0,
            'errors': 0,
            'test_cases_created': 0,
            'test_cases_updated': 0,
        }

        offset = 0
        while True:
            batch = list(qs[offset: offset + batch_size])
            if not batch:
                break
            offset += batch_size

            for problem in batch:
                try:
                    result = _normalize_problem(
                        problem=problem,
                        dry_run=dry_run,
                        verbose=verbose,
                        parse_example_arguments=parse_example_arguments,
                        serialize_to_stdin=serialize_to_stdin,
                        serialize_to_expected_stdout=serialize_to_expected_stdout,
                        determine_output_checker=determine_output_checker,
                        evaluate_problem_contract=evaluate_problem_contract,
                        TestCase=TestCase,
                        LanguageTemplate=LanguageTemplate,
                    )
                    stats['normalized'] += result.get('normalized', 0)
                    stats['already_ready'] += result.get('already_ready', 0)
                    stats['marked_config_required'] += result.get('marked_config_required', 0)
                    stats['test_cases_created'] += result.get('test_cases_created', 0)
                    stats['test_cases_updated'] += result.get('test_cases_updated', 0)
                except Exception as exc:
                    stats['errors'] += 1
                    logger.error("Error normalizing problem #%s (%s): %s",
                                 getattr(problem, 'question_number', '?'), problem.id, exc)
                    if verbose:
                        self.stdout.write(self.style.ERROR(
                            f"  ERROR #{getattr(problem, 'question_number', '?')}: {exc}\n"
                            + traceback.format_exc()
                        ))

        # --- Final report ---
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS("Normalization complete"))
        self.stdout.write(f"  Problems normalized (JUDGE_READY):   {stats['normalized']}")
        self.stdout.write(f"  Marked CONFIGURATION_REQUIRED:        {stats['marked_config_required']}")
        self.stdout.write(f"  Test cases created:                   {stats['test_cases_created']}")
        self.stdout.write(f"  Test cases updated:                   {stats['test_cases_updated']}")
        self.stdout.write(f"  Errors:                               {stats['errors']}")
        if dry_run:
            self.stdout.write(self.style.WARNING("  DRY RUN — nothing was written."))


def _normalize_problem(
    problem,
    dry_run: bool,
    verbose: bool,
    parse_example_arguments,
    serialize_to_stdin,
    serialize_to_expected_stdout,
    determine_output_checker,
    evaluate_problem_contract,
    TestCase,
    LanguageTemplate,
) -> dict:
    """
    Normalize a single problem in-place.

    Returns a stats dict with keys:
        normalized, already_ready, marked_config_required,
        test_cases_created, test_cases_updated
    """
    from tracker.models import Problem as ProblemModel

    result = {
        'normalized': 0,
        'already_ready': 0,
        'marked_config_required': 0,
        'test_cases_created': 0,
        'test_cases_updated': 0,
    }

    qnum = getattr(problem, 'question_number', '?')
    examples = problem.examples or []
    existing_tcs = list(TestCase.objects.filter(problem=problem).order_by('order'))

    # -----------------------------------------------------------------------
    # Step 1: Determine output_checker strategy
    # -----------------------------------------------------------------------
    checker_strategy = determine_output_checker(
        problem_desc=problem.description or '',
        return_type=problem.return_type or '',
        examples=examples,
    )

    # -----------------------------------------------------------------------
    # Step 2: Normalize test case data if examples exist
    # -----------------------------------------------------------------------
    new_test_cases = []

    if examples:
        for idx, ex in enumerate(examples):
            raw_inp = ex.get('input', '')
            raw_out = ex.get('output', '')

            # --- Canonical STDIN ---
            try:
                args = parse_example_arguments(raw_inp)
                if args:
                    inp_text = serialize_to_stdin(args)
                else:
                    # No structured arguments — pass through as-is (some problems are
                    # already in clean STDIN format, e.g. "n\n1 2 3")
                    inp_text = raw_inp.strip()
            except Exception:
                inp_text = raw_inp.strip()

            # --- Canonical STDOUT ---
            try:
                out_text = serialize_to_expected_stdout(raw_out, problem.return_type or '')
            except Exception:
                out_text = raw_out.strip()

            # Skip examples that produce empty data — don't fabricate
            if not inp_text or not out_text:
                continue

            # Visibility: first 1-2 visible, rest hidden
            cutoff = 1 if len(examples) == 2 else 2
            is_hidden = idx >= cutoff

            new_test_cases.append({
                'input_text': inp_text,
                'expected_output': out_text,
                'is_hidden': is_hidden,
                'order': idx + 1,
            })

    elif existing_tcs:
        # Problem has no examples in problem.examples (wasn't fetched or stored),
        # but it already has TestCase records — normalize those in-place
        for tc in existing_tcs:
            raw_inp = tc.input_text or ''
            raw_out = tc.expected_output or ''

            # Only re-normalize if the input looks like LeetCode bracket format
            if '[' in raw_inp or (raw_inp and not raw_inp[0].isdigit() and raw_inp[0] not in ('"', '-', 't', 'f')):
                try:
                    args = parse_example_arguments(raw_inp)
                    if args:
                        inp_text = serialize_to_stdin(args)
                    else:
                        inp_text = raw_inp.strip()
                except Exception:
                    inp_text = raw_inp.strip()
            else:
                inp_text = raw_inp.strip()

            if '[' in raw_out or raw_out.strip().startswith('['):
                try:
                    out_text = serialize_to_expected_stdout(raw_out, problem.return_type or '')
                except Exception:
                    out_text = raw_out.strip()
            else:
                out_text = raw_out.strip()

            new_test_cases.append({
                'input_text': inp_text,
                'expected_output': out_text,
                'is_hidden': tc.is_hidden,
                'order': tc.order,
            })

    # -----------------------------------------------------------------------
    # Step 3: Ensure at least one visible and one hidden test case
    # -----------------------------------------------------------------------
    if new_test_cases:
        has_visible = any(not t['is_hidden'] for t in new_test_cases)
        has_hidden = any(t['is_hidden'] for t in new_test_cases)

        if not has_hidden and len(new_test_cases) >= 1:
            # Duplicate last visible test as hidden
            last = dict(new_test_cases[-1])
            last['is_hidden'] = True
            last['order'] = new_test_cases[-1]['order'] + 1
            new_test_cases.append(last)
            has_hidden = True

        if not has_visible and len(new_test_cases) >= 1:
            new_test_cases[0]['is_hidden'] = False
            has_visible = True

    # -----------------------------------------------------------------------
    # Step 4: Write to DB (unless dry_run)
    # -----------------------------------------------------------------------
    if not dry_run and new_test_cases:
        with transaction.atomic():
            # Delete old test cases and replace
            TestCase.objects.filter(problem=problem).delete()
            created = TestCase.objects.bulk_create([
                TestCase(
                    problem=problem,
                    input_text=t['input_text'],
                    expected_output=t['expected_output'],
                    is_hidden=t['is_hidden'],
                    order=t['order'],
                )
                for t in new_test_cases
            ])
            result['test_cases_created'] = len(created)

    # -----------------------------------------------------------------------
    # Step 5: Update problem.output_checker and evaluate contract
    # -----------------------------------------------------------------------
    if not dry_run:
        problem.output_checker = checker_strategy

        # Evaluate contract readiness
        contract_info = evaluate_problem_contract(problem)
        problem.is_judge_ready = contract_info['is_judge_ready']
        problem.judge_readiness_status = contract_info['judge_readiness_status']
        problem.missing_configuration = contract_info['missing_configuration']
        problem.save(update_fields=[
            'output_checker',
            'is_judge_ready',
            'judge_readiness_status',
            'missing_configuration',
        ])

        if problem.is_judge_ready:
            result['normalized'] = 1
        else:
            result['marked_config_required'] = 1
    else:
        # Dry-run: evaluate but don't save
        contract_info = evaluate_problem_contract(problem)
        is_ready = contract_info['is_judge_ready'] and bool(new_test_cases)
        if is_ready:
            result['normalized'] = 1
        else:
            result['marked_config_required'] = 1

    if verbose:
        status_label = "JUDGE_READY" if (result.get('normalized', 0) > 0) else "CONFIGURATION_REQUIRED"
        missing = contract_info.get('missing_configuration', [])
        print(
            f"  #{qnum:<6} {status_label:<25} checker={checker_strategy:<25} "
            f"tests={len(new_test_cases)}  "
            + (f"missing={missing}" if missing else "")
        )

    return result
