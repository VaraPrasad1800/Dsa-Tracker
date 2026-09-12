"""
Management command to audit and synchronize is_premium flags for all DSA problems
against the authoritative backend/data/leetcode_mapping.json dataset.
"""
import os
import json
from django.conf import settings
from django.core.management.base import BaseCommand
from tracker.models import Problem


class Command(BaseCommand):
    help = 'Synchronize Problem.is_premium with authoritative leetcode_mapping.json data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Report mismatches without updating the database',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        self.stdout.write('Auditing and synchronizing is_premium flags against leetcode_mapping.json...')

        mapping_path = os.path.join(settings.BASE_DIR, 'data', 'leetcode_mapping.json')
        if not os.path.exists(mapping_path):
            self.stderr.write(self.style.ERROR(f'Mapping file not found at: {mapping_path}'))
            return

        with open(mapping_path, 'r', encoding='utf-8') as f:
            mapping_data = json.load(f)

        # Build lookup tables
        by_id = {}
        by_slug = {}
        for slug, item in mapping_data.items():
            by_id[item['id']] = item
            by_slug[slug] = item

        problems = Problem.objects.all()
        total_problems = problems.count()
        matched = 0
        unmatched = 0
        false_positives = []  # Marked premium in DB, actually free in LeetCode
        false_negatives = []  # Marked free in DB, actually premium in LeetCode
        updated_count = 0

        for p in problems:
            item = None
            if p.leetcode_id and p.leetcode_id in by_id:
                item = by_id[p.leetcode_id]
                matched += 1
            elif p.slug and p.slug in by_slug:
                item = by_slug[p.slug]
                matched += 1
            else:
                unmatched += 1
                continue

            authoritative_premium = item.get('paid_only', False)
            if p.is_premium != authoritative_premium:
                if p.is_premium and not authoritative_premium:
                    false_positives.append((p, authoritative_premium))
                else:
                    false_negatives.append((p, authoritative_premium))

                if not dry_run:
                    p.is_premium = authoritative_premium
                    p.save(update_fields=['is_premium'])
                    updated_count += 1

        self.stdout.write('=' * 60)
        self.stdout.write(f'Total problems inspected: {total_problems}')
        self.stdout.write(f'Matched against mapping: {matched}')
        self.stdout.write(f'Unmatched problems:      {unmatched}')
        self.stdout.write(f'False positives found:   {len(false_positives)}')
        self.stdout.write(f'False negatives found:   {len(false_negatives)}')
        self.stdout.write('=' * 60)

        if false_positives:
            self.stdout.write(self.style.WARNING('\nFalse Positives (was marked Premium, actually FREE):'))
            for p, _ in false_positives:
                self.stdout.write(f'  - #{p.question_number} {p.title} (LC #{p.leetcode_id}) -> is_premium=False')

        if false_negatives:
            self.stdout.write(self.style.WARNING('\nFalse Negatives (was marked Free, actually PREMIUM):'))
            for p, _ in false_negatives:
                self.stdout.write(f'  - #{p.question_number} {p.title} (LC #{p.leetcode_id}) -> is_premium=True')

        if dry_run:
            self.stdout.write(self.style.NOTICE('\nDry run complete. No database changes made.'))
        else:
            self.stdout.write(self.style.SUCCESS(f'\nSuccessfully updated {updated_count} problems in the database!'))
