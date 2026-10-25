"""Local subprocess transport; at-least-once delivery, single dispatcher."""
import json
import subprocess
import sys
from pathlib import Path
from .storage import connect, setting


def deliver(invoice_path, event, fail_after_commit=False):
    command = [sys.executable, '-m', 'rental.worker', str(invoice_path)]
    if fail_after_commit:
        command.append('--exit-after-commit')
    result = subprocess.run(command, input=json.dumps(event), text=True, capture_output=True,
                            cwd=str(Path(__file__).resolve().parent.parent), timeout=15)
    return result.returncode == 0


def dispatch(path, fail_after_commit=False, unavailable=False):
    path = Path(path).resolve()
    sent, errors = 0, 0
    # Serialize dispatch with writes/migration. This local transport deliberately
    # prioritizes deterministic safety over throughput; timings include startup.
    with connect(path / 'booking.sqlite', True) as db:
        if setting(db, 'mode') != 'split':
            raise ValueError('Dispatch requires split architecture')
        if setting(db, 'paused') == '1':
            raise ValueError('Dispatch paused for migration')
        for row in db.execute('SELECT id,payload FROM outbox WHERE delivered=0 ORDER BY id').fetchall():
            try:
                ok = False if unavailable else deliver(path / 'invoice.sqlite', json.loads(row['payload']), fail_after_commit)
            except (OSError, subprocess.TimeoutExpired):
                ok = False
            if not ok:
                errors += 1
                break
            db.execute('UPDATE outbox SET delivered=1 WHERE id=?', (row['id'],))
            sent += 1
        pending = db.execute('SELECT COUNT(*) FROM outbox WHERE delivered=0').fetchone()[0]
    return dict(delivered=sent, failures=errors, pending=pending)
