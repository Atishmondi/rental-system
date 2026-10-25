"""Booking commands. A inlines invoices; B invokes a module; C records an outbox."""
import json
from pathlib import Path
from .storage import connect, init_booking, setting, set_setting, invoice_rows, INVOICES
from .pricing import terms
from .invoicing import apply_event


class Rental:
    def __init__(self, path, mode='coupled'):
        if mode not in ('coupled', 'modular', 'split'):
            raise ValueError('Unknown architecture')
        self.path = Path(path).resolve()
        self.path.mkdir(parents=True, exist_ok=True)
        init_booking(self.path / 'booking.sqlite', mode)
        with connect(self.path / 'booking.sqlite') as db:
            active = setting(db, 'mode')
        # Never create a missing invoice store on reopening a split system.
        invoice = self.path / 'invoice.sqlite'
        if active == 'split' and not invoice.exists():
            with connect(self.path / 'booking.sqlite') as db:
                if db.execute('SELECT COUNT(*) FROM bookings').fetchone()[0]:
                    raise ValueError('Invoice database missing; restore it before continuing')
            with connect(invoice, True) as db:
                db.execute(INVOICES)

    @staticmethod
    def _writable(db):
        if setting(db, 'paused') == '1':
            raise ValueError('Bookings are paused for migration')

    def book(self, booking_id, item, start, end, rate):
        if not isinstance(booking_id, str) or not booking_id.strip() or not isinstance(item, str) or not item.strip():
            raise ValueError('Booking and item identifiers must be nonempty')
        with connect(self.path / 'booking.sqlite', True) as db:
            self._writable(db)
            rate_minor, amount = terms(start, end, rate, setting(db, 'policy'))
            old = db.execute('SELECT * FROM bookings WHERE id=?', (booking_id,)).fetchone()
            if old:
                if (old['item'], old['start'], old['end'], old['rate_minor'], old['status']) != (item, start, end, rate_minor, 'confirmed'):
                    raise ValueError('Booking ID already used for different or cancelled booking')
                return dict(old)
            if db.execute("SELECT 1 FROM bookings WHERE item=? AND status='confirmed' AND start < ? AND end > ?", (item, end, start)).fetchone():
                raise ValueError('Item is already reserved for overlapping dates')
            db.execute('INSERT INTO bookings VALUES (?,?,?,?,?,?,?,?)', (booking_id, item, start, end, rate_minor, amount, 'confirmed', 1))
            event = dict(booking_id=booking_id, amount_minor=amount, status='active', version=1)
            mode = setting(db, 'mode')
            if mode == 'coupled':
                db.execute('INSERT INTO invoices VALUES (?,?,?,?)', (booking_id, amount, 'active', 1))
            elif mode == 'modular':
                apply_event(db, event)
            else:
                db.execute('INSERT INTO outbox(payload) VALUES (?)', (json.dumps(event),))
            return dict(db.execute('SELECT * FROM bookings WHERE id=?', (booking_id,)).fetchone())

    def cancel(self, booking_id):
        with connect(self.path / 'booking.sqlite', True) as db:
            self._writable(db)
            old = db.execute('SELECT * FROM bookings WHERE id=?', (booking_id,)).fetchone()
            if not old:
                raise ValueError('Unknown booking')
            if old['status'] == 'cancelled':
                return
            version = old['version'] + 1
            db.execute("UPDATE bookings SET status='cancelled',version=? WHERE id=?", (version, booking_id))
            event = dict(booking_id=booking_id, amount_minor=old['amount_minor'], status='void', version=version)
            mode = setting(db, 'mode')
            if mode == 'coupled':
                db.execute("UPDATE invoices SET status='void',version=? WHERE booking_id=?", (version, booking_id))
            elif mode == 'modular':
                apply_event(db, event)
            else:
                db.execute('INSERT INTO outbox(payload) VALUES (?)', (json.dumps(event),))

    def set_policy(self, policy):
        if policy not in ('standard', 'weekly-discount'):
            raise ValueError('Unknown pricing policy')
        with connect(self.path / 'booking.sqlite', True) as db:
            self._writable(db)
            set_setting(db, 'policy', policy)

    def snapshot(self):
        with connect(self.path / 'booking.sqlite') as db:
            mode = setting(db, 'mode')
            result = dict(mode=mode, paused=setting(db, 'paused') == '1',
                          policy=setting(db, 'policy'), migration=setting(db, 'migration'),
                          bookings=[dict(r) for r in db.execute('SELECT * FROM bookings ORDER BY id')],
                          pending=db.execute('SELECT COUNT(*) FROM outbox WHERE delivered=0').fetchone()[0])
            if mode != 'split':
                result['invoices'] = invoice_rows(db)
        if mode == 'split':
            with connect(self.path / 'invoice.sqlite') as db:
                result['invoices'] = invoice_rows(db)
        return result
