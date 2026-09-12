import os
import tempfile
from django.test import TestCase
from django.core.management import call_command
from rest_framework.test import APIClient
from rest_framework import status
from tracker.models import Problem

class QuestionNumberTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.p1 = Problem.objects.create(
            title='Two Sum',
            slug='two-sum',
            question_number=1,
            difficulty='Easy'
        )
        self.p42 = Problem.objects.create(
            title='Trapping Rain Water',
            slug='trapping-rain-water',
            question_number=42,
            difficulty='Hard'
        )
        self.p11 = Problem.objects.create(
            title='Container With Most Water',
            slug='container-with-most-water',
            question_number=11,
            difficulty='Medium'
        )

    def test_search_by_exact_question_number(self):
        res = self.client.get('/api/problems/?search=42')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        results = res.data['results']
        self.assertTrue(len(results) >= 1)
        self.assertEqual(results[0]['question_number'], 42)
        self.assertEqual(results[0]['title'], 'Trapping Rain Water')

    def test_search_by_hash_question_number(self):
        res = self.client.get('/api/problems/?search=%231')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        results = res.data['results']
        self.assertEqual(results[0]['question_number'], 1)
        self.assertEqual(results[0]['title'], 'Two Sum')

    def test_search_by_partial_title(self):
        res = self.client.get('/api/problems/?search=trapping')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        results = res.data['results']
        self.assertEqual(results[0]['question_number'], 42)
        self.assertEqual(results[0]['title'], 'Trapping Rain Water')

    def test_problem_detail_includes_question_number(self):
        res = self.client.get(f'/api/problems/{self.p42.id}/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['question_number'], 42)
        self.assertEqual(res.data['title'], 'Trapping Rain Water')

    def test_csv_import_with_question_number(self):
        csv_content = (
            "question_number,title,difficulty,topic,companies,source_url\n"
            "100,Same Tree,Easy,Tree|Binary Tree,Google,https://leetcode.com/problems/same-tree\n"
        )
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(csv_content)
            temp_path = f.name

        try:
            call_command('import_dsa_problems', csv=temp_path)
            imported = Problem.objects.filter(question_number=100).first()
            self.assertIsNotNone(imported)
            self.assertEqual(imported.title, 'Same Tree')
            self.assertEqual(imported.question_number, 100)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_csv_import_validation_duplicate_and_invalid(self):
        csv_content = (
            "question_number,title,difficulty\n"
            "invalid,Bad Problem,Easy\n"
            "42,Conflict Problem,Medium\n"
            "200,Valid Problem,Medium\n"
            "200,Duplicate In CSV,Hard\n"
        )
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(csv_content)
            temp_path = f.name

        try:
            call_command('import_dsa_problems', csv=temp_path)
            # 'invalid' question number skipped
            self.assertFalse(Problem.objects.filter(slug='bad-problem').exists())
            # 42 conflict with existing Trapping Rain Water skipped
            self.assertFalse(Problem.objects.filter(slug='conflict-problem').exists())
            # 200 first is created, duplicate is skipped
            self.assertTrue(Problem.objects.filter(slug='valid-problem', question_number=200).exists())
            self.assertFalse(Problem.objects.filter(slug='duplicate-in-csv').exists())
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)
