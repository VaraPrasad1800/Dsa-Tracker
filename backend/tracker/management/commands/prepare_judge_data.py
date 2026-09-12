"""
prepare_judge_data — Idempotent, Resumable Judge Data Preparation Pipeline
===========================================================================

DESIGN PRINCIPLES
-----------------
1. DATABASE IS THE SINGLE SOURCE OF TRUTH.
   The Problem.preparation_status field drives all decisions.
   Python variables, in-memory state, or terminal history play no role.

2. IDEMPOTENT.
   Running the command multiple times produces the same result.
   Already-prepared problems (preparation_status=JUDGE_READY) are NEVER re-fetched.

3. CHECKPOINT PER PROBLEM.
   Each successfully prepared problem is committed to the DB immediately.
   If the process is killed mid-batch, already-committed problems remain committed.
   The next run resumes exactly where the interrupted run left off.

4. ZERO HARDCODING.
   No problem-specific logic. All behavior derives from generic problem data.

5. SAFE TO STOP AT ANY TIME.
   Interrupted FETCHING/NORMALIZING states are treated as PENDING on next run
   (a process crash cannot leave a problem incorrectly marked JUDGE_READY).

PREPARATION STATUS LIFECYCLE
-----------------------------
PENDING            → Not yet processed. Eligible for this run.
FETCHING           → Network request was in-progress (or process crashed). Retry next run.
NORMALIZING        → Data processing was in-progress (or process crashed). Retry next run.
JUDGE_READY        → Fully prepared. SKIP in all normal runs.
CONFIGURATION_REQUIRED → External data unavailable (e.g. no leetcode_id). Skip until --retry-config.
FAILED             → Fetch/prepare error. Retry after back-off (or immediately with --retry-failed).

WHAT COUNTS AS "JUDGE_READY"
-----------------------------
A problem is only marked JUDGE_READY when ALL of the following are validated:
  - problem.is_judge_ready == True (from evaluate_problem_contract)
  - at least 1 visible TestCase exists with non-empty input_text + expected_output
  - at least 1 hidden TestCase exists
  - at least 1 LanguageTemplate exists for python
  - TestCase.input_text does NOT contain bracket notation [...]

USAGE
-----
    python manage.py prepare_judge_data --batch-size=10
    python manage.py prepare_judge_data --batch-size=50
    python manage.py prepare_judge_data --batch-size=10 --retry-failed
    python manage.py prepare_judge_data --batch-size=10 --question-number=29
    python manage.py prepare_judge_data --force --batch-size=10   (rebuild — explicit destructive)
    python manage.py prepare_judge_data --dry-run
"""

import logging
import traceback
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)

# Max attempts before a problem is no longer auto-retried without --retry-failed
MAX_AUTO_RETRY_ATTEMPTS = 3
# Minimum time between retries for FAILED problems (without --retry-failed flag)
FAILED_RETRY_BACKOFF_HOURS = 1


