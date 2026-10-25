import sqlite3
import tempfile
import unittest
from pathlib import Path
from rental.app import Rental
from rental.transport import dispatch
from rental.migration import pause, prepare, activate, resume, rollback


class Migration(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)
        self.app = Rental(self.path, 'modular')
        self.app.book('A', 'camera', '2026-10-20', '2026-10-23', '500')
        self.app.book('B', 'light', '2026-10-20', '2026-10-23', '100')
        self.app.cancel('B')
        self.original = self.app.snapshot()['invoices']

    def test_migrate_populated_state_then_continue_and_reject_rollback(self):
        pause(self.path)
        prepare(self.path)
        activate(self.path)
        self.assertEqual(self.app.snapshot()['invoices'], self.original)
        self.assertTrue(self.app.snapshot()['paused'])
        with self.assertRaises(ValueError):
            dispatch(self.path)
        resume(self.path)
        self.app.cancel('A')
        self.app.book('C', 'camera', '2026-10-20', '2026-10-23', '500')
        dispatch(self.path)
        self.assertEqual([(i['booking_id'], i['status']) for i in self.app.snapshot()['invoices']], [('A', 'void'), ('B', 'void'), ('C', 'active')])
        with self.assertRaises(ValueError):
            rollback(self.path)

    def test_pause_persists_on_reopen_and_blocks_all_changes(self):
        pause(self.path)
        reopened = Rental(self.path)
        for fn in [lambda: reopened.cancel('A'), lambda: reopened.book('C', 'x', '2026-10-20', '2026-10-23', '500'), lambda: reopened.set_policy('weekly-discount')]:
            with self.assertRaises(ValueError):
                fn()
        rollback(self.path)
        reopened.cancel('A')
        self.assertEqual(reopened.snapshot()['invoices'][0]['status'], 'void')

    def test_corrupt_copy_blocks_cutover_and_source_survives(self):
        pause(self.path)
        prepare(self.path)
        with sqlite3.connect(self.path / 'invoice.sqlite') as db:
            db.execute("UPDATE invoices SET amount_minor=1 WHERE booking_id='A'")
        with self.assertRaises(ValueError):
            activate(self.path)
        self.assertEqual(self.app.snapshot()['mode'], 'modular')
        rollback(self.path)
        self.assertEqual(self.app.snapshot()['invoices'], self.original)

    def test_corruption_after_activate_blocks_resume(self):
        pause(self.path)
        prepare(self.path)
        activate(self.path)
        with sqlite3.connect(self.path / 'invoice.sqlite') as db:
            db.execute("UPDATE invoices SET status='void' WHERE booking_id='A'")
        with self.assertRaises(ValueError):
            resume(self.path)
        self.assertTrue(self.app.snapshot()['paused'])
        rollback(self.path)
        self.assertEqual(self.app.snapshot()['mode'], 'modular')
        self.assertEqual(self.app.snapshot()['invoices'], self.original)

    def test_wrong_phase_does_not_migrate(self):
        for fn in (prepare, activate, resume, rollback):
            with self.assertRaises(ValueError):
                fn(self.path)
        pause(self.path)
        with self.assertRaises(ValueError):
            activate(self.path)
        prepare(self.path)
        with self.assertRaises(ValueError):
            prepare(self.path)

    def test_existing_destination_is_not_overwritten(self):
        pause(self.path)
        (self.path / 'invoice.sqlite').write_bytes(b'preserve me')
        with self.assertRaises(ValueError):
            prepare(self.path)
        self.assertEqual((self.path / 'invoice.sqlite').read_bytes(), b'preserve me')

    def test_coupled_source_supported(self):
        with tempfile.TemporaryDirectory() as directory:
            app = Rental(directory, 'coupled')
            app.book('A', 'camera', '2026-10-20', '2026-10-23', '500')
            pause(directory)
            prepare(directory)
            activate(directory)
            resume(directory)
            self.assertEqual(app.snapshot()['mode'], 'split')
            self.assertEqual(app.snapshot()['invoices'][0]['amount_minor'], 150000)
