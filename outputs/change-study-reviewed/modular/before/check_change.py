import json, sys
from pathlib import Path
from rental.app import Rental
from rental.transport import dispatch
path, mode, stage = sys.argv[1:]
app = Rental(Path(path), mode)
if stage == 'seed':
    app.book('historical', 'old-camera', '2026-10-01', '2026-10-08', '500')
    # In split mode deliberately leave the historical invoice pending at upgrade.
    result = {'historical': app.snapshot()['bookings'][0]['amount_minor']}
    expected = {'historical': 350000}
else:
    app.set_policy('weekly-discount')
    app.book('new', 'camera', '2026-10-01', '2026-10-08', '500')
    app.book('six_days', 'light', '2026-10-01', '2026-10-07', '500')
    app.book('rounded', 'stand', '2026-10-01', '2026-10-08', '0.05')
    if mode == 'split':
        dispatch(app.path)
    result = {r['booking_id']: r['amount_minor'] for r in app.snapshot()['invoices']}
    expected = {'historical': 350000, 'new': 315000, 'six_days': 300000, 'rounded': 32}
print(json.dumps(result, sort_keys=True))
sys.exit(0 if result == expected else 1)
