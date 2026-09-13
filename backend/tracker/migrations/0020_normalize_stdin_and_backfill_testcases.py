"""
Data migration:
1. Backfill is_sample on TestCase (is_sample = not is_hidden).
2. Backfill judging_mode and parameter_schema on Problem.
3. Backfill time_limit_seconds on Problem.
4. Normalize stdin input_text and expected_output across all TestCase rows.
"""

from django.db import migrations


def forward_normalize_and_backfill(apps, schema_editor):
    Problem = apps.get_model('tracker', 'Problem')
    TestCase = apps.get_model('tracker', 'TestCase')

    # 1. Backfill is_sample on TestCase
    TestCase.objects.filter(is_hidden=True).update(is_sample=False)
    TestCase.objects.filter(is_hidden=False).update(is_sample=True)

    # 2. Backfill judging_mode and parameter_schema on Problem
    Problem.objects.filter(execution_mode='FUNCTION').update(judging_mode='function')
    Problem.objects.filter(execution_mode='STDIN_STDOUT').update(judging_mode='stdio')

    # Backfill parameter_schema and time_limit_seconds for problems
    for p in Problem.objects.iterator(chunk_size=500):
        changed = False
        if not p.parameter_schema and p.parameters_meta:
            p.parameter_schema = p.parameters_meta
            changed = True
        if p.time_limit_seconds is None and p.time_limit_ms:
            p.time_limit_seconds = round(p.time_limit_ms / 1000.0, 2)
            changed = True
        if changed:
            p.save(update_fields=['parameter_schema', 'time_limit_seconds'])

    # 3. Normalize all TestCase stdin input_text and expected_output (if judge package available)
    try:
        from tracker.judge.canonical_serialization import normalize_stdin_text, normalize_expected_output_text
    except ImportError:
        def normalize_stdin_text(t): return t
        def normalize_expected_output_text(t): return t

    for tc in TestCase.objects.iterator(chunk_size=500):
        orig_in = tc.input_text or ""
        orig_out = tc.expected_output or ""

        norm_in = normalize_stdin_text(orig_in)
        norm_out = normalize_expected_output_text(orig_out)

        if norm_in != orig_in or norm_out != orig_out:
            tc.input_text = norm_in
            tc.expected_output = norm_out
            tc.save(update_fields=['input_text', 'expected_output'])


def reverse_normalize_and_backfill(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('tracker', '0019_online_judge_schema_hardening'),
    ]

    operations = [
        migrations.RunPython(forward_normalize_and_backfill, reverse_normalize_and_backfill),
    ]
