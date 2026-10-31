"""Offline regression tests for the redacted repository checker."""
import importlib.util
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('commit_safety', Path(__file__).resolve().parents[1] / 'check_commit_safety.py')
checker = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = checker
spec.loader.exec_module(checker)


class CommitSafetyTests(unittest.TestCase):
    def test_generated_and_private_paths_are_blocked(self):
        for path in ('backend/.env', '.env.local', '.venv2/bin/pip', '.local/archive/a.py',
                     'backend/cache.db-wal', 'backend/cache.sqlite3-shm', 'secrets/token', 'client.key'):
            with self.subTest(path=path):
                self.assertTrue(checker.prohibited_path(path))

    def test_examples_and_nested_tests_are_allowed(self):
        for path in ('.env.example', 'backend/.env.example', 'backend/tests/regression/test_calendar.py'):
            self.assertFalse(checker.prohibited_path(path))

    def test_real_token_shape_is_flagged_without_echoing_value(self):
        value = b'ntn_' + b'x' * 40
        findings = checker.inspect_text('sample.py', value)
        self.assertEqual(findings[0].rule, 'credential-token')
        self.assertNotIn(value.decode(), repr(findings))

    def test_documentation_placeholder_is_not_a_secret(self):
        self.assertEqual(checker.inspect_text('example', b'secret_your_integration_token_here'), [])

    def test_python_identifier_is_not_a_token(self):
        self.assertEqual(checker.inspect_text('sample.py', b'def test_staged_secret_is_checked_independently():'), [])

    def test_exact_local_value_is_always_detected(self):
        value = b'example_but_real_local_value'
        findings = checker.inspect_text('sample.py', value, (value,))
        self.assertEqual(findings[0].rule, 'local-sensitive-value')

    def test_synthetic_notion_url_is_allowed(self):
        self.assertEqual(checker.inspect_text('sample', b'https://notion.so/' + b'1' * 32), [])

    def test_private_notion_url_is_flagged_without_echoing_identifier(self):
        identifier = bytes(range(16)).hex().encode()
        findings = checker.inspect_text('sample', b'https://notion.so/Title-' + identifier)
        self.assertEqual(findings[0].rule, 'private-notion-url')
        self.assertNotIn(identifier.decode(), repr(findings))

    def test_staged_secret_is_checked_independently_of_working_tree(self):
        token = b'ntn_' + b'x' * 40
        with patch.object(checker, 'git', side_effect=[b'example.py\0', token]):
            count, findings = checker.inspect_staged(())
        self.assertEqual(count, 1)
        self.assertEqual(findings[0].rule, 'credential-token')
        self.assertIn('(staged)', findings[0].path)

    def test_no_staged_changes_is_not_an_error(self):
        with patch.object(checker, 'git', return_value=b''):
            self.assertEqual(checker.inspect_staged(()), (0, []))


if __name__ == '__main__':
    unittest.main()
