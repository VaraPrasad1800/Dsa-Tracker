"""
Management command to batch-hydrate Problem contracts, test cases, and starter templates.

Usage examples:
    python manage.py hydrate_problem_contracts --range 1-50
    python manage.py hydrate_problem_contracts --question 20
    python manage.py hydrate_problem_contracts --limit 30
    python manage.py hydrate_problem_contracts --popular
"""
import time
from django.core.management.base import BaseCommand
from tracker.models import Problem
from tracker.services.problem_hydration_service import hydrate_problem_contract
from tracker.services.problem_contract_service import evaluate_problem_contract


class Command(BaseCommand):
    help = 'Batch hydrate DSA problem contracts, test cases, and templates'

    def add_arguments(self, parser):
        parser.add_argument(
            '--range',
            type=str,
            help='Range of question numbers to hydrate, e.g. 1-50',
        )
        parser.add_argument(
            '--question',
            type=int,
            help='Single question number to hydrate, e.g. 20',
        )
        parser.add_argument(
            '--limit',
            type=int,
            help='Number of unhydrated problems to hydrate',
        )
        parser.add_argument(
            '--popular',
            action='store_true',
            help='Hydrate top frequent / popular interview problems',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Re-hydrate even if already judge ready',
        )

    def handle(self, *args, **options):
        q_range = options.get('range')
        q_single = options.get('question')
        limit = options.get('limit')
        popular = options.get('popular')
        force = options.get('force')

        qs = Problem.objects.all()

        if q_single:
            qs = qs.filter(question_number=q_single)
        elif q_range:
            parts = q_range.split('-')
            if len(parts) == 2:
                start, end = int(parts[0]), int(parts[1])
                qs = qs.filter(question_number__gte=start, question_number__lte=end).order_by('question_number')
        elif popular:
            qs = qs.order_by('-frequency', 'question_number')
        else:
            qs = qs.order_by('question_number')

        if not force:
            qs = qs.filter(is_judge_ready=False)

        if limit:
            problems = list(qs[:limit])
        else:
            problems = list(qs)

        total = len(problems)
        self.stdout.write(f'Beginning hydration for {total} problems...')

        succeeded = 0
        failed = 0

        for idx, p in enumerate(problems, 1):
            self.stdout.write(f'[{idx}/{total}] Hydrating #{p.question_number} {p.title} (LC #{p.leetcode_id})... ', ending='')
            try:
                p, ok, msg = hydrate_problem_contract(p, force=force)
                if ok:
                    succeeded += 1
                    self.stdout.write(self.style.SUCCESS(f'OK -> {p.function_name}() [{p.test_cases.count()} tests]'))
                else:
                    failed += 1
                    self.stdout.write(self.style.WARNING(f'PENDING: {msg}'))
            except Exception as e:
                failed += 1
                self.stdout.write(self.style.ERROR(f'ERROR: {e}'))

        self.stdout.write('=' * 60)
        self.stdout.write(self.style.SUCCESS(f'Hydration complete: {succeeded} succeeded, {failed} pending/failed.'))
