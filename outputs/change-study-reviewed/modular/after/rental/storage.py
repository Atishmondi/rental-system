"""SQLite connection lifecycle and experiment schemas."""
import sqlite3
from contextlib import contextmanager

INVOICES = '''CREATE TABLE IF NOT EXISTS invoices (
    booking_id TEXT PRIMARY KEY, amount_minor INTEGER NOT NULL CHECK(amount_minor>0),
    status TEXT NOT NULL CHECK(status IN ('active','void')), version INTEGER NOT NULL)'''


@contextmanager
def connect(path, write=False):
    db = sqlite3.connect(str(path), timeout=10)
    db.row_factory = sqlite3.Row
    try:
        if write:
            db.execute('BEGIN IMMEDIATE')
        yield db
        db.commit()
    except BaseException:
        db.rollback()
        raise
    finally:
        db.close()


def init_booking(path, mode):
    with connect(path, True) as db:
        db.execute('CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)')
        for key, value in [('mode', mode), ('paused', '0'), ('policy', 'standard'), ('migration', 'none')]:
            db.execute('INSERT OR IGNORE INTO meta VALUES (?,?)', (key, value))
        db.execute('''CREATE TABLE IF NOT EXISTS bookings (
            id TEXT PRIMARY KEY, item TEXT NOT NULL, start TEXT NOT NULL, end TEXT NOT NULL,
            rate_minor INTEGER NOT NULL, amount_minor INTEGER NOT NULL,
            status TEXT NOT NULL, version INTEGER NOT NULL)''')
        db.execute(INVOICES)
        db.execute('''CREATE TABLE IF NOT EXISTS outbox (
            id INTEGER PRIMARY KEY AUTOINCREMENT, payload TEXT NOT NULL,
            delivered INTEGER NOT NULL DEFAULT 0)''')


def setting(db, key):
    return db.execute('SELECT value FROM meta WHERE key=?', (key,)).fetchone()[0]


def set_setting(db, key, value):
    db.execute('INSERT OR REPLACE INTO meta VALUES (?,?)', (key, str(value)))


def invoice_rows(db):
    return [dict(r) for r in db.execute('SELECT * FROM invoices ORDER BY booking_id')]
