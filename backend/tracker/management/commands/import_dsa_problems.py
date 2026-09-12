import csv
import os
import re
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from tracker.models import Problem, Tag, Company

VALID_DIFFICULTIES = {'Easy', 'Medium', 'Hard'}
URL_REGEX = re.compile(r'^https?://', re.IGNORECASE)

class Command(BaseCommand):
    help = 'Import DSA problems from a CSV file with question_number support, validation, duplicate detection, and --dry-run support'

    def add_arguments(self, parser):
        parser.add_argument('--csv', type=str, required=True, help='Path to the CSV file')
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Validate and simulate import without modifying database'
        )

    def handle(self, *args, **options):
        csv_path = options['csv']
        dry_run = options.get('dry_run', False)

        if not os.path.isabs(csv_path):
            csv_path = os.path.abspath(csv_path)

        if not os.path.exists(csv_path):
            self.stderr.write(self.style.ERROR(f'CSV file not found: {csv_path}'))
            return

        if dry_run:
            self.stdout.write(self.style.WARNING('[DRY RUN MODE] Database will not be modified.'))

        created_count = 0
        updated_count = 0
        skipped_count = 0
        warnings = []
        seen_slugs = set()
        seen_question_numbers = set()

        with open(csv_path, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            line_no = 1
            has_qn_column = any(
                col in (reader.fieldnames or [])
                for col in ['question_number', 'question_no', 'leetcode_id', '#']
            )

            for row in reader:
                line_no += 1
                title = row.get('title', '') or row.get('Title', '')
                title = title.strip()
                difficulty = row.get('difficulty', '') or row.get('Difficulty', '')
                difficulty = difficulty.strip()
                topics_raw = row.get('topic', '') or row.get('Topics', '') or row.get('tags', '')
                topics_raw = topics_raw.strip()
                companies_raw = row.get('companies', '') or row.get('Companies', '')
                companies_raw = companies_raw.strip()
                source_url = row.get('source_url', '') or row.get('Link', '') or row.get('url', '')
                source_url = source_url.strip()
                source_platform = row.get('source_platform', 'LeetCode').strip()

                if not title:
                    warnings.append(f'Line {line_no}: Skipped - missing title.')
                    skipped_count += 1
                    continue

                slug = slugify(title)
                if slug in seen_slugs:
                    warnings.append(f'Line {line_no}: Duplicate title/slug in CSV: "{title}" ({slug}).')
                seen_slugs.add(slug)

                # Question Number Extraction & Validation
                raw_qn = (
                    row.get('question_number')
                    or row.get('question_no')
                    or row.get('leetcode_id')
                    or row.get('#')
                )

                q_num = None
                if raw_qn is not None and str(raw_qn).strip():
                    cleaned_qn = str(raw_qn).strip().lstrip('#').strip()
                    if not cleaned_qn.isdigit() or int(cleaned_qn) <= 0:
                        warnings.append(f'Line {line_no}: Skipped - invalid/non-numeric question_number "{raw_qn}".')
                        skipped_count += 1
                        continue
                    q_num = int(cleaned_qn)

                    # Duplicate question_number in CSV
                    if q_num in seen_question_numbers:
                        warnings.append(f'Line {line_no}: Skipped - duplicate question_number #{q_num} in CSV ("{title}").')
                        skipped_count += 1
                        continue
                    seen_question_numbers.add(q_num)

                    # Conflicting existing question_number in DB
                    conflict = Problem.objects.filter(question_number=q_num).exclude(slug=slug).first()
                    if conflict:
                        warnings.append(
                            f'Line {line_no}: Skipped - conflicting question_number #{q_num} already used by "{conflict.title}".'
                        )
                        skipped_count += 1
                        continue

                    # Conflicting slug with a different question_number
                    existing_slug = Problem.objects.filter(slug=slug).first()
                    if existing_slug and existing_slug.question_number != q_num:
                        warnings.append(
                            f'Line {line_no}: Slug "{slug}" exists with #{existing_slug.question_number}, updating to #{q_num}.'
                        )
                elif has_qn_column:
                    warnings.append(f'Line {line_no}: Skipped - missing question_number for "{title}".')
                    skipped_count += 1
                    continue
                else:
                    # CSV did not have a question_number column; preserve existing or assign next available
                    existing_prob = Problem.objects.filter(slug=slug).first()
                    if existing_prob and existing_prob.question_number:
                        q_num = existing_prob.question_number
                    else:
                        from django.db.models import Max
                        max_val = Problem.objects.aggregate(Max('question_number'))['question_number__max'] or 0
                        q_num = max_val + 1

                if not difficulty or difficulty.capitalize() not in VALID_DIFFICULTIES:
                    warnings.append(f'Line {line_no}: "{title}" has invalid difficulty "{difficulty}". Defaulting to Medium.')
                    difficulty = 'Medium'
                else:
                    difficulty = difficulty.capitalize()

                if source_url and not URL_REGEX.match(source_url):
                    warnings.append(f'Line {line_no}: "{title}" has malformed source_url "{source_url}".')

                if dry_run:
                    exists = Problem.objects.filter(slug=slug).exists()
                    if exists:
                        updated_count += 1
                    else:
                        created_count += 1
                    continue

                problem, created = Problem.objects.update_or_create(
                    slug=slug,
                    defaults={
                        'title': title,
                        'question_number': q_num,
                        'leetcode_id': q_num,
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
                    if len(tag_names) == 1 and ',' in tag_names[0]:
                        tag_names = [t.strip() for t in tag_names[0].split(',') if t.strip()]
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

        for w in warnings[:20]:
            self.stdout.write(self.style.WARNING(w))
        if len(warnings) > 20:
            self.stdout.write(self.style.WARNING(f'... and {len(warnings) - 20} more warnings.'))

        prefix = '[DRY RUN] ' if dry_run else ''
        self.stdout.write(self.style.SUCCESS(
            f'{prefix}Import completed: {created_count} created, {updated_count} updated, {skipped_count} skipped. Total warnings: {len(warnings)}'
        ))

