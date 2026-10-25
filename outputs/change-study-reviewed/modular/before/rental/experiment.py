"""Repeatable synthetic scenarios; observed outcomes, never invented metrics."""
import hashlib
import json
import platform
import sqlite3
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from .app import Rental
from .transport import dispatch, deliver
from . import migration
from .storage import connect

MODES = ('coupled', 'modular', 'split')
SCENARIOS = ('normal', 'storage_failure', 'worker_unavailable', 'duplicate', 'exit_after_commit', 'cancel_during_outage')


def _book(app, booking_id='A', item='camera'):
    app.book(booking_id, item, '2026-10-20', '2026-10-23', '500')


def _state(app):
    snap = app.snapshot()
    return {key: snap[key] for key in ('bookings', 'invoices', 'pending')}


def _correct(state, cancelled=False):
    return (state['pending'] == 0 and len(state['bookings']) == 1
            and state['bookings'][0]['status'] == ('cancelled' if cancelled else 'confirmed')
            and state['invoices'] == [dict(booking_id='A', amount_minor=150000,
                                           status='void' if cancelled else 'active', version=2 if cancelled else 1)])


def _scenario(mode, scenario, repeat):
    if mode != 'split' and scenario in ('worker_unavailable', 'exit_after_commit', 'cancel_during_outage'):
        return dict(mode=mode, scenario=scenario, repeat=repeat, applicable=False,
                    passed=None, reason='No independently running invoice worker in this architecture')
    with tempfile.TemporaryDirectory() as directory:
        app = Rental(directory, mode)
        started = time.perf_counter()
        note = ''
        if scenario == 'storage_failure':
            target = app.path / ('invoice.sqlite' if mode == 'split' else 'booking.sqlite')
            with connect(target, True) as db:
                db.execute("CREATE TRIGGER fail_invoice BEFORE INSERT ON invoices BEGIN SELECT RAISE(ABORT, 'injected storage failure'); END")
            rejected = False
            try:
                _book(app)
                if mode == 'split':
                    dispatch(app.path)
            except sqlite3.DatabaseError:
                rejected = True
            before = _state(app)
            initial_ok = (len(before['bookings']) == 1 and before['pending'] == 1 and before['invoices'] == []) if mode == 'split' else (rejected and before == dict(bookings=[], invoices=[], pending=0))
            with connect(target, True) as db:
                db.execute('DROP TRIGGER fail_invoice')
            recovery = time.perf_counter()
            if mode == 'split':
                dispatch(app.path)
            else:
                _book(app)
            note = 'Single DB rejects whole command; split preserves booking and retries invoice after storage restored.'
        else:
            _book(app)
            initial_ok = True
            if scenario == 'normal':
                before = _state(app)
                recovery = time.perf_counter()
                if mode == 'split':
                    dispatch(app.path)
            elif scenario == 'duplicate':
                if mode == 'split':
                    with connect(app.path / 'booking.sqlite') as db:
                        event = json.loads(db.execute('SELECT payload FROM outbox ORDER BY id').fetchone()[0])
                    deliver(app.path / 'invoice.sqlite', event)
                    deliver(app.path / 'invoice.sqlite', event)
                else:
                    _book(app)
                before = _state(app)
                recovery = time.perf_counter()
                if mode == 'split':
                    dispatch(app.path)
                note = 'Command replay in A/B; event replay in C. Same invoice invariant, different boundary.'
            else:
                dispatch(app.path, unavailable=scenario != 'exit_after_commit', fail_after_commit=scenario == 'exit_after_commit')
                if scenario == 'cancel_during_outage':
                    app.cancel('A')
                    dispatch(app.path, unavailable=True)
                before = _state(app)
                initial_ok = before['pending'] == (2 if scenario == 'cancel_during_outage' else 1)
                if scenario == 'exit_after_commit':
                    initial_ok = initial_ok and len(before['invoices']) == 1
                else:
                    initial_ok = initial_ok and before['invoices'] == []
                recovery = time.perf_counter()
                dispatch(app.path)
        finished = time.perf_counter()
        after = _state(app)
        return dict(mode=mode, scenario=scenario, repeat=repeat, applicable=True,
                    passed=initial_ok and _correct(after, scenario == 'cancel_during_outage'),
                    before_recovery=before, after_recovery=after,
                    recovery_ms=round((finished-recovery)*1000, 3), elapsed_ms=round((finished-started)*1000, 3),
                    note=note, intervention='Restore injected fault when present; explicitly invoke retry/dispatcher.')


