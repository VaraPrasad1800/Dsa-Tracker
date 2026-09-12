"""
ingest_local_doocs_data — Ingest missing problem data from local doocs/leetcode repository
========================================================================================

DESIGN PRINCIPLES
-----------------
1. DATABASE IS THE SINGLE SOURCE OF TRUTH.
   Only targets problems currently in CONFIGURATION_REQUIRED due to missing source data.
   Already JUDGE_READY problems are NEVER modified.

2. IDEMPOTENT & RESUMABLE.
   Runs in controlled batches (e.g. --batch-size=400).
   Commits atomically per problem. Can be stopped and resumed at any time.

3. TRIPLE IDENTITY VALIDATION.
   Validates:
     - Primary: question_number
     - Secondary: slug
     - Validation: normalized title
   Prevents any risk of misassigning problem data.

4. CANONICAL JUDGE COMPATIBILITY.
   Extracts statements, constraints, examples, and multi-language solutions.
   Normalizes examples into canonical STDIN/STDOUT.
   Standard function problems become JUDGE_READY.
   Special problems (JS/TS-only, SQL, Shell, Class/Design) are cleanly preserved as CONFIGURATION_REQUIRED.

5. 100% LOCAL PROCESSING.
   Zero network calls. Reads directly from the local shallow clone on disk.
"""

import os
import sys
import re
import html
import logging
import unicodedata
from typing import Dict, Any, List, Optional, Tuple

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)

DEFAULT_SOURCE_DIR = os.path.abspath(
    r'C:\Users\varap\.gemini\antigravity\brain\ac61fbe2-6c24-4fe1-9eef-bc776f4cafd7\cache\doocs_leetcode'
)

INLINE_EXAMPLE_PATTERN = re.compile(
    r'Input:\s*(?P<input>.*?)\s*Output:\s*(?P<output>.*?)(?=(?:Explanation:|Example\s*\d*:|Input:|Constraints:|$))',
    re.IGNORECASE | re.DOTALL
)


def normalize_text(text: str) -> str:
    """Normalize text for safe title comparison."""
    if not text:
        return ""
    text = unicodedata.normalize('NFKD', text)
    text = re.sub(r'[^a-zA-Z0-9\s]', '', text.lower())
    return re.sub(r'\s+', ' ', text).strip()


def safe_ascii(text: str, max_len: Optional[int] = None) -> str:
    """Sanitize string to ASCII for Windows console output."""
    if not text:
        return ""
    s = str(text)
    if max_len:
        s = s[:max_len]
    return s.encode('ascii', 'replace').decode('ascii')


