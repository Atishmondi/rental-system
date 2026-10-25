"""One-event invoice worker: stdin JSON, commit, then acknowledge by exit 0."""
import json
import os
import sys
from pathlib import Path
from .storage import connect
from .invoicing import apply_event


def main():
    path = Path(sys.argv[1])
    if not path.is_file():
        raise ValueError('Invoice database unavailable')
    event = json.load(sys.stdin)
    with connect(path, True) as db:
        apply_event(db, event)
    if '--exit-after-commit' in sys.argv[2:]:
        os._exit(75)
    print(json.dumps({'acknowledged': event['booking_id'], 'version': event['version']}))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, KeyError) as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
