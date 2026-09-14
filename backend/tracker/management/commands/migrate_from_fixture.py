import json
import os
import sys
import time
from collections import defaultdict
from django.core.management.base import BaseCommand, CommandError
from django.core.serializers import deserialize
from django.db import connection, transaction
from django.apps import apps
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = 'Resumable, high-performance migration of data_dump.json into Render PostgreSQL using bulk operations.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--fixture',
            type=str,
            default='data_dump.json',
            help='Path to the JSON fixture file'
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=500,
            help='Batch size for bulk inserts'
        )

    def handle(self, *args, **options):
        fixture_path = options['fixture']
        default_batch_size = options['batch_size']

        if not os.path.isabs(fixture_path):
            fixture_path = os.path.join(os.getcwd(), fixture_path)

        if not os.path.exists(fixture_path):
            raise CommandError(f"Fixture file not found: {fixture_path}")

        # Safety Check: Verify active engine is PostgreSQL
        engine = connection.settings_dict.get('ENGINE', '')
        if 'postgresql' not in engine:
            raise CommandError(
                f"SAFETY STOP: Database engine is '{engine}', NOT PostgreSQL! Refusing to run."
            )

        db_name = connection.settings_dict.get('NAME')
        db_host = connection.settings_dict.get('HOST', '')
        self.stdout.write(self.style.SUCCESS(
            f"=== TARGET DATABASE: {db_name} on {db_host} (PostgreSQL) ==="
        ))

        # 1. Read & Deserialize Fixture
        self.stdout.write(f"Reading fixture from {fixture_path}...")
        t0 = time.time()
        with open(fixture_path, 'r', encoding='utf-8') as f:
            json_text = f.read()

        file_size_mb = len(json_text.encode('utf-8')) / (1024 * 1024)
        self.stdout.write(f"Loaded {file_size_mb:.2f} MB JSON in {time.time() - t0:.2f}s. Deserializing...")

        t_deser = time.time()
        objects_by_model = defaultdict(list)
        m2m_by_model = defaultdict(list)

        total_deserialized = 0
        for obj in deserialize('json', json_text):
            m_cls = obj.object.__class__
            objects_by_model[m_cls].append(obj.object)
            if obj.m2m_data:
                m2m_by_model[m_cls].append((obj.object.pk, obj.m2m_data))
            total_deserialized += 1

        self.stdout.write(self.style.SUCCESS(
            f"Deserialized {total_deserialized} objects across {len(objects_by_model)} models in {time.time() - t_deser:.2f}s."
        ))

        # 2. Define Strict Dependency Order
        Token = apps.get_model('authtoken', 'Token')
        Tag = apps.get_model('tracker', 'Tag')
        Company = apps.get_model('tracker', 'Company')
        Achievement = apps.get_model('tracker', 'Achievement')
        UserPoints = apps.get_model('tracker', 'UserPoints')
        UserProfile = apps.get_model('tracker', 'UserProfile')
        UserStreak = apps.get_model('tracker', 'UserStreak')
        DailyStat = apps.get_model('tracker', 'DailyStat')
        Notification = apps.get_model('tracker', 'Notification')
        StudyPlan = apps.get_model('tracker', 'StudyPlan')
        UserAchievement = apps.get_model('tracker', 'UserAchievement')
        Problem = apps.get_model('tracker', 'Problem')
        Solution = apps.get_model('tracker', 'Solution')
        CompanyProblem = apps.get_model('tracker', 'CompanyProblem')
        UserProblemProgress = apps.get_model('tracker', 'UserProblemProgress')
        ReviewHistory = apps.get_model('tracker', 'ReviewHistory')
        StudyPlanDay = apps.get_model('tracker', 'StudyPlanDay')
        InterviewSession = apps.get_model('tracker', 'InterviewSession')
        InterviewProblem = apps.get_model('tracker', 'InterviewProblem')
        ActivityEvent = apps.get_model('tracker', 'ActivityEvent')

        dependency_ordered_models = [
            User,
            Token,
            Tag,
            Company,
            Achievement,
            UserPoints,
            UserProfile,
            UserStreak,
            DailyStat,
            Notification,
            StudyPlan,
            UserAchievement,
            Problem,
            Solution,
            CompanyProblem,
            UserProblemProgress,
            StudyPlanDay,
            InterviewSession,
            ActivityEvent,
            ReviewHistory,
            InterviewProblem,
        ]

        # 3. Process Each Model with Resumable Batch Insertion
        self.stdout.write("\n=== STARTING RESUMABLE BATCH MIGRATION ===")
        migration_stats = {}
        total_start_time = time.time()

        for model_cls in dependency_ordered_models:
            model_name = model_cls.__name__
            instances = objects_by_model.get(model_cls, [])
            source_count = len(instances)

            if source_count == 0:
                continue

            existing_pks = set(model_cls.objects.values_list('pk', flat=True))
            to_insert = [inst for inst in instances if inst.pk not in existing_pks]
            skipped_existing = source_count - len(to_insert)

            if len(to_insert) == 0:
                self.stdout.write(self.style.SUCCESS(
                    f"[OK] {model_name:22} | Source: {source_count:5} | Skipped: {skipped_existing:5} | Inserted:     0 | Errors: 0 | Remaining: 0"
                ))
                migration_stats[model_name] = {
                    'source': source_count,
                    'inserted': 0,
                    'skipped': skipped_existing,
                    'errors': 0,
                    'remaining': 0,
                }
                continue

            batch_size = default_batch_size
            if model_cls in (Solution, Problem):
                batch_size = min(default_batch_size, 200)

            inserted_count = 0
            error_count = 0
            model_start_time = time.time()

            self.stdout.write(
                f"[>] {model_name:22} | Inserting {len(to_insert)} new records (Batch: {batch_size}, Skipped: {skipped_existing})..."
            )

            for i in range(0, len(to_insert), batch_size):
                batch = to_insert[i:i + batch_size]
                try:
                    with transaction.atomic():
                        model_cls.objects.bulk_create(batch, batch_size=batch_size)
                    inserted_count += len(batch)
                except Exception as batch_err:
                    self.stdout.write(self.style.WARNING(
                        f"    [!] Batch {i//batch_size + 1} hit error: {batch_err}. Falling back to row-by-row..."
                    ))
                    for inst in batch:
                        try:
                            with transaction.atomic():
                                inst.save(force_insert=True)
                            inserted_count += 1
                        except Exception as row_err:
                            error_count += 1
                            self.stdout.write(self.style.ERROR(
                                f"    [FAIL] {model_name} pk={inst.pk}: {row_err}"
                            ))

                pct = ((i + len(batch)) / len(to_insert)) * 100
                elapsed = time.time() - model_start_time
                self.stdout.write(
                    f"    {model_name:20} -> {inserted_count}/{len(to_insert)} ({pct:5.1f}%) | elapsed: {elapsed:5.1f}s"
                )

            remaining = source_count - (skipped_existing + inserted_count)
            migration_stats[model_name] = {
                'source': source_count,
                'inserted': inserted_count,
                'skipped': skipped_existing,
                'errors': error_count,
                'remaining': remaining,
            }

            status_style = self.style.SUCCESS if error_count == 0 else self.style.ERROR
            self.stdout.write(status_style(
                f"[OK] {model_name:22} | Source: {source_count:5} | Skipped: {skipped_existing:5} | Inserted: {inserted_count:5} | Errors: {error_count:2} | Remaining: {remaining:2}\n"
            ))

            if error_count > 0:
                raise CommandError(
                    f"STOPPED: {error_count} errors encountered while inserting {model_name}. Halting migration."
                )

        # 4. Process Many-to-Many Through Tables
        self.stdout.write("\n=== PROCESSING MANY-TO-MANY RELATIONSHIPS ===")
        m2m_definitions = [
            (Problem, 'tags', 'problem', 'tag'),
            (Problem, 'companies', 'problem', 'company'),
            (UserProfile, 'bookmarked_problems', 'userprofile', 'problem'),
            (StudyPlanDay, 'problems', 'studyplanday', 'problem'),
        ]

        for model_cls, field_name, src_col, tgt_col in m2m_definitions:
            m2m_records = m2m_by_model.get(model_cls, [])
            if not m2m_records:
                continue

            field = model_cls._meta.get_field(field_name)
            through_model = field.remote_field.through
            through_name = through_model.__name__

            desired_pairs = []
            for src_pk, m2m_dict in m2m_records:
                targets = m2m_dict.get(field_name, [])
                for tgt_pk in targets:
                    desired_pairs.append((src_pk, tgt_pk))

            source_count = len(desired_pairs)
            if source_count == 0:
                continue

            existing_pairs = set(
                through_model.objects.values_list(f"{src_col}_id", f"{tgt_col}_id")
            )
            to_insert_pairs = [pair for pair in desired_pairs if pair not in existing_pairs]
            skipped_existing = source_count - len(to_insert_pairs)

            if not to_insert_pairs:
                self.stdout.write(self.style.SUCCESS(
                    f"[OK] {through_name:30} | Total: {source_count:6} | Skipped: {skipped_existing:6} | Inserted:      0 | Errors: 0"
                ))
                continue

            instances = [
                through_model(**{f"{src_col}_id": p[0], f"{tgt_col}_id": p[1]})
                for p in to_insert_pairs
            ]

            inserted_count = 0
            error_count = 0
            for i in range(0, len(instances), 1000):
                batch = instances[i:i + 1000]
                try:
                    with transaction.atomic():
                        through_model.objects.bulk_create(batch, batch_size=1000)
                    inserted_count += len(batch)
                except Exception as m2m_err:
                    self.stdout.write(self.style.WARNING(
                        f"    [!] M2M Batch failed: {m2m_err}. Falling back to row-by-row..."
                    ))
                    for inst in batch:
                        try:
                            with transaction.atomic():
                                inst.save()
                            inserted_count += 1
                        except Exception as row_err:
                            error_count += 1
                            self.stdout.write(self.style.ERROR(f"    [FAIL] M2M: {row_err}"))

            self.stdout.write(self.style.SUCCESS(
                f"[OK] {through_name:30} | Total: {source_count:6} | Skipped: {skipped_existing:6} | Inserted: {inserted_count:6} | Errors: {error_count}"
            ))

        # 5. Reset PostgreSQL Sequences for Integer AutoField Models
        self.stdout.write("\n=== RESETTING POSTGRESQL SEQUENCES ===")
        from django.core.management.color import no_style
        sequence_sql = connection.ops.sequence_reset_sql(no_style(), dependency_ordered_models)
        if sequence_sql:
            with connection.cursor() as cursor:
                for sql in sequence_sql:
                    cursor.execute(sql)
            self.stdout.write(self.style.SUCCESS(f"Successfully reset {len(sequence_sql)} PostgreSQL sequences."))

        total_elapsed = time.time() - total_start_time
        self.stdout.write(self.style.SUCCESS(
            f"\n=== MIGRATION FINISHED IN {total_elapsed:.1f}s ({total_elapsed/60:.2f} mins) ==="
        ))
