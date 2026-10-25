import json
import sqlite3
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from rental.app import Rental
from rental.transport import dispatch, deliver


class Contracts(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def apps(self):
        for mode in ('coupled', 'modular', 'split'):
            yield mode, Rental(self.root / mode, mode)

    def settle(self, mode, app):
        if mode == 'split':
            dispatch(app.path)
        return app.snapshot()

    def test_price_adjacent_dates_and_overlap(self):
        for mode, app in self.apps():
            with self.subTest(mode=mode):
                app.book('A', 'camera', '2026-10-20', '2026-10-23', '500.00')
                with self.assertRaises(ValueError):
                    app.book('B', 'camera', '2026-10-22', '2026-10-24', '500')
                app.book('C', 'camera', '2026-10-23', '2026-10-25', '500')
                state = self.settle(mode, app)
                self.assertEqual([r['amount_minor'] for r in state['invoices']], [150000, 100000])
                self.assertEqual(len(state['bookings']), 2)

    def test_cancellation_retains_void_invoice_and_frees_item(self):
        for mode, app in self.apps():
            app.book('A', 'camera', '2026-10-20', '2026-10-23', '500')
            app.cancel('A')
            app.cancel('A')
            app.book('B', 'camera', '2026-10-20', '2026-10-23', '500')
            state = self.settle(mode, app)
            self.assertEqual([(i['booking_id'], i['status']) for i in state['invoices']], [('A', 'void'), ('B', 'active')])
            self.assertEqual(state['bookings'][0]['version'], 2)

    def test_command_replay_and_conflicting_id(self):
        for mode, app in self.apps():
            args = ('A', 'camera', '2026-10-20', '2026-10-23', '500')
            app.book(*args)
            app.book(*args)
            with self.assertRaises(ValueError):
                app.book('A', 'other', '2026-10-20', '2026-10-23', '500')
            self.assertEqual(len(self.settle(mode, app)['invoices']), 1)
            app.cancel('A')
            with self.assertRaises(ValueError):
                app.book(*args)

    def test_invalid_inputs_do_not_persist(self):
        for mode, app in self.apps():
            for rate in ('NaN', 'Infinity', '-1', '0', '1.001', 'bad'):
                with self.subTest(mode=mode, rate=rate), self.assertRaises(ValueError):
                    app.book('A', 'camera', '2026-10-20', '2026-10-23', rate)
            for start, end in [('2026-10-23', '2026-10-20'), ('2026-10-20', '2026-10-20'), ('2026-02-30', '2026-03-02')]:
                with self.assertRaises(ValueError):
                    app.book('A', 'camera', start, end, '500')
            with self.assertRaises(ValueError):
                app.book('', 'camera', '2026-10-20', '2026-10-23', '500')
            with self.assertRaises(ValueError):
                app.cancel('missing')
            self.assertEqual(app.snapshot()['bookings'], [])

    def test_discount_boundary_rounding_and_historical_amount(self):
        for mode, app in self.apps():
            app.book('old', 'one', '2026-10-01', '2026-10-08', '500')
            app.set_policy('weekly-discount')
            app.book('new', 'two', '2026-10-01', '2026-10-08', '500')
            app.book('six', 'three', '2026-10-01', '2026-10-07', '500')
            app.book('round', 'four', '2026-10-01', '2026-10-08', '0.05')
            rows = {i['booking_id']: i['amount_minor'] for i in self.settle(mode, app)['invoices']}
            self.assertEqual(rows, {'old': 350000, 'new': 315000, 'six': 300000, 'round': 32})

    def test_storage_failure_is_atomic_in_single_database_versions(self):
        for mode in ('coupled', 'modular'):
            app = Rental(self.root / mode, mode)
            with sqlite3.connect(app.path / 'booking.sqlite') as db:
                db.execute("CREATE TRIGGER fail_invoice BEFORE INSERT ON invoices BEGIN SELECT RAISE(ABORT, 'storage unavailable'); END")
            with self.assertRaises(sqlite3.DatabaseError):
                app.book('A', 'camera', '2026-10-20', '2026-10-23', '500')
            self.assertEqual(app.snapshot()['bookings'], [])
            with sqlite3.connect(app.path / 'booking.sqlite') as db:
                db.execute('DROP TRIGGER fail_invoice')
            app.book('A', 'camera', '2026-10-20', '2026-10-23', '500')
            self.assertEqual(len(app.snapshot()['invoices']), 1)

    def test_concurrent_overlapping_bookings_only_one_succeeds(self):
        for mode, app in self.apps():
            def attempt(booking_id):
                try:
                    app.book(booking_id, 'camera', '2026-10-20', '2026-10-23', '500')
                    return True
                except ValueError:
                    return False
            with ThreadPoolExecutor(max_workers=2) as pool:
                self.assertEqual(sorted(pool.map(attempt, ['A', 'B'])), [False, True])
            self.assertEqual(len(self.settle(mode, app)['invoices']), 1)


class Recovery(unittest.TestCase):
    def setUp(self):
        Contracts.setUp(self)

    def test_outage_and_cancel_recover(self):
        app = Rental(self.root / 'outage', 'split')
        app.book('A', 'camera', '2026-10-20', '2026-10-23', '500')
        self.assertEqual(dispatch(app.path, unavailable=True)['pending'], 1)
        self.assertEqual(app.snapshot()['invoices'], [])
        app.cancel('A')
        self.assertEqual(dispatch(app.path, unavailable=True)['pending'], 2)
        self.assertEqual(dispatch(app.path)['pending'], 0)
        self.assertEqual([(i['status'], i['amount_minor']) for i in app.snapshot()['invoices']], [('void', 150000)])

    def test_worker_exit_after_commit_then_retry_has_one_invoice(self):
        app = Rental(self.root / 'crash', 'split')
        app.book('A', 'camera', '2026-10-20', '2026-10-23', '500')
        result = dispatch(app.path, fail_after_commit=True)
        self.assertEqual(result['pending'], 1)
        self.assertEqual(len(app.snapshot()['invoices']), 1)
        self.assertEqual(dispatch(app.path)['pending'], 0)
        self.assertEqual(len(app.snapshot()['invoices']), 1)

    def test_duplicate_and_reverse_delivery_cannot_resurrect_invoice(self):
        app = Rental(self.root / 'reverse', 'split')
        app.book('A', 'camera', '2026-10-20', '2026-10-23', '500')
        app.cancel('A')
        with sqlite3.connect(app.path / 'booking.sqlite') as db:
            events = [json.loads(row[0]) for row in db.execute('SELECT payload FROM outbox ORDER BY id')]
        for event in [events[1], events[0], events[1]]:
            self.assertTrue(deliver(app.path / 'invoice.sqlite', event))
        dispatch(app.path)
        self.assertEqual([(i['status'], i['version']) for i in app.snapshot()['invoices']], [('void', 2)])
