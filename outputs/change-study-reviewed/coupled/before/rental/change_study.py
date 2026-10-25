"""Controlled source-change study; baseline is reconstructed, not historical."""
import difflib
import hashlib
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

DISCOUNT = "        if policy == 'weekly-discount' and days >= 7:\n            total = (total * 90 + 50) // 100  # exact positive half-up rounding\n"

# Run in fresh interpreters to ensure each stage imports its retained sources.
CHECK = '''import json, sys
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
'''


def run_change_study(output):
    """Keep sources, patches, subprocess transcripts and upgrade databases."""
    import shutil
    source = Path(__file__).parent
    current = {p.name: p.read_text() for p in sorted(source.glob('*.py'))}
    if current['pricing.py'].count(DISCOUNT) != 1:
        raise ValueError('Pricing source changed; review the baseline reconstruction protocol')
    baseline = dict(current)
    baseline['pricing.py'] = baseline['pricing.py'].replace(DISCOUNT, '')
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    report = dict(generated_at=datetime.now(timezone.utc).isoformat(),
                  python=platform.python_version(), platform=platform.platform(),
                  provenance='Controlled reconstructed baseline: remove the two discount lines from current pricing.py. Not historical development or independent implementations.',
                  architectures=[])
    for mode in ('coupled', 'modular', 'split'):
        root = output / mode
        hashes = {}
        for stage, files in (('before', baseline), ('after', current)):
            package = root / stage / 'rental'
            package.mkdir(parents=True)
            for name, content in files.items():
                (package / name).write_text(content)
            (root / stage / 'check_change.py').write_text(CHECK)
            hashes[stage] = {name: hashlib.sha256((package / name).read_bytes()).hexdigest() for name in files}
        patch = list(difflib.unified_diff(baseline['pricing.py'].splitlines(True), current['pricing.py'].splitlines(True), fromfile='before/rental/pricing.py', tofile='after/rental/pricing.py'))
        (root / 'change.diff').write_text(''.join(patch))
        runs = []
        def run(stage, database, action):
            command = [sys.executable, 'check_change.py', str(database), mode, action]
            result = subprocess.run(command, cwd=root / stage, capture_output=True, text=True, timeout=30)
            runs.append(dict(stage=stage, action=action, command=command, cwd=str(root / stage), returncode=result.returncode, stdout=result.stdout, stderr=result.stderr))
            return result
        database = root / 'upgrade-data'
        seed = run('before', database, 'seed')
        # Probe the new requirement on a copy, preserving the original upgrade data.
        probe = root / 'baseline-probe-data'
        if database.exists():
            shutil.copytree(database, probe)
        red = run('before', probe, 'requirement')
        green = run('after', database, 'requirement')
        try:
            red_expected = json.loads(red.stdout) == dict(historical=350000, new=350000, six_days=300000, rounded=35)
        except ValueError:
            red_expected = False
        changed = [name for name in current if hashes['before'][name] != hashes['after'][name]]
        report['architectures'].append(dict(mode=mode, changed_files=changed,
            added_lines=sum(line.startswith('+') and not line.startswith('+++') for line in patch),
            removed_lines=sum(line.startswith('-') and not line.startswith('---') for line in patch),
            source_sha256=hashes, runs=runs,
            passed=seed.returncode == 0 and red.returncode == 1 and red_expected and not red.stderr and green.returncode == 0))
    report['passed'] = all(row['passed'] for row in report['architectures'])
    (output / 'manifest.json').write_text(json.dumps(report, indent=2) + '\n')
    lines = ['# Retained source-change experiment', '', report['provenance'], '',
             '| Architecture | Changed files | Added / removed lines | Upgrade checks |', '|---|---|---|---|']
    for row in report['architectures']:
        lines.append('| %s | %s | %s / %s | %s |' % (row['mode'], ', '.join(row['changed_files']), row['added_lines'], row['removed_lines'], 'Pass' if row['passed'] else 'FAIL'))
    lines.extend(['', 'The baseline passes a historical-booking check, then fails the new discount requirement with the expected undiscounted amounts. The changed source passes that requirement on the preserved database. Checks cover the seven-day threshold, six-day exclusion, half-up rounding, and unchanged historical amounts. In split mode the old invoice is delivered only after upgrade.', '',
                  'All three architectures use the same pricing boundary and need the same two-line addition. This change provides no evidence of a service-separation advantage. No database schema, event format or worker source changes occur in this controlled patch. This measures edit scope for one change, not developer effort, independent deployability or general maintainability.', '',
                  'The baseline already includes the policy-selection interface. This study measures adding the calculation only, not the cost of implementing the whole discount feature. Baseline reconstruction and changed implementation were produced by the same AI-assisted process.', '',
                  'Each directory retains before/after packages, the identical check script, the patch, and both probe and upgrade databases. manifest.json records source hashes and all subprocess commands, output and exit codes. Run the top-level change-study command into a new output directory to reproduce.'])
    if not report['passed']:
        lines = lines[:6 + len(report['architectures'])] + ['',
            'The experiment did not pass. Do not infer upgrade correctness or architectural conclusions from this run. Inspect FAIL rows and manifest.json subprocess transcripts before interpreting the evidence.',
            '', report['provenance']]
    (output / 'report.md').write_text('\n'.join(lines) + '\n')
    return report
