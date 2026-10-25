import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class CLI(unittest.TestCase):
    def test_cli_roundtrip_and_errors(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'demo'
            def run(*args):
                return subprocess.run([sys.executable, '-m', 'rental', '--path', str(path), *args], capture_output=True, text=True)
            missing = run('status')
            self.assertNotEqual(missing.returncode, 0)
            self.assertFalse(path.exists())
            created = run('init', '--mode', 'split')
            self.assertEqual(created.returncode, 0, created.stderr)
            booked = run('book', 'A', 'camera', '2026-10-20', '2026-10-23', '500')
            self.assertEqual(booked.returncode, 0, booked.stderr)
            self.assertEqual(json.loads(run('status').stdout)['pending'], 1)
            self.assertEqual(run('dispatch').returncode, 0)
            self.assertEqual(json.loads(run('status').stdout)['invoices'][0]['amount_minor'], 150000)
            invalid = run('book', 'B', 'camera', '2026-10-21', '2026-10-23', '500')
            self.assertNotEqual(invalid.returncode, 0)
            self.assertNotIn('Traceback', invalid.stderr)
            self.assertEqual(run('cancel', 'A').returncode, 0)
            self.assertEqual(run('dispatch').returncode, 0)
            self.assertEqual(json.loads(run('status').stdout)['invoices'][0]['status'], 'void')
