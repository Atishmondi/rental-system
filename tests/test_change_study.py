import json
import hashlib
from pathlib import Path
import tempfile
import unittest
import subprocess
from unittest.mock import patch

from rental.change_study import run_change_study


class ChangeStudyTests(unittest.TestCase):
    def test_failed_upgrade_does_not_produce_success_narrative(self):
        real_run = subprocess.run
        def fail_after(*args, **kwargs):
            result = real_run(*args, **kwargs)
            if kwargs.get('cwd') and Path(kwargs['cwd']).name == 'after':
                result.returncode = 1
            return result
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'failed'
            with patch('rental.change_study.subprocess.run', side_effect=fail_after):
                result = run_change_study(output)
            self.assertFalse(result['passed'])
            report = (output / 'report.md').read_text()
            self.assertIn('did not pass', report)
            self.assertNotIn('changed source passes', report)
            self.assertEqual(report.count('| FAIL |'), 3)

    def test_retained_sources_and_red_green_upgrade(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'evidence'
            result = run_change_study(output)
            self.assertTrue(result['passed'])
            self.assertEqual(len(result['architectures']), 3)
            for row in result['architectures']:
                self.assertEqual(row['changed_files'], ['pricing.py'])
                self.assertEqual(row['added_lines'], 2)
                self.assertEqual(row['removed_lines'], 0)
                self.assertEqual([r['returncode'] for r in row['runs']], [0, 1, 0])
                observed = json.loads(row['runs'][2]['stdout'])
                self.assertEqual(observed['historical'], 350000)
                self.assertEqual(observed['new'], 315000)
                self.assertEqual(observed['six_days'], 300000)
                self.assertEqual(observed['rounded'], 32)
                self.assertTrue((output / row['mode'] / 'change.diff').is_file())
                for stage in ('before', 'after'):
                    for name, digest in row['source_sha256'][stage].items():
                        saved = output / row['mode'] / stage / 'rental' / name
                        self.assertEqual(hashlib.sha256(saved.read_bytes()).hexdigest(), digest)
            original = (output / 'manifest.json').read_bytes()
            with self.assertRaises(FileExistsError):
                run_change_study(output)
            self.assertEqual((output / 'manifest.json').read_bytes(), original)
