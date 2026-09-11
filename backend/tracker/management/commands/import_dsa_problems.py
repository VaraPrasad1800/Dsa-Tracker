import csv
import os
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from tracker.models import Problem, Tag, Company

class Command(BaseCommand):
    help = 'Import DSA problems from a CSV file (idempotent, upserts by slug)'

    def add_arguments(self, parser):
        parser.add_argument('--csv', type=str, required=True, help='Path to the CSV file')

    def handle(self, *args, **options):
        csv_path = options['csv']
        if not os.path.isabs(csv_path):
            csv_path = os.path.abspath(csv_path)

        if not os.path.exists(csv_path):
            self.stderr.write(self.style.ERROR(f'CSV file not found: {csv_path}'))
            return

        created_count = 0
        updated_count = 0
        skipped_count = 0

        with open(csv_path, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                title = row.get('title', '').strip()
                difficulty = row.get('difficulty', '').strip()
                topics_raw = row.get('topic', '').strip()
                companies_raw = row.get('companies', '').strip()
                source_url = row.get('source_url', '').strip()
                source_platform = row.get('source_platform', 'LeetCode').strip()

                if not title or not difficulty:
                    skipped_count += 1
                    continue

                slug = slugify(title)
                problem, created = Problem.objects.update_or_create(
                    slug=slug,
                    defaults={
                        'title': title,
                        'difficulty': difficulty,
                        'source_url': source_url,
                        'source_platform': source_platform,
                    }
                )

                if created:
                    created_count += 1
                else:
                    updated_count += 1

                # Parse and associate tags
                if topics_raw:
                    tag_names = [t.strip() for t in topics_raw.split('|') if t.strip()]
                    for name in tag_names:
                        tag_slug = slugify(name)
                        tag, _ = Tag.objects.get_or_create(slug=tag_slug, defaults={'name': name})
                        problem.tags.add(tag)

                # Parse and associate companies
                if companies_raw:
                    company_names = [c.strip() for c in companies_raw.split('|') if c.strip()]
                    for name in company_names:
                        company_slug = slugify(name)
                        comp, _ = Company.objects.get_or_create(slug=company_slug, defaults={'name': name})
                        problem.companies.add(comp)

        self.stdout.write(self.style.SUCCESS(
            f'Import completed: {created_count} created, {updated_count} updated, {skipped_count} skipped.'
        ))
