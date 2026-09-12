"""
Normalize Judge Execution Model Management Command
===================================================
Migrates problems across the problem bank to ONE universal user-facing execution model:
  User writes complete program (Python, C, C++, Java) -> stdin -> stdout -> output validator.

Populates:
1. execution_mode = 'STDIN_STDOUT'
2. input_format & output_format specifications
3. Complete-program starter templates for Python, C++, Java, and C
4. Structured visible and hidden TestCases
5. Problem contract synchronization
"""

import sys
import logging
from django.core.management.base import BaseCommand
from tracker.models import Problem, TestCase, LanguageTemplate
from tracker.services.problem_hydration_service import hydrate_problem_contract
from tracker.services.problem_contract_service import evaluate_problem_contract

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Normalize DSA problems to the universal Complete Program / Standard I/O execution model'

    def add_arguments(self, parser):
        parser.add_argument(
            '--range',
            type=str,
            help='Range of question numbers to process (e.g. 1-50)'
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=0,
            help='Maximum number of problems to process (0 for all in query)'
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Process all problems in database'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force re-hydration even if problem is already marked judge-ready'
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Initializing universal Online Judge normalization..."))

        qs = Problem.objects.all().order_by('question_number')

        if options.get('range'):
            try:
                start_str, end_str = options['range'].split('-')
                start, end = int(start_str), int(end_str)
                qs = qs.filter(question_number__gte=start, question_number__lte=end)
                self.stdout.write(f"Targeting range: #{start} to #{end} ({qs.count()} problems)")
            except ValueError:
                self.stdout.write(self.style.ERROR(f"Invalid range format '{options['range']}'. Use start-end (e.g. 1-50)."))
                return

        if options.get('limit') and options['limit'] > 0:
            qs = qs[:options['limit']]

        total_to_process = qs.count() if not isinstance(qs, list) else len(qs)
        self.stdout.write(f"Total problems queued for normalization: {total_to_process}")

        processed = 0
        ready_count = 0
        failed_count = 0

        for problem in qs:
            processed += 1
            try:
                p, is_ready, msg = hydrate_problem_contract(problem, force=options.get('force', False))
                if is_ready:
                    ready_count += 1
                    status_text = self.style.SUCCESS("[JUDGE_READY]")
                else:
                    failed_count += 1
                    status_text = self.style.WARNING("[CONFIG_REQ]")

                if processed <= 25 or processed % 25 == 0 or processed == total_to_process:
                    self.stdout.write(
                        f"  [{processed:4d}/{total_to_process:4d}] #{p.question_number:4d} {p.title[:30]:30s} -> {status_text} {msg[:60]}"
                    )
            except Exception as exc:
                failed_count += 1
                self.stdout.write(
                    self.style.ERROR(f"  [{processed:4d}/{total_to_process:4d}] #{problem.question_number} {problem.title}: {exc}")
                )

        self.stdout.write(self.style.SUCCESS("\n============================================================"))
        self.stdout.write(self.style.SUCCESS("NORMALIZATION COMPLETE"))
        self.stdout.write(self.style.SUCCESS("============================================================"))
        self.stdout.write(f"Processed:            {processed}")
        self.stdout.write(f"JUDGE_READY:          {ready_count}")
        self.stdout.write(f"Pending/Incomplete:   {failed_count}")
        self.stdout.write("============================================================\n")
