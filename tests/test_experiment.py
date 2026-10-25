import unittest
from rental.experiment import run_experiments


class Experiment(unittest.TestCase):
    def test_scenarios_have_actual_outcomes_and_explicit_applicability(self):
        report = run_experiments(repeats=2)
        self.assertEqual(report['repeats'], 2)
        rows = report['observations']
        self.assertEqual(len(rows), 36)
        applicable = [r for r in rows if r['applicable']]
        self.assertEqual(len(applicable), 24)
        self.assertTrue(all(r['passed'] for r in applicable), applicable)
        self.assertTrue(all(r['passed'] is None for r in rows if not r['applicable']))
        crash = [r for r in rows if r['scenario'] == 'exit_after_commit' and r['applicable']]
        self.assertEqual([r['before_recovery']['pending'] for r in crash], [1, 1])
        self.assertEqual([len(r['before_recovery']['invoices']) for r in crash], [1, 1])
        self.assertTrue(report['migration']['preserved'])
        self.assertEqual(report['pricing']['coupled'], {'historical': 350000, 'new': 315000})
