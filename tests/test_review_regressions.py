"""Regression cases from independent review, exercised against public APIs/CLI."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from rental.app import Rental
from rental.pricing import terms
from rental import migration


class ReviewRegressions(unittest.TestCase):
    def test_fractional_minor_units_are_not_rounded_into_valid_rates(self):
        with self.assertRaises(ValueError):
            terms('2026-10-20', '2026-10-23', '1.000000000000000000000000000001', 'standard')

    def test_extreme_exponents_raise_validation_errors(self):
        for rate in ('1e999999999', '1e-999999999'):
            with self.subTest(rate=rate), self.assertRaises(ValueError):
                terms('2026-10-20', '2026-10-23', rate, 'standard')

    def test_exact_trailing_zero_rate_and_large_integer_boundary(self):
        self.assertEqual(terms('2026-10-20', '2026-10-23', '1.000000000000000000000000000000', 'standard'), (100, 300))
        self.assertEqual(terms('2026-10-20', '2026-10-21', '92233720368547758.07', 'standard'), (9223372036854775807, 9223372036854775807))
        with self.assertRaises(ValueError):
            terms('2026-10-20', '2026-10-22', '92233720368547758.07', 'standard')

    def test_cli_rollback_works_if_destination_disappears_before_resume(self):
        with tempfile.TemporaryDirectory() as directory:
            app = Rental(directory, 'modular')
            app.book('A', 'camera', '2026-10-20', '2026-10-23', '500')
            migration.pause(directory)
            migration.prepare(directory)
            migration.activate(directory)
            (Path(directory) / 'invoice.sqlite').unlink()
            command = [sys.executable, '-m', 'rental', '--path', directory, 'rollback']
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            state = json.loads(result.stdout)
            self.assertEqual(state['mode'], 'modular')
            self.assertFalse(state['paused'])
            self.assertEqual(state['invoices'][0]['amount_minor'], 150000)