class Command(BaseCommand):
    help = (
        "Idempotent, resumable pipeline to fetch and prepare judge data "
        "for DSA problems. Safe to stop and restart at any time."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--batch-size',
            type=int,
            default=10,
            dest='batch_size',
            help='Number of eligible problems to process in this run (default: 10)',
        )
        parser.add_argument(
            '--question-number',
            type=int,
            default=None,
            dest='question_number',
            help='Target a single problem by its question number',
        )
        parser.add_argument(
            '--retry-failed',
            action='store_true',
            default=False,
            dest='retry_failed',
            help='Include FAILED problems in this run (regardless of attempt count or backoff)',
        )
        parser.add_argument(
            '--retry-config',
            action='store_true',
            default=False,
            dest='retry_config',
            help='Include CONFIGURATION_REQUIRED problems in this run (re-attempt fetch)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            default=False,
            dest='dry_run',
            help='Show what would be processed without writing anything',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            default=False,
            dest='force',
            help=(
                'DESTRUCTIVE: Rebuild judge data even for already-JUDGE_READY problems. '
                'Use only for explicit rebuild/repair. Normal runs must never use this.'
            ),
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            default=False,
            dest='verbose',
            help='Print per-problem processing detail',
        )

    def handle(self, *args, **options):
        from tracker.models import Problem, TestCase, LanguageTemplate

        batch_size = options['batch_size']
        question_number = options.get('question_number')
        retry_failed = options['retry_failed']
        retry_config = options['retry_config']
        dry_run = options['dry_run']
        force = options['force']
        verbose = options['verbose']

        # -----------------------------------------------------------------------
        # 0. Sync preparation_status for already-JUDGE_READY problems that were
        #    prepared before this field existed (backfill guard).
        # -----------------------------------------------------------------------
        Problem.objects.filter(
            is_judge_ready=True,
        ).exclude(
            preparation_status='JUDGE_READY'
        ).update(preparation_status='JUDGE_READY')

        # -----------------------------------------------------------------------
        # 1. Print current DB state BEFORE processing — from actual DB counts.
        # -----------------------------------------------------------------------
        self._print_header(batch_size, dry_run, force, retry_failed, retry_config)

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN mode — nothing will be written.\n"))

        # -----------------------------------------------------------------------
        # 2. Build the eligible problem queryset.
        # -----------------------------------------------------------------------
        eligible_qs = self._build_eligible_queryset(
            question_number=question_number,
            retry_failed=retry_failed,
            retry_config=retry_config,
            force=force,
        )

        eligible_count = eligible_qs.count()

        if eligible_count == 0:
            self.stdout.write(self.style.SUCCESS(
                "\nNo problems require preparation. All done!\n"
                "Use --retry-failed to reprocess previously failed problems.\n"
                "Use --force to rebuild already-prepared problems.\n"
            ))
            return

        # Select the batch — deterministic by question_number ascending
        batch = list(eligible_qs[:batch_size])
        self.stdout.write(
            f"\nSelecting {len(batch)} problems from {eligible_count} eligible "
            f"(ordered by question_number ascending).\n"
        )

        # -----------------------------------------------------------------------
        # 3. Process each problem individually with per-problem commit.
        # -----------------------------------------------------------------------
        run_stats = {
            'attempted': 0,
            'succeeded': 0,
            'skipped': 0,
            'failed': 0,
            'config_required': 0,
        }

        for problem in batch:
            run_stats['attempted'] += 1
            qnum = problem.question_number or '?'
            title_clean = (problem.title or '')[:45].encode('ascii', 'replace').decode('ascii')
            label = f"#{qnum} {title_clean!r}"

            if dry_run:
                self.stdout.write(f"  [DRY-RUN] Would process {label}")
                run_stats['succeeded'] += 1
                continue

            result = self._process_one_problem(problem, force=force, verbose=verbose)

            if result == 'JUDGE_READY':
                run_stats['succeeded'] += 1
                if verbose:
                    self.stdout.write(self.style.SUCCESS(f"  [OK]   {label} -> JUDGE_READY"))
                else:
                    self.stdout.write(f"  [OK]   {label} -> JUDGE_READY")
            elif result == 'CONFIGURATION_REQUIRED':
                run_stats['config_required'] += 1
                self.stdout.write(self.style.WARNING(f"  [WARN] {label} -> CONFIGURATION_REQUIRED"))
            elif result == 'FAILED':
                run_stats['failed'] += 1
                self.stdout.write(self.style.ERROR(f"  [ERR]  {label} -> FAILED"))
            else:
                run_stats['skipped'] += 1
                self.stdout.write(f"  [--]   {label} -> {result}")

        # -----------------------------------------------------------------------
        # 4. Print final DB state AFTER processing — from actual DB counts.
        # -----------------------------------------------------------------------
        self._print_footer(run_stats)

    # ---------------------------------------------------------------------------
    # Queryset builder — the core skip/resume logic
    # ---------------------------------------------------------------------------

    def _build_eligible_queryset(self, question_number, retry_failed, retry_config, force):
        """
        Return a queryset of problems eligible for processing in this run.

        NEVER includes JUDGE_READY problems unless --force is set.
        """
        from tracker.models import Problem

        qs = Problem.objects.all()

        if question_number is not None:
            qs = qs.filter(question_number=question_number)

        if force:
            # Force mode: include everything (including JUDGE_READY)
            pass
        else:
            # Normal mode: exclude already-done problems
            excluded_statuses = ['JUDGE_READY']

            if not retry_failed:
                # Don't retry FAILED problems unless explicitly requested
                excluded_statuses.append('FAILED')

            if not retry_config:
                # Don't retry CONFIGURATION_REQUIRED unless explicitly requested
                excluded_statuses.append('CONFIGURATION_REQUIRED')

            qs = qs.exclude(preparation_status__in=excluded_statuses)

            # Also exclude FAILED problems that haven't cooled off yet
            # (unless --retry-failed is set, they were already excluded above)
            if retry_failed:
                backoff_cutoff = timezone.now() - timedelta(hours=FAILED_RETRY_BACKOFF_HOURS)
                # For --retry-failed: include all FAILED regardless of backoff
                # The cutoff only applies to automatic inclusion (no --retry-failed)
                pass

            # Exclude problems without a leetcode_id (can't fetch anything)
            # Unless question_number was specified, in which case user knows what they want
            if question_number is None:
                qs = qs.filter(leetcode_id__isnull=False)

            # Treat FETCHING/NORMALIZING as PENDING (process crashed mid-step)
            # These are already included because we only excluded ['JUDGE_READY', ...]

        return qs.order_by('question_number', 'id')

    # ---------------------------------------------------------------------------
    # Single-problem processing — atomic checkpoint per problem
    # ---------------------------------------------------------------------------

    def _process_one_problem(self, problem, force: bool, verbose: bool) -> str:
        """
        Attempt to fetch, normalize, and validate judge data for a single problem.

        Returns one of: 'JUDGE_READY', 'CONFIGURATION_REQUIRED', 'FAILED'

        Commits state to DB after every significant step — safe against interruption.
        """
        from tracker.models import Problem, TestCase, LanguageTemplate
        from django.utils import timezone

        qnum = problem.question_number or '?'

        # --- Mark as FETCHING before any network access ---
        Problem.objects.filter(pk=problem.pk).update(
            preparation_status='FETCHING',
            preparation_attempts=problem.preparation_attempts + 1,
            preparation_last_attempted=timezone.now(),
            preparation_error='',
        )
        problem.preparation_status = 'FETCHING'
        problem.preparation_attempts += 1
        problem.preparation_last_attempted = timezone.now()

        # -----------------------------------------------------------------------
        # Step 1: Fetch from external source
        # -----------------------------------------------------------------------
        try:
            fetched = self._fetch_problem_data(problem)
        except Exception as exc:
            error_msg = f"Fetch error: {exc}"
            if verbose:
                error_msg += "\n" + traceback.format_exc()
            logger.error("prepare_judge_data: fetch failed for #%s: %s", qnum, exc)
            Problem.objects.filter(pk=problem.pk).update(
                preparation_status='FAILED',
                preparation_error=error_msg[:2000],
            )
            return 'FAILED'

        if fetched is None:
            # External page unavailable — could be a 404 or permanent failure
            msg = "External source unavailable (None returned from fetch)"
            Problem.objects.filter(pk=problem.pk).update(
                preparation_status='CONFIGURATION_REQUIRED',
                preparation_error=msg,
            )
            return 'CONFIGURATION_REQUIRED'

        # -----------------------------------------------------------------------
        # Step 2: Persist fetched data + normalize → mark NORMALIZING
        # -----------------------------------------------------------------------
        Problem.objects.filter(pk=problem.pk).update(preparation_status='NORMALIZING')

        try:
            success, error_msg = self._persist_and_normalize(problem, fetched, force=force, verbose=verbose)
        except Exception as exc:
            error_msg = f"Normalize error: {exc}"
            if verbose:
                error_msg += "\n" + traceback.format_exc()
            logger.error("prepare_judge_data: normalize failed for #%s: %s", qnum, exc)
            Problem.objects.filter(pk=problem.pk).update(
                preparation_status='FAILED',
                preparation_error=error_msg[:2000],
            )
            return 'FAILED'

        # -----------------------------------------------------------------------
        # Step 3: Validate result and set final status
        # -----------------------------------------------------------------------
        problem.refresh_from_db()

        if success and problem.is_judge_ready:
            # Verify the validation criteria independently
            valid, validation_error = self._validate_judge_ready(problem)
            if valid:
                Problem.objects.filter(pk=problem.pk).update(
                    preparation_status='JUDGE_READY',
                    preparation_error='',
                )
                return 'JUDGE_READY'
            else:
                Problem.objects.filter(pk=problem.pk).update(
                    preparation_status='CONFIGURATION_REQUIRED',
                    preparation_error=f"Validation failed: {validation_error}",
                )
                return 'CONFIGURATION_REQUIRED'
        else:
            final_error = error_msg or getattr(problem, 'preparation_error', '') or 'Missing required judge data'
            Problem.objects.filter(pk=problem.pk).update(
                preparation_status='CONFIGURATION_REQUIRED',
                preparation_error=final_error[:2000],
            )
            return 'CONFIGURATION_REQUIRED'

    # ---------------------------------------------------------------------------
    # Fetch layer — calls scraper, respects rate limiting
    # ---------------------------------------------------------------------------

    def _fetch_problem_data(self, problem) -> dict | None:
        """
        Fetch problem data from leetcode.ca or reuse existing local DB data.
        Returns structured dict or None. Raises on unrecoverable error.
        """
        from tracker.models import Solution
        from tracker.scraper import fetch_solution

        sol = Solution.objects.filter(problem=problem).first()
        if problem.description and sol:
            return {
                'title': problem.title,
                'description': problem.description,
                'examples': problem.examples or [],
                'constraints': problem.constraints or [],
                'code': sol.code or '',
                'code_by_language': sol.code_by_language or {},
                'language': sol.language or 'python',
                'explanation': sol.explanation or '',
                'time_complexity': sol.time_complexity or '',
                'space_complexity': sol.space_complexity or '',
                'source_url': sol.source_url or '',
                'solution_source_url': sol.solution_source_url or '',
                'question_number': sol.question_number or problem.question_number,
            }

        return fetch_solution(problem.leetcode_id)

    # ---------------------------------------------------------------------------
    # Persist + normalize layer — calls existing hydration service
    # ---------------------------------------------------------------------------

    def _persist_and_normalize(self, problem, fetched: dict, force: bool, verbose: bool):
        """
        Persist fetched data, generate canonical test cases and templates,
        normalize I/O format, set output_checker, evaluate contract.

        Returns (success: bool, error_msg: str).
        Uses existing hydrate_problem_contract() but called ONLY from this pipeline,
        never from user-facing Run Code or Submit endpoints.
        """
        from tracker.services.problem_hydration_service import hydrate_problem_contract

        # Call existing hydration service with pre-fetched data to avoid duplicate network calls
        _, ok, msg = hydrate_problem_contract(problem, force=force, fetched_data=fetched)
        return ok, (msg if not ok else '')

    # ---------------------------------------------------------------------------
    # Validation — verifies the problem truly satisfies the judge contract
    # ---------------------------------------------------------------------------

    def _validate_judge_ready(self, problem) -> tuple[bool, str]:
        """
        Independently verify that the problem meets all JUDGE_READY criteria.
        Returns (is_valid: bool, error_description: str).
        """
        from tracker.models import TestCase, LanguageTemplate

        # Must have at least 1 visible test case
        visible_tcs = TestCase.objects.filter(problem=problem, is_hidden=False)
        if not visible_tcs.exists():
            return False, "No visible test cases"

        # Must have at least 1 hidden test case
        hidden_tcs = TestCase.objects.filter(problem=problem, is_hidden=True)
        if not hidden_tcs.exists():
            return False, "No hidden test cases"

        # All test cases must have non-empty input and output
        for tc in TestCase.objects.filter(problem=problem):
            if not (tc.input_text or '').strip():
                return False, f"TestCase {tc.pk} has empty input_text"
            if not (tc.expected_output or '').strip():
                return False, f"TestCase {tc.pk} has empty expected_output"

        # Test case inputs must NOT contain bracket notation (canonical check)
        for tc in TestCase.objects.filter(problem=problem):
            inp = (tc.input_text or '').strip()
            if inp.startswith('[') and not inp.startswith('[['):
                # Plain bracket array like [2,7,11,15] — not canonical
                return False, f"TestCase {tc.pk} input_text still in bracket notation: {inp[:50]!r}"

        # Must have at least a Python language template
        if not LanguageTemplate.objects.filter(problem=problem, language='python').exists():
            return False, "No Python language template"

        return True, ''

    # ---------------------------------------------------------------------------
    # Display helpers
    # ---------------------------------------------------------------------------

    def _get_db_counts(self):
        """Return fresh DB counts — never uses Python counters."""
        from tracker.models import Problem
        from django.db.models import Count

        counts = {s: 0 for s in ['PENDING', 'FETCHING', 'NORMALIZING',
                                  'JUDGE_READY', 'CONFIGURATION_REQUIRED', 'FAILED']}
        for row in Problem.objects.values('preparation_status').annotate(n=Count('id')):
            counts[row['preparation_status']] = row['n']

        total = Problem.objects.count()
        return total, counts

    def _print_header(self, batch_size, dry_run, force, retry_failed, retry_config):
        total, counts = self._get_db_counts()
        pending = counts.get('PENDING', 0) + counts.get('FETCHING', 0) + counts.get('NORMALIZING', 0)
        ready = counts.get('JUDGE_READY', 0)
        failed = counts.get('FAILED', 0)
        config_req = counts.get('CONFIGURATION_REQUIRED', 0)

        self.stdout.write("\n" + "=" * 54)
        self.stdout.write("  JUDGE DATA PREPARATION PIPELINE")
        self.stdout.write("=" * 54)
        self.stdout.write(f"  Total problems       : {total}")
        self.stdout.write(f"  Already JUDGE_READY  : {ready}")
        self.stdout.write(f"  Pending              : {pending}")
        self.stdout.write(f"  Failed               : {failed}")
        self.stdout.write(f"  Config required      : {config_req}")
        self.stdout.write(f"  Batch size           : {batch_size}")
        if force:
            self.stdout.write(self.style.WARNING("  Mode                 : FORCE (rebuilding ready problems)"))
        elif retry_failed:
            self.stdout.write("  Mode                 : retry-failed included")
        if dry_run:
            self.stdout.write(self.style.WARNING("  Mode                 : DRY RUN"))
        self.stdout.write("=" * 54 + "\n")

    def _print_footer(self, run_stats):
        total, counts = self._get_db_counts()
        pending = counts.get('PENDING', 0) + counts.get('FETCHING', 0) + counts.get('NORMALIZING', 0)
        ready = counts.get('JUDGE_READY', 0)
        failed = counts.get('FAILED', 0)
        config_req = counts.get('CONFIGURATION_REQUIRED', 0)
        remaining = total - ready

        self.stdout.write("\n" + "=" * 54)
        self.stdout.write("  THIS RUN")
        self.stdout.write("=" * 54)
        self.stdout.write(f"  Attempted            : {run_stats['attempted']}")
        self.stdout.write(
            self.style.SUCCESS(f"  Succeeded (READY)    : {run_stats['succeeded']}")
            if run_stats['succeeded'] else f"  Succeeded (READY)    : {run_stats['succeeded']}"
        )
        self.stdout.write(f"  Config required      : {run_stats['config_required']}")
        self.stdout.write(
            self.style.ERROR(f"  Failed               : {run_stats['failed']}")
            if run_stats['failed'] else f"  Failed               : {run_stats['failed']}"
        )
        self.stdout.write("\n  OVERALL DATABASE STATE (from DB)")
        self.stdout.write("-" * 54)
        self.stdout.write(f"  Total                : {total}")
        self.stdout.write(f"  JUDGE_READY          : {ready}")
        self.stdout.write(f"  Pending              : {pending}")
        self.stdout.write(f"  Config required      : {config_req}")
        self.stdout.write(f"  Failed               : {failed}")
        self.stdout.write(f"  Remaining to prepare : {remaining}")
        self.stdout.write("=" * 54 + "\n")

        if remaining > 0:
            self.stdout.write(
                f"Run again to prepare the next batch:\n"
                f"  python manage.py prepare_judge_data --batch-size={run_stats['attempted']}\n"
            )
