"""Invoice module used in-process by B and in a separate process by C."""

def apply_event(db, event):
    if event['status'] not in ('active', 'void') or event['version'] < 1 or event['amount_minor'] <= 0:
        raise ValueError('Invalid invoice event')
    db.execute('''INSERT INTO invoices VALUES (?,?,?,?)
        ON CONFLICT(booking_id) DO UPDATE SET
        status=excluded.status, version=excluded.version
        WHERE excluded.version > invoices.version''',
        (event['booking_id'], event['amount_minor'], event['status'], event['version']))
