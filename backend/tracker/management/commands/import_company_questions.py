import os
import csv
import json
import re
import requests
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify
from tracker.models import Problem, Tag, Company, CompanyProblem


class Command(BaseCommand):
    help = (
        'Import company-wise questions from leetcode-company-wise-problems repository. '
        'Parses all company folders and time-period CSVs, maps exact LeetCode IDs, '
        'deduplicates questions, and creates CompanyProblem relationships.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--data-dir',
            type=str,
            default='',
            help='Path to cloned leetcode-company-wise-problems repository directory'
        )
        parser.add_argument(
            '--company',
            type=str,
            default='',
            help='Filter to import only a specific company (e.g. Google, Amazon, Meta)'
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=0,
            help='Limit the number of companies processed (useful for testing)'
        )
        parser.add_argument(
            '--clear-old',
            action='store_true',
            help='Delete old problems before importing'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview changes without saving to the database'
        )

    def _load_leetcode_mapping(self, data_dir: str) -> dict:
        """Load or fetch the authoritative slug -> {id, title, paid_only, difficulty} mapping."""
        possible_paths = [
            os.path.join(data_dir, '..', 'leetcode_mapping.json'),
            os.path.join(data_dir, 'leetcode_mapping.json'),
            'data/leetcode_mapping.json',
            'backend/data/leetcode_mapping.json',
        ]
        for p in possible_paths:
            norm_p = os.path.normpath(p)
            if os.path.isfile(norm_p):
                try:
                    with open(norm_p, 'r', encoding='utf-8') as f:
                        mapping = json.load(f)
                        self.stdout.write(f"Loaded LeetCode problem catalog with {len(mapping)} problems from {norm_p}")
                        return mapping
                except Exception as e:
                    self.stderr.write(f"Error loading {norm_p}: {e}")

        # Fallback: fetch from LeetCode public API
        self.stdout.write("Fetching full LeetCode problem catalog from LeetCode public API...")
        try:
            url = 'https://leetcode.com/api/problems/all/'
            resp = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=20)
            resp.raise_for_status()
            data = resp.json()
            mapping = {}
            diff_map = {1: 'Easy', 2: 'Medium', 3: 'Hard'}
            for pair in data.get('stat_status_pairs', []):
                stat = pair.get('stat', {})
                slug = stat.get('question__title_slug')
                fid = stat.get('frontend_question_id')
                title = stat.get('question__title')
                paid_only = pair.get('paid_only', False)
                d_level = pair.get('difficulty', {}).get('level', 1)
                if slug:
                    mapping[slug] = {
                        'id': fid,
                        'title': title,
                        'paid_only': paid_only,
                        'difficulty': diff_map.get(d_level, 'Medium')
                    }
            self.stdout.write(f"Fetched {len(mapping)} problems from LeetCode API.")
            return mapping
        except Exception as e:
            self.stderr.write(self.style.WARNING(f"Could not load LeetCode mapping: {e}"))
            return {}

    def _extract_slug_from_link(self, link: str, title: str) -> str:
        """Extract problem title slug from leetcode.com/problems/{slug} link."""
        if link:
            match = re.search(r'leetcode\.com/problems/([^/?#]+)', link)
            if match:
                return match.group(1).strip().lower()
        return slugify(title).lower()

    def _normalize_difficulty(self, diff: str) -> str:
        """Normalize difficulty to 'Easy', 'Medium', or 'Hard'."""
        d = diff.strip().capitalize()
        if d.upper() == 'EASY':
            return 'Easy'
        if d.upper() == 'MEDIUM':
            return 'Medium'
        if d.upper() == 'HARD':
            return 'Hard'
        return d if d in ('Easy', 'Medium', 'Hard') else 'Medium'

    def _extract_time_period(self, filename: str) -> str:
        """
        Convert filename like '1. Thirty Days.csv' -> 'Thirty Days',
        '2. Three Months.csv' -> 'Three Months', '5. All.csv' -> 'All'
        """
        base = os.path.splitext(filename)[0]
        cleaned = re.sub(r'^\d+[\.\-\s]+', '', base).strip()
        return cleaned or base

    def handle(self, *args, **options):
        data_dir = options.get('data_dir')
        target_company = options.get('company', '').strip().lower()
        limit = options.get('limit', 0)
        clear_old = options.get('clear_old', False)
        dry_run = options.get('dry_run', False)

        # Locate dataset directory
        if not data_dir:
            for candidate in ['data/company_problems', 'backend/data/company_problems']:
                if os.path.isdir(candidate):
                    data_dir = candidate
                    break

        if not data_dir or not os.path.isdir(data_dir):
            self.stderr.write(self.style.ERROR(
                f"Company problems directory not found at '{data_dir}'. "
                "Please specify --data-dir or clone repository into backend/data/company_problems"
            ))
            return

        self.stdout.write(f"Using company questions data directory: {os.path.abspath(data_dir)}")

        # Load authoritative LeetCode catalog
        leetcode_catalog = self._load_leetcode_mapping(data_dir)

        # Optional: clear old dummy questions
        if clear_old:
            if dry_run:
                self.stdout.write(self.style.WARNING("Dry run: Would delete existing problems."))
            else:
                self.stdout.write(self.style.WARNING("Purging old problems dataset..."))
                Problem.objects.all().delete()
                self.stdout.write(self.style.SUCCESS("Existing problems purged."))

        # Enumerate company directories
        company_dirs = []
        for item in sorted(os.listdir(data_dir)):
            full_path = os.path.join(data_dir, item)
            if os.path.isdir(full_path) and not item.startswith('.'):
                if target_company and item.lower() != target_company:
                    continue
                company_dirs.append((item, full_path))

        if limit > 0:
            company_dirs = company_dirs[:limit]

        self.stdout.write(f"Found {len(company_dirs)} company folders to process.")

        # Statistics
        stats = {
            'companies_processed': 0,
            'csv_files_processed': 0,
            'questions_created': 0,
            'questions_updated': 0,
            'duplicate_occurrences': 0,
            'company_problems_created': 0,
            'errors': 0,
        }

        # Cache models in memory to prevent repetitive round-trips
        self.stdout.write("Caching database indexes in memory for high performance...")
        tag_cache = {t.name.lower(): t for t in Tag.objects.all()}
        company_cache = {c.name.lower(): c for c in Company.objects.all()}
        problem_cache = {p.slug: p for p in Problem.objects.all()}
        cp_cache = {
            (cp.company_id, cp.problem_id, cp.time_period): cp
            for cp in CompanyProblem.objects.all()
        }

        for company_name, company_path in company_dirs:
            stats['companies_processed'] += 1
            csv_files = [f for f in os.listdir(company_path) if f.endswith('.csv')]
            csv_files.sort()

            # Ensure company exists in DB
            company_obj = company_cache.get(company_name.lower())
            if not company_obj and not dry_run:
                company_obj, _ = Company.objects.get_or_create(
                    slug=slugify(company_name),
                    defaults={'name': company_name}
                )
                company_cache[company_name.lower()] = company_obj

            self.stdout.write(f"Processing [{stats['companies_processed']}/{len(company_dirs)}] {company_name} ({len(csv_files)} CSVs)...")

            # Batch process company within a single atomic transaction
            if not dry_run:
                transaction_context = transaction.atomic()
            else:
                from contextlib import nullcontext
                transaction_context = nullcontext()

            with transaction_context:
                for csv_file in csv_files:
                    stats['csv_files_processed'] += 1
                    time_period = self._extract_time_period(csv_file)
                    fpath = os.path.join(company_path, csv_file)

                    try:
                        with open(fpath, 'r', encoding='utf-8', errors='ignore') as fp:
                            reader = csv.DictReader(fp)
                            for row in reader:
                                raw_title = row.get('Title', '').strip()
                                raw_link = row.get('Link', '').strip()
                                raw_diff = row.get('Difficulty', '').strip()
                                raw_freq = row.get('Frequency', '').strip()
                                raw_accept = row.get('Acceptance Rate', '').strip()
                                raw_topics = row.get('Topics', '').strip()

                                if not raw_title and not raw_link:
                                    continue

                                slug = self._extract_slug_from_link(raw_link, raw_title)
                                if not slug:
                                    continue

                                catalog_entry = leetcode_catalog.get(slug, {})
                                leetcode_id = catalog_entry.get('id')
                                official_title = catalog_entry.get('title') or raw_title
                                is_premium = catalog_entry.get('paid_only', False)

                                try:
                                    frequency = float(raw_freq) if raw_freq else 0.0
                                except ValueError:
                                    frequency = 0.0

                                try:
                                    acceptance_rate = float(raw_accept) if raw_accept else None
                                except ValueError:
                                    acceptance_rate = None

                                difficulty = self._normalize_difficulty(
                                    catalog_entry.get('difficulty') or raw_diff or 'Medium'
                                )

                                canonical_url = raw_link or f"https://leetcode.com/problems/{slug}"
                                if not canonical_url.startswith('http'):
                                    canonical_url = f"https://leetcode.com/problems/{slug}"

                                if dry_run:
                                    stats['questions_created'] += 1
                                    continue

                                # Retrieve or create canonical Problem
                                problem_obj = problem_cache.get(slug)
                                if not problem_obj:
                                    problem_obj = Problem.objects.create(
                                        slug=slug,
                                        title=official_title,
                                        difficulty=difficulty,
                                        source_url=canonical_url,
                                        source_platform='LeetCode',
                                        leetcode_id=leetcode_id,
                                        is_premium=is_premium,
                                        frequency=int(round(frequency)),
                                    )
                                    problem_cache[slug] = problem_obj
                                    stats['questions_created'] += 1
                                else:
                                    stats['duplicate_occurrences'] += 1
                                    # Update problem if richer data available
                                    updated = False
                                    if not problem_obj.leetcode_id and leetcode_id:
                                        problem_obj.leetcode_id = leetcode_id
                                        updated = True
                                    if not problem_obj.is_premium and is_premium:
                                        problem_obj.is_premium = is_premium
                                        updated = True
                                    if frequency > problem_obj.frequency:
                                        problem_obj.frequency = int(round(frequency))
                                        updated = True
                                    if not problem_obj.source_url and canonical_url:
                                        problem_obj.source_url = canonical_url
                                        updated = True
                                    if updated:
                                        problem_obj.save(update_fields=['leetcode_id', 'is_premium', 'frequency', 'source_url'])
                                        stats['questions_updated'] += 1

                                # Associate Company with Problem (ManyToManyField)
                                if company_obj:
                                    problem_obj.companies.add(company_obj)

                                    # Associate CompanyProblem record
                                    cp_key = (company_obj.id, problem_obj.id, time_period)
                                    if cp_key not in cp_cache:
                                        cp = CompanyProblem.objects.create(
                                            company=company_obj,
                                            problem=problem_obj,
                                            time_period=time_period,
                                            frequency=frequency,
                                            acceptance_rate=acceptance_rate,
                                        )
                                        cp_cache[cp_key] = cp
                                        stats['company_problems_created'] += 1

                                # Associate topic tags
                                if raw_topics:
                                    topic_names = [t.strip() for t in re.split(r'[,|]', raw_topics) if t.strip()]
                                    for tname in topic_names:
                                        t_key = tname.lower()
                                        tag_obj = tag_cache.get(t_key)
                                        if not tag_obj:
                                            tag_slug = slugify(tname)
                                            tag_obj, _ = Tag.objects.get_or_create(
                                                slug=tag_slug,
                                                defaults={'name': tname}
                                            )
                                            tag_cache[t_key] = tag_obj
                                        problem_obj.tags.add(tag_obj)

                    except Exception as e:
                        stats['errors'] += 1
                        self.stderr.write(f"Error processing {fpath}: {e}")

        # Summary Report
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS("LEETCODE COMPANY QUESTIONS IMPORT COMPLETE"))
        self.stdout.write("=" * 60)
        self.stdout.write(f"Companies processed:           {stats['companies_processed']}")
        self.stdout.write(f"CSV files processed:           {stats['csv_files_processed']}")
        self.stdout.write(f"Canonical questions created:   {stats['questions_created']}")
        self.stdout.write(f"Canonical questions updated:   {stats['questions_updated']}")
        self.stdout.write(f"Duplicate occurrences linked:  {stats['duplicate_occurrences']}")
        self.stdout.write(f"Company-problem list entries:  {stats['company_problems_created']}")
        self.stdout.write(f"Errors encountered:            {stats['errors']}")
        self.stdout.write("=" * 60)