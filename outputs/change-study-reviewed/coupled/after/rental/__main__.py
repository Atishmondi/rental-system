"""Command-line interface for local architecture experiments."""
import argparse
import json
import sqlite3
import sys
from pathlib import Path
from .app import Rental
from .transport import dispatch
from . import migration


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--path', default='runs/demo', help='Local experiment directory')
    sub = parser.add_subparsers(dest='command', required=True)
    init = sub.add_parser('init')
    init.add_argument('--mode', choices=['coupled', 'modular', 'split'], default='coupled')
    book = sub.add_parser('book')
    for name in ('booking_id', 'item', 'start', 'end', 'rate'):
        book.add_argument(name)
    cancel = sub.add_parser('cancel')
    cancel.add_argument('booking_id')
    sub.add_parser('status')
    policy = sub.add_parser('policy')
    policy.add_argument('name', choices=['standard', 'weekly-discount'])
    send = sub.add_parser('dispatch')
    send.add_argument('--unavailable', action='store_true', help='Inject unavailable worker')
    send.add_argument('--exit-after-commit', action='store_true', help='Inject actual worker exit before acknowledgement')
    for command in ('pause', 'prepare', 'activate', 'resume', 'rollback'):
        sub.add_parser(command)
    experiment = sub.add_parser('experiment')
    experiment.add_argument('--repeats', type=int, default=3)
    experiment.add_argument('--output', default='outputs')
    change = sub.add_parser('change-study')
    change.add_argument('--output', default='outputs/change-study')
    args = parser.parse_args()
    if args.command == 'change-study':
        from .change_study import run_change_study
        result = run_change_study(args.output)
        print(json.dumps({'passed': result['passed'], 'output': str(Path(args.output).resolve())}, indent=2))
        return 0 if result['passed'] else 1
    if args.command == 'experiment':
        from .experiment import write_report
        result = write_report(args.output, args.repeats)
        print(json.dumps(result, indent=2))
        return 0 if result['passed'] == result['applicable'] else 1
    path = Path(args.path)
    if args.command != 'init' and not (path / 'booking.sqlite').is_file():
        raise ValueError('Experiment does not exist; run init first')
    if args.command == 'init' and (path / 'booking.sqlite').exists():
        raise ValueError('Experiment already exists; use status or choose another path')
    # Recovery must be reachable even when the destination database is missing.
    # The migration layer validates phase and restores source ownership first.
    if args.command == 'rollback':
        migration.rollback(path)
        print(json.dumps(Rental(path).snapshot(), indent=2))
        return 0
    app = Rental(path, getattr(args, 'mode', 'coupled'))
    result = None
    if args.command == 'book':
        result = app.book(args.booking_id, args.item, args.start, args.end, args.rate)
    elif args.command == 'cancel':
        app.cancel(args.booking_id)
    elif args.command == 'policy':
        app.set_policy(args.name)
    elif args.command == 'dispatch':
        result = dispatch(path, args.exit_after_commit, args.unavailable)
    elif args.command in ('pause', 'prepare', 'activate', 'resume', 'rollback'):
        getattr(migration, args.command)(path)
    print(json.dumps(result if result is not None else app.snapshot(), indent=2))
    return 1 if args.command == 'dispatch' and result['failures'] else 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (ValueError, sqlite3.Error, OSError) as exc:
        print('Error: ' + str(exc), file=sys.stderr)
        sys.exit(1)
