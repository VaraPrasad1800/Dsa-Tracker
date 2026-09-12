"""
Sync Problem Contracts Management Command
=========================================
Evaluates and updates the database records for all problems with their canonical
contract readiness (is_judge_ready, judge_readiness_status, missing_configuration).
"""

from django.core.management.base import BaseCommand
from tracker.services.problem_contract_service import sync_all_problem_contracts


class Command(BaseCommand):
    help = 'Sync and persist canonical problem contract readiness across all problems'

    def add_arguments(self, parser):
        parser.add_argument(
            '--batch-size',
            type=int,
            default=500,
            help='Batch size for database bulk updates'
        )

    def handle(self, *args, **options):
        batch_size = options['batch_size']
        self.stdout.write(f"Evaluating and syncing problem contracts (batch_size={batch_size})...")

        res = sync_all_problem_contracts(batch_size=batch_size)

        self.stdout.write(self.style.SUCCESS(
            f"Successfully synced contracts across {res['total_problems']} problems!\n"
            f"Judge Ready: {res['judge_ready']}\n"
            f"Configuration Required: {res['configuration_required']}"
        ))