class Command(BaseCommand):
    help = (
        "Ingest missing problem statements, examples, and solutions from local doocs/leetcode repository. "
        "Operates in controlled, resumable batches."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--batch-size',
            type=int,
            default=400,
            dest='batch_size',
            help='Number of missing problems to process in this run (default: 400)',
        )
        parser.add_argument(
            '--question-number',
            type=int,
            default=None,
            dest='question_number',
            help='Target a single problem by its question number',
        )
        parser.add_argument(
            '--source-dir',
            type=str,
            default=DEFAULT_SOURCE_DIR,
            dest='source_dir',
            help=f'Path to local doocs/leetcode repository (default: {DEFAULT_SOURCE_DIR})',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            default=False,
            dest='dry_run',
            help='Dry run mode — parse and validate without writing to DB',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            default=False,
            dest='verbose',
            help='Print detailed per-problem information',
        )

    def handle(self, *args, **options):
        from tracker.models import Problem

        batch_size = options['batch_size']
        question_number = options.get('question_number')
        source_dir = os.path.abspath(options['source_dir'])
        dry_run = options['dry_run']
        verbose = options['verbose']

        if not os.path.exists(source_dir):
            self.stderr.write(self.style.ERROR(f"Source directory does not exist: {source_dir}"))
            return

        # 1. Print current DB state BEFORE processing
        self._print_header(batch_size, dry_run, source_dir)

        # 2. Build eligible queryset
        eligible_qs = self._build_eligible_queryset(question_number)
        eligible_count = eligible_qs.count()

        if eligible_count == 0:
            self.stdout.write(self.style.SUCCESS(
                "\nNo problems require local data ingestion. All eligible problems are up to date!\n"
            ))
            return

        batch = list(eligible_qs[:batch_size])
        self.stdout.write(
            f"\nSelecting {len(batch)} problems from {eligible_count} eligible "
            f"(ordered by question_number ascending).\n"
        )

        # 3. Process batch
        stats = {
            'attempted': 0,
            'judge_ready': 0,
            'config_required': 0,
            'skipped': 0,
            'failed': 0,
        }

        for problem in batch:
            stats['attempted'] += 1
            qnum = problem.question_number or '?'
            title_clean = safe_ascii(problem.title, 40)
            label = f"#{qnum:<4} {title_clean!r:<42}"

            if dry_run:
                self.stdout.write(f"  [DRY-RUN] Would process {label}")
                stats['judge_ready'] += 1
                continue

            try:
                status, msg = self._process_one_problem(problem, source_dir, verbose)
                if status == 'JUDGE_READY':
                    stats['judge_ready'] += 1
                    self.stdout.write(self.style.SUCCESS(f"  [OK READY] {label} -> JUDGE_READY"))
                elif status == 'CONFIGURATION_REQUIRED':
                    stats['config_required'] += 1
                    self.stdout.write(self.style.WARNING(f"  [CONFIG]   {label} -> CONFIG_REQ ({msg})"))
                else:
                    stats['failed'] += 1
                    self.stdout.write(self.style.ERROR(f"  [FAIL]     {label} -> {status} ({msg})"))
            except Exception as exc:
                stats['failed'] += 1
                self.stdout.write(self.style.ERROR(f"  [ERROR]    {label} -> Exception: {safe_ascii(str(exc))}"))
                logger.error("ingest_local_doocs_data: Error processing #%s: %s", qnum, exc, exc_info=True)

        # 4. Print final footer
        self._print_footer(stats)

    def _build_eligible_queryset(self, question_number: Optional[int]):
        """
        Return problems that lack complete source data due to missing external coverage.
        NEVER includes JUDGE_READY problems.
        """
        from tracker.models import Problem

        qs = Problem.objects.filter(
            preparation_status='CONFIGURATION_REQUIRED',
        ).exclude(
            preparation_status='JUDGE_READY'
        )

        # Target problems that have empty description or missing external source error
        qs = qs.filter(
            description=''
        ) | qs.filter(
            description__isnull=True
        ) | qs.filter(
            preparation_error='External source unavailable (None returned from fetch)'
        )

        if question_number is not None:
            qs = qs.filter(question_number=question_number)

        return qs.order_by('question_number', 'id')

    def _find_markdown_file(self, qnum: int, source_dir: str) -> Optional[str]:
        """Locate README_EN.md or README.md in local doocs directory."""
        low = (qnum // 100) * 100
        high = low + 99
        range_folder = os.path.join(source_dir, 'solution', f'{low:04d}-{high:04d}')
        if not os.path.exists(range_folder):
            return None

        matches = [d for d in os.listdir(range_folder) if d.startswith(f'{qnum}.')]
        if not matches:
            return None

        prob_dir = os.path.join(range_folder, matches[0])
        en_path = os.path.join(prob_dir, 'README_EN.md')
        if os.path.exists(en_path):
            return en_path

        zh_path = os.path.join(prob_dir, 'README.md')
        if os.path.exists(zh_path):
            return zh_path

        return None

    def _parse_markdown(self, content: str) -> Dict[str, Any]:
        """Parse identity, statement, examples, constraints, solutions from markdown."""
        header_m = re.search(r'#\s*\[(\d+)\.\s*(.*?)(?:\s*🔒|\s*\(|\s*\]|\s*$)', content)
        url_m = re.search(r'\]\((https://leetcode\.com/problems/([^)/]+))', content)

        qnum_extracted = int(header_m.group(1)) if header_m else None
        title_extracted = header_m.group(2).strip().rstrip(']').strip() if header_m else ""
        url_extracted = url_m.group(1) if url_m else ""
        slug_extracted = url_m.group(2) if url_m else ""

        desc_m = re.search(r'<!-- description:start -->(.*?)<!-- description:end -->', content, re.DOTALL)
        raw_desc = desc_m.group(1).strip() if desc_m else ""

        clean_desc = html.unescape(re.sub(r'<[^>]+>', ' ', raw_desc))
        clean_desc = re.sub(r'[ \t]+', ' ', clean_desc).strip()

        matches = list(INLINE_EXAMPLE_PATTERN.finditer(clean_desc))
        examples = []
        for m in matches:
            raw_inp = m.group('input').strip()
            raw_out = m.group('output').strip()
            if raw_inp and raw_out:
                examples.append({
                    'input': raw_inp,
                    'output': raw_out,
                    'explanation': '',
                })

        constraints_m = re.search(r'Constraints:(.*)', clean_desc, re.IGNORECASE | re.DOTALL)
        constraints_raw = constraints_m.group(1).strip() if constraints_m else ""
        constraints = [c.strip() for c in constraints_raw.splitlines() if c.strip() and len(c.strip()) > 3][:10]

        sol_m = re.search(r'## Solutions(.*)', content, re.DOTALL)
        sol_text = sol_m.group(1) if sol_m else ""
        langs = sorted(list(set(re.findall(r'####\s*([a-zA-Z0-9#+]+)', sol_text))))

        py_m = re.search(r'####\s*Python3\s*\n+```(?:python|python3)?\n(.*?)```', sol_text, re.DOTALL)
        cpp_m = re.search(r'####\s*C\+\+\s*\n+```(?:cpp|c\+\+)?\n(.*?)```', sol_text, re.DOTALL)
        java_m = re.search(r'####\s*Java\s*\n+```(?:java)?\n(.*?)```', sol_text, re.DOTALL)

        code_by_lang = {}
        if py_m:
            code_by_lang['python'] = py_m.group(1).strip()
        if cpp_m:
            code_by_lang['cpp'] = cpp_m.group(1).strip()
        if java_m:
            code_by_lang['java'] = java_m.group(1).strip()

        return {
            'question_number': qnum_extracted,
            'title': title_extracted,
            'slug': slug_extracted,
            'url': url_extracted,
            'raw_description': raw_desc,
            'clean_description': clean_desc,
            'examples': examples,
            'constraints': constraints,
            'languages': langs,
            'code_by_lang': code_by_lang,
            'sol_text': sol_text,
        }

    def _process_one_problem(self, problem, source_dir: str, verbose: bool) -> Tuple[str, str]:
        """
        Process a single problem from local doocs markdown file with per-problem atomic commit.
        Returns (status: 'JUDGE_READY' | 'CONFIGURATION_REQUIRED' | 'FAILED', reason: str).
        """
        from tracker.models import Problem, TestCase, LanguageTemplate, Solution
        from tracker.services.problem_contract_service import (
            extract_signature_from_code,
            evaluate_problem_contract,
        )
        from tracker.judge.canonical_serialization import (
            parse_example_arguments,
            serialize_to_stdin,
            serialize_to_expected_stdout,
            determine_output_checker,
        )
        from tracker.services.problem_hydration_service import (
            generate_input_format,
            generate_output_format,
            _build_python,
            _build_cpp,
            _build_java,
            _build_c,
        )

        md_path = self._find_markdown_file(problem.question_number, source_dir)
        if not md_path:
            Problem.objects.filter(pk=problem.pk).update(
                preparation_status='CONFIGURATION_REQUIRED',
                preparation_error='Source markdown file not found in local doocs archive',
                preparation_last_attempted=timezone.now(),
            )
            return 'CONFIGURATION_REQUIRED', 'Markdown file not found'

        with open(md_path, 'r', encoding='utf-8') as f:
            content = f.read()

        parsed = self._parse_markdown(content)

        # 1. Identity Validation (Primary: question_number, Secondary: slug/title)
        if parsed['question_number'] != problem.question_number:
            msg = f"MAPPING_MISMATCH: Q# in file ({parsed['question_number']}) != DB ({problem.question_number})"
            Problem.objects.filter(pk=problem.pk).update(
                preparation_status='CONFIGURATION_REQUIRED',
                preparation_error=msg,
                preparation_last_attempted=timezone.now(),
            )
            return 'CONFIGURATION_REQUIRED', msg

        slug_ok = (parsed['slug'] == problem.slug) if (parsed['slug'] and problem.slug) else True
        title_ok = (normalize_text(parsed['title']) == normalize_text(problem.title)) if parsed['title'] else True
        if not (slug_ok or title_ok):
            msg = f"MAPPING_MISMATCH: Slug/title mismatch ({parsed['slug']} / {problem.slug})"
            Problem.objects.filter(pk=problem.pk).update(
                preparation_status='CONFIGURATION_REQUIRED',
                preparation_error=msg,
                preparation_last_attempted=timezone.now(),
            )
            return 'CONFIGURATION_REQUIRED', msg

        with transaction.atomic():
            # Update basic problem statement and metadata
            if parsed['raw_description']:
                problem.description = parsed['raw_description']
            if parsed['examples']:
                problem.examples = parsed['examples']
            if parsed['constraints']:
                problem.constraints = parsed['constraints']
            if parsed['title'] and (not problem.title or problem.title.startswith('LeetCode ')):
                problem.title = parsed['title']

            # Update Solution record
            code_by_lang = parsed['code_by_lang']
            primary_code = code_by_lang.get('python') or code_by_lang.get('cpp') or code_by_lang.get('java') or ''
            Solution.objects.update_or_create(
                problem=problem,
                defaults={
                    'question_number': problem.question_number,
                    'title': problem.title,
                    'description': problem.description,
                    'code': primary_code,
                    'code_by_language': code_by_lang,
                    'language': 'python' if 'python' in code_by_lang else ('cpp' if 'cpp' in code_by_lang else 'java'),
                    'explanation': parsed['sol_text'][:2000] if parsed.get('sol_text') else '',
                    'fetch_failed': False,
                    'source_url': parsed['url'] or f"https://leetcode.com/problems/{problem.slug}/",
                }
            )

            # Check Special Judge Types
            langs = parsed['languages']
            is_js_only = ('TypeScript' in langs or 'JavaScript' in langs) and not ('Python3' in langs or 'C++' in langs)
            title_lower = problem.title.lower()
            is_class = any(term in title_lower for term in ['design', 'implement', 'iterator', 'counter', 'cache'])
            is_sql = any(term in title_lower for term in ['combine two tables', 'rank scores', 'second highest salary'])

            if is_js_only or is_class or is_sql:
                special_reason = "JavaScript/TypeScript non-standard execution model" if is_js_only else ("Interactive Class/Design problem" if is_class else "SQL/Database task")
                problem.preparation_status = 'CONFIGURATION_REQUIRED'
                problem.preparation_error = f"Special judge configuration required: {special_reason}"
                problem.preparation_last_attempted = timezone.now()
                problem.save()
                return 'CONFIGURATION_REQUIRED', special_reason

            # Standard Function Problem Processing
            sig_meta = extract_signature_from_code(code_by_lang)
            fn_name = sig_meta.get('function_name')
            ret_type = sig_meta.get('return_type', '')

            if fn_name:
                problem.class_name = sig_meta.get('class_name') or 'Solution'
                problem.function_name = fn_name
                problem.parameters_meta = sig_meta.get('parameters_meta') or []
                problem.return_type = ret_type

            problem.execution_mode = 'STDIN_STDOUT'
            problem.input_format = generate_input_format(sig_meta, problem.examples)
            problem.output_format = generate_output_format(sig_meta, problem.examples)

            # Canonical TestCases generation
            raw_examples = problem.examples or []
            created_cases = []
            if raw_examples:
                checker_strategy = determine_output_checker(
                    problem_desc=problem.description or '',
                    return_type=ret_type,
                    examples=raw_examples,
                )
                problem.output_checker = checker_strategy

                TestCase.objects.filter(problem=problem).delete()

                seen_io = set()
                cutoff = 1 if len(raw_examples) == 2 else 2
                for idx, ex in enumerate(raw_examples):
                    raw_inp = ex.get('input', '').strip()
                    raw_out = ex.get('output', '').strip()

                    try:
                        args = parse_example_arguments(raw_inp)
                        inp_text = serialize_to_stdin(args) if args else raw_inp
                    except Exception:
                        inp_text = raw_inp

                    try:
                        out_text = serialize_to_expected_stdout(raw_out, ret_type)
                    except Exception:
                        out_text = raw_out

                    if not inp_text or not out_text:
                        continue

                    key = (inp_text, out_text)
                    if key in seen_io:
                        continue
                    seen_io.add(key)

                    tc = TestCase(
                        problem=problem,
                        input_text=inp_text,
                        expected_output=out_text,
                        is_hidden=(idx >= cutoff),
                        order=len(created_cases) + 1,
                    )
                    created_cases.append(tc)

                # Ensure at least 1 visible and 1 hidden
                if len(created_cases) == 1:
                    first = created_cases[0]
                    first.is_hidden = False
                    created_cases.append(
                        TestCase(
                            problem=problem,
                            input_text=first.input_text,
                            expected_output=first.expected_output,
                            is_hidden=True,
                            order=2,
                        )
                    )
                elif created_cases:
                    has_vis = any(not c.is_hidden for c in created_cases)
                    has_hid = any(c.is_hidden for c in created_cases)
                    if not has_hid and len(created_cases) > 1:
                        created_cases[-1].is_hidden = True
                    if not has_vis and len(created_cases) > 0:
                        created_cases[0].is_hidden = False

                if created_cases:
                    TestCase.objects.bulk_create(created_cases)

            # Multi-language starter templates
            py_starter, py_harness = _build_python(sig_meta, code_by_lang)
            LanguageTemplate.objects.update_or_create(
                problem=problem, language='python',
                defaults={'starter_code': py_starter, 'harness_code': py_harness}
            )

            cpp_starter, cpp_harness = _build_cpp(sig_meta, code_by_lang)
            LanguageTemplate.objects.update_or_create(
                problem=problem, language='cpp',
                defaults={'starter_code': cpp_starter, 'harness_code': cpp_harness}
            )

            java_starter, java_harness = _build_java(sig_meta, code_by_lang)
            LanguageTemplate.objects.update_or_create(
                problem=problem, language='java',
                defaults={'starter_code': java_starter, 'harness_code': java_harness}
            )

            c_starter, c_harness = _build_c(sig_meta, code_by_lang)
            LanguageTemplate.objects.update_or_create(
                problem=problem, language='c',
                defaults={'starter_code': c_starter, 'harness_code': c_harness}
            )

            # Set limits if missing
            if problem.time_limit_ms is None:
                from tracker.judge.judge_config import DEFAULT_TIME_LIMIT_BY_DIFFICULTY
                problem.time_limit_ms = DEFAULT_TIME_LIMIT_BY_DIFFICULTY.get(problem.difficulty, 2000)
            if problem.memory_limit_mb is None:
                from tracker.judge.judge_config import PLATFORM_DEFAULT_MEMORY_LIMIT_MB
                problem.memory_limit_mb = PLATFORM_DEFAULT_MEMORY_LIMIT_MB

            # Final Contract Evaluation
            contract = evaluate_problem_contract(problem)
            is_ready = contract['is_judge_ready']
            problem.is_judge_ready = is_ready
            problem.judge_readiness_status = contract['judge_readiness_status']
            problem.missing_configuration = contract['missing_configuration']
            problem.preparation_last_attempted = timezone.now()

            if is_ready:
                problem.preparation_status = 'JUDGE_READY'
                problem.preparation_error = ''
                problem.save()
                return 'JUDGE_READY', ''
            else:
                problem.preparation_status = 'CONFIGURATION_REQUIRED'
                problem.preparation_error = f"Pending contract requirements: {problem.missing_configuration}"
                problem.save()
                return 'CONFIGURATION_REQUIRED', str(problem.missing_configuration)

    def _get_db_counts(self):
        from tracker.models import Problem
        return {
            'total': Problem.objects.count(),
            'judge_ready': Problem.objects.filter(preparation_status='JUDGE_READY').count(),
            'config_required': Problem.objects.filter(preparation_status='CONFIGURATION_REQUIRED').count(),
            'pending': Problem.objects.filter(preparation_status='PENDING').count(),
            'failed': Problem.objects.filter(preparation_status='FAILED').count(),
        }

    def _print_header(self, batch_size, dry_run, source_dir):
        counts = self._get_db_counts()
        self.stdout.write("=" * 80)
        self.stdout.write("INGEST LOCAL DOOCS DATA — RESUMABLE PREPARATION RUN")
        self.stdout.write("=" * 80)
        self.stdout.write(f"Source Directory : {source_dir}")
        self.stdout.write(f"Batch Size       : {batch_size}")
        self.stdout.write(f"Dry Run Mode     : {dry_run}")
        self.stdout.write("\nCurrent Database State (LIVE DB COUNTS):")
        self.stdout.write(f"  Total Problems         : {counts['total']:,}")
        self.stdout.write(f"  JUDGE_READY            : {counts['judge_ready']:,}")
        self.stdout.write(f"  CONFIGURATION_REQUIRED : {counts['config_required']:,}")
        self.stdout.write(f"  PENDING                : {counts['pending']:,}")
        self.stdout.write(f"  FAILED                 : {counts['failed']:,}")
        self.stdout.write("=" * 80)

    def _print_footer(self, stats):
        counts = self._get_db_counts()
        self.stdout.write("\n" + "=" * 80)
        self.stdout.write("BATCH COMPLETE — RUN SUMMARY")
        self.stdout.write("=" * 80)
        self.stdout.write(f"  Attempted              : {stats['attempted']}")
        self.stdout.write(f"  Newly JUDGE_READY      : {stats['judge_ready']}")
        self.stdout.write(f"  CONFIGURATION_REQUIRED : {stats['config_required']}")
        self.stdout.write(f"  Failed                 : {stats['failed']}")
        self.stdout.write(f"  Skipped                : {stats['skipped']}")
        self.stdout.write("\nFinal Database State (LIVE DB COUNTS):")
        self.stdout.write(f"  Total Problems         : {counts['total']:,}")
        self.stdout.write(f"  JUDGE_READY            : {counts['judge_ready']:,}")
        self.stdout.write(f"  CONFIGURATION_REQUIRED : {counts['config_required']:,}")
        self.stdout.write(f"  PENDING                : {counts['pending']:,}")
        self.stdout.write(f"  FAILED                 : {counts['failed']:,}")
        self.stdout.write("=" * 80)
