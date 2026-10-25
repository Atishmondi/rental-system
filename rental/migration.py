"""Paused cutover protocol. Source invoices retained for pre-resume rollback."""
from pathlib import Path
from .storage import connect, setting, set_setting, INVOICES, invoice_rows


def _require(db, phase):
    if setting(db, 'paused') != '1' or setting(db, 'migration') != phase:
        raise ValueError('Migration requires paused phase: ' + phase)


def _verify(source, target):
    with connect(target) as other:
        if invoice_rows(source) != invoice_rows(other):
            raise ValueError('Invoice verification failed; keep paused and investigate or rollback')


def pause(path):
    with connect(Path(path) / 'booking.sqlite', True) as db:
        if setting(db, 'mode') == 'split' or setting(db, 'migration') != 'none':
            raise ValueError('Only unmigrated single-database architectures can begin migration')
        set_setting(db, 'previous_mode', setting(db, 'mode'))
        set_setting(db, 'paused', '1')
        set_setting(db, 'migration', 'paused')


def prepare(path):
    path = Path(path)
    with connect(path / 'booking.sqlite', True) as db:
        _require(db, 'paused')
        target = path / 'invoice.sqlite'
        # Exclusive creation protects any existing destination, including corrupt
        # copies retained as evidence after an interrupted or rolled-back attempt.
        try:
            with target.open('xb'):
                pass
        except FileExistsError as exc:
            raise ValueError('Destination exists; archive it before retrying') from exc
        with connect(target, True) as other:
            other.execute(INVOICES)
            other.executemany('INSERT INTO invoices VALUES (?,?,?,?)',
                              [(r['booking_id'], r['amount_minor'], r['status'], r['version']) for r in invoice_rows(db)])
        _verify(db, target)
        set_setting(db, 'migration', 'prepared')


def activate(path):
    path = Path(path)
    with connect(path / 'booking.sqlite', True) as db:
        _require(db, 'prepared')
        _verify(db, path / 'invoice.sqlite')
        set_setting(db, 'mode', 'split')
        set_setting(db, 'migration', 'activated')


def resume(path):
    path = Path(path)
    with connect(path / 'booking.sqlite', True) as db:
        _require(db, 'activated')
        _verify(db, path / 'invoice.sqlite')
        set_setting(db, 'paused', '0')
        set_setting(db, 'migration', 'resumed')


def rollback(path):
    with connect(Path(path) / 'booking.sqlite', True) as db:
        if setting(db, 'paused') != '1' or setting(db, 'migration') not in ('paused', 'prepared', 'activated'):
            raise ValueError('Rollback allowed only before resume')
        set_setting(db, 'mode', setting(db, 'previous_mode'))
        set_setting(db, 'migration', 'none')
        set_setting(db, 'paused', '0')
