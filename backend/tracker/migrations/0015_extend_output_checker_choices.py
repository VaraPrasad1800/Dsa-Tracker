"""
Migration: Extend output_checker choices to include strategy-based validators.

This is a choices-only migration — no DB schema change required because the
field max_length=50 already accommodates all new choice keys.

New choices added:
  NORMALIZED_TEXT         — alias for NORMALIZED
  BOOLEAN                 — true/false case-insensitive comparison
  INTEGER                 — numeric integer equality
  FLOAT_WITH_TOLERANCE    — floating-point with 1e-5 tolerance
  ARRAY                   — ordered space-separated array comparison
  ORDER_INSENSITIVE_ARRAY — multiset (any-order) array comparison
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tracker', '0014_problem_memory_limit_mb_problem_time_limit_ms'),
    ]

    operations = [
        migrations.AlterField(
            model_name='problem',
            name='output_checker',
            field=models.CharField(
                choices=[
                    ('EXACT', 'Exact match (character-for-character)'),
                    ('NORMALIZED', 'Normalized text (whitespace-insensitive)'),
                    ('NORMALIZED_TEXT', 'Normalized text (whitespace-insensitive)'),
                    ('ALTERNATIVES', 'Multiple Valid Alternatives (pipe-separated)'),
                    ('JSON', 'JSON Equality'),
                    ('BOOLEAN', 'Boolean (true/false, case-insensitive)'),
                    ('INTEGER', 'Integer (numeric equality)'),
                    ('FLOAT_WITH_TOLERANCE', 'Float with 1e-5 tolerance'),
                    ('ARRAY', 'Ordered Array (space-separated elements)'),
                    ('ORDER_INSENSITIVE_ARRAY', 'Order-Insensitive Array (multiset equality)'),
                ],
                default='NORMALIZED',
                help_text='Output validator mode for judging solutions',
                max_length=50,
            ),
        ),
    ]