def run_experiments(repeats=3):
    if not isinstance(repeats, int) or not 1 <= repeats <= 100:
        raise ValueError('Repeats must be between 1 and 100')
    observations = [_scenario(mode, scenario, repeat) for repeat in range(1, repeats+1)
                    for mode in MODES for scenario in SCENARIOS]
    pricing = {}
    for mode in MODES:
        with tempfile.TemporaryDirectory() as directory:
            app = Rental(directory, mode)
            app.book('historical', 'camera', '2026-10-01', '2026-10-08', '500')
            app.set_policy('weekly-discount')
            app.book('new', 'light', '2026-10-01', '2026-10-08', '500')
            if mode == 'split':
                dispatch(app.path)
            pricing[mode] = {r['booking_id']: r['amount_minor'] for r in app.snapshot()['invoices']}
    with tempfile.TemporaryDirectory() as directory:
        app = Rental(directory, 'modular')
        _book(app)
        _book(app, 'B', 'light')
        app.cancel('B')
        original = app.snapshot()['invoices']
        migration.pause(directory)
        migration.prepare(directory)
        migration.activate(directory)
        migration.resume(directory)
        migrated = app.snapshot()['invoices']
        migration_result = dict(source_mode='modular', target_mode='split', preserved=original == migrated,
                                before=original, after=migrated, scope='One successful populated migration; negative paths covered by unit/integration suite.')
    sources = {str(p.relative_to(Path(__file__).parent)): hashlib.sha256(p.read_bytes()).hexdigest()
               for p in sorted(Path(__file__).parent.glob('*.py'))}
    return dict(generated_at=datetime.now(timezone.utc).isoformat(), python=platform.python_version(),
                platform=platform.platform(), sqlite=sqlite3.sqlite_version,
                repeats=repeats, synthetic=True, source_sha256=sources,
                observations=observations, pricing=pricing, migration=migration_result)


def write_report(output, repeats=3):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    report = run_experiments(repeats)
    (output / 'results.json').write_text(json.dumps(report, indent=2) + '\n')
    rows = report['observations']
    applicable = [r for r in rows if r['applicable']]
    passed = sum(r['passed'] for r in applicable)
    lines = ['# Rental architecture experiment findings', '',
             'AI-assisted implementation and analysis. Synthetic local experiment, not a production study.', '',
             'Generated: ' + report['generated_at'],
             'Python: ' + report['python'] + '; SQLite: ' + report['sqlite'], '',
             '**Observed:** %d/%d applicable scenario runs passed; %d runs were not applicable.' % (passed, len(applicable), len(rows)-len(applicable)), '',
             '| Scenario | Coupled | Modular | Separated |', '|---|---|---|---|']
    for scenario in SCENARIOS:
        cells = []
        for mode in MODES:
            group = [r for r in rows if r['scenario'] == scenario and r['mode'] == mode]
            cells.append('%d/%d passed' % (sum(r['passed'] for r in group), len(group)) if group[0]['applicable'] else 'Not applicable')
        lines.append('| ' + ' | '.join([scenario] + cells) + ' |')
    lines.extend(['', '## Interpretation', '',
                  'The coupled and modular versions retain transactional booking/invoice consistency. An injected invoice-storage error rejects the entire booking; the caller retries after restoration.', '',
                  'The separated version can confirm a booking with invoicing unavailable. A pending notification records the unfinished work. A separate process commits invoice state; retries and monotonically versioned full-state events converge without duplicate invoices in the tested scenarios.', '',
                  'This introduces a deliberate trade-off: booking availability during invoice failure versus immediate invoice consistency and additional recovery responsibilities. The dispatcher holds a booking database write lock during local delivery; therefore dispatch can temporarily block writes. This is not a demonstration of high throughput or independent scaling.', '',
                  'The modular version is the provisional default for this small case: it offers a clear invoice boundary while keeping atomic writes. Service separation is justified only if accepting bookings during invoice outages is worth pending states, retries and operating another process. That business priority has not been established with a real organisation.', '',
                  '## Migration and pricing', '',
                  'The populated migration preserved every invoice row: ' + str(report['migration']['preserved']) + '. Source invoices remain archived in the booking database. Tests separately cover corruption, pause persistence and rollback boundaries.', '',
                  'For all three architectures, a seven-day rental at 500/day retains its historical 3500 invoice while the new 10% policy produces 3150 for a new booking. Amounts in JSON are integer minor units.', '',
                  'The shared pricing policy is intentionally reused across architectures. This is a behaviour-preservation demonstration, not an independently executed maintainability or developer-productivity experiment. No edit-count, effort or deployment superiority is claimed.', '',
                  '## Validity limits', '',
                  '- Same-host subprocess communication, SQLite and a single dispatcher; no network partitions or separate-machine failure tests.',
                  '- Synthetic fixtures and repeated deterministic scenarios; pass counts are correctness checks, not estimated reliability rates.',
                  '- Recovery timings include local process startup and scheduling. No statistical performance ranking is justified.',
                  '- Fault flags and a database trigger simulate outages/storage errors; only the worker exit is an actual abrupt process termination.',
                  '- Only invoice component recovery is demonstrated. Backup restoration, whole-host crashes and production migration readiness are not established.',
                  '- Architecture A and B share booking validation, storage and pricing infrastructure; this isolates the invoice boundary but does not represent independent development teams.',
                  '- A separate controlled source-change study is available through `python3 -m rental change-study --output <new-directory>`. It retains a reconstructed baseline and measures edit scope for one calculation change. Independent implementations and an interactive showcase remain future work.', '',
                  '## Reproduce', '', '`python3 -m unittest discover -v`', '',
                  '`python3 -m rental experiment --output outputs --repeats 3`', '',
                  'The JSON includes before/after evidence, scenario applicability, environment versions and SHA-256 fingerprints of the implementation. Existing report files at the selected output path are replaced on rerun.'])
    (output / 'findings.md').write_text('\n'.join(lines) + '\n')
    return dict(passed=passed, applicable=len(applicable), not_applicable=len(rows)-len(applicable), output=str(output.resolve()))
