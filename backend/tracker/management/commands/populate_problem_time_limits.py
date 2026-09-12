"""
Management command to populate difficulty-aware time and memory limits across all problems.

Usage:
    python manage.py populate_problem_time_limits [--force] [--batch-size 1000]
"""

from django.core.management.base import BaseCommand
from tracker.models import Problem
from tracker.judge.judge_config import (
    DEFAULT_TIME_LIMIT_BY_DIFFICULTY,
    PLATFORM_DEFAULT_TIME_LIMIT_MS,
    PLATFORM_DEFAULT_MEMORY_LIMIT_MB,
)


class Command(BaseCommand):
    help = "Populate authoritative difficulty-aware execution time and memory limits for all problems"

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Overwrite existing non-null time_limit_ms values with difficulty defaults',
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=1000,
            help='Batch size for bulk updates (default: 1000)',
        )

    def handle(self, *args, **options):
        force = options['force']
        batch_size = options['batch_size']

        qs = Problem.objects.all()
        total_count = qs.count()

        if not force:
            qs = qs.filter(time_limit_ms__isnull=True)

        target_count = qs.count()
        self.stdout.write(
            f"Found {total_count} total problems. {target_count} need time_limit_ms population (force={force})."
        )

        if target_count == 0:
            self.stdout.write(self.style.SUCCESS("All problems already have time limits configured!"))
            return

        updated_count = 0
        difficulty_counts = {'Easy': 0, 'Medium': 0, 'Hard': 0, 'Other': 0}

        problems_to_update = []
        for problem in qs.iterator(chunk_size=batch_size):
            diff = problem.difficulty or 'Medium'
            time_limit = DEFAULT_TIME_LIMIT_BY_DIFFICULTY.get(diff, PLATFORM_DEFAULT_TIME_LIMIT_MS)
            mem_limit = problem.memory_limit_mb or PLATFORM_DEFAULT_MEMORY_LIMIT_MB

            problem.time_limit_ms = time_limit
            problem.memory_limit_mb = mem_limit
            problems_to_update.append(problem)

            if diff in difficulty_counts:
                difficulty_counts[diff] += 1
            else:
                difficulty_counts['Other'] += 1

            if len(problems_to_update) >= batch_size:
                Problem.objects.bulk_update(problems_to_update, ['time_limit_ms', 'memory_limit_mb'])
                updated_count += len(problems_to_update)
                problems_to_update = []
                self.stdout.write(f"Updated {updated_count}/{target_count} problems...")

        if problems_to_update:
            Problem.objects.bulk_update(problems_to_update, ['time_limit_ms', 'memory_limit_mb'])
            updated_count += len(problems_to_update)

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully updated {updated_count} problems with authoritative limits:\n"
                f"  - Easy ({DEFAULT_TIME_LIMIT_BY_DIFFICULTY['Easy']}ms): {difficulty_counts['Easy']}\n"
                f"  - Medium ({DEFAULT_TIME_LIMIT_BY_DIFFICULTY['Medium']}ms): {difficulty_counts['Medium']}\n"
                f"  - Hard ({DEFAULT_TIME_LIMIT_BY_DIFFICULTY['Hard']}ms): {difficulty_counts['Hard']}\n"
                f"  - Memory limit set to {PLATFORM_DEFAULT_MEMORY_LIMIT_MB}MB"
            )
        )
