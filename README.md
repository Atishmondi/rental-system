# Rental architecture decision study

A free, local experiment comparing a coupled rental application, a modular application and independently running invoicing. The question is whether allowing bookings to continue during invoice failures is worth delayed invoice consistency and extra recovery machinery.

**Status:** working command-line research prototype. Synthetic fixtures; AI-assisted implementation. This repository does not establish independent student proficiency, enterprise scalability or admissions outcomes.

## Start here

- [Observed findings](outputs/findings.md): results and limitations.
- [Source-change study](outputs/change-study-reviewed/report.md): retained code, patches and upgrade checks.
- [Raw evidence](outputs/results.json): before/after states, environment and source fingerprints.
- [Approved brief](outputs/invoicing-service-decision-brief.md).
- [Detailed design](docs/superpowers/specs/2026-10-15-rental-study.md).
- [Progress and decisions](docs/progress.md).

Requires Python 3.9 or newer with SQLite support. No packages, subscriptions, Docker, cloud accounts or paid APIs are required. Run commands from this directory.

```sh
python3 -m unittest discover -v
python3 -m rental experiment --output outputs --repeats 3
python3 -m rental change-study --output outputs/change-study-new
```

The change study requires a new output directory and retains its source versions and databases. Its baseline is reconstructed by removing the discount calculation; the policy selector already exists. It measures one calculation change, not whole-feature effort.

Recovery experiments use temporary databases, then save JSON observations and a Markdown report. Rerunning replaces those two report files only. Pass counts are deterministic correctness checks, not estimated reliability rates. Timing varies by machine and includes process startup.

## See the separated version recover

Choose a new local directory; init refuses to overwrite an existing experiment.

```sh
python3 -m rental --path runs/example init --mode split
python3 -m rental --path runs/example book A camera 2026-10-20 2026-10-23 500
python3 -m rental --path runs/example status
python3 -m rental --path runs/example dispatch --exit-after-commit
python3 -m rental --path runs/example status
python3 -m rental --path runs/example dispatch
python3 -m rental --path runs/example status
```

The injected worker exit returns a nonzero status deliberately. After the exit, one invoice exists while its notification is still pending. Retrying acknowledges the notification without creating another invoice. Use `--unavailable` instead to inject an outage before delivery. Real worker processes execute locally; there is no HTTP server or external message broker.

## Run the migration

```sh
python3 -m rental --path runs/migration init --mode modular
python3 -m rental --path runs/migration book A camera 2026-10-20 2026-10-23 500
python3 -m rental --path runs/migration pause
python3 -m rental --path runs/migration prepare
python3 -m rental --path runs/migration activate
python3 -m rental --path runs/migration resume
python3 -m rental --path runs/migration status
```

Before `resume`, `rollback` restores the previous architecture and reopens writes. After resume it is prohibited. Both activation and resume compare exact invoice rows with the preserved source. Corruption keeps writes paused. Existing target files are never overwritten: failed or rolled-back copies must be manually archived before another preparation attempt. Source invoice rows are retained but become inactive once split mode is active.

## Business rules

Dates use `[start, return)`; 20–23 October is three days, and an adjacent booking can start on the 23rd. A confirmed booking reserves one item. Overlaps are rejected, including simultaneous requests. An identical command ID is safe to retry; changing its payload is an error. Cancelled IDs cannot reconfirm. Cancellation frees the item and voids (never deletes) its invoice.

Prices are exact values in one unspecified currency, stored as integer minor units: 500/day for three days is 150000. Rates must be positive and have no fractional minor units. No exchange rates, payments, tax or legal invoice compliance are modelled.

`policy weekly-discount` enables a 10% discount for new rentals lasting at least seven days. Round half-up to the nearest minor unit. Historical bookings retain their quoted amounts even when their invoices are delivered later. This policy demonstration does not measure independent refactoring effort.

## Implementation map

| Component | Responsibility |
|---|---|
| `rental/app.py` | Booking commands; inline invoice SQL in A, module calls in B, outbox writes in C |
| `rental/invoicing.py` | Version-aware invoice state updates for B and C |
| `rental/worker.py` | Separate invoice process, owns its database |
| `rental/transport.py` | Local delivery, retry and acknowledgement |
| `rental/migration.py` | Durable pause, exact copy verification, cutover, resume and rollback |
| `rental/experiment.py` | Repeated fresh-fixture scenarios and evidence reports |

The worker receives only a JSON event and its invoice DB path. It never reads the booking database. The dispatcher reads the outbox and serializes delivery with booking writes; this simplicity imposes contention and is explicitly not a throughput claim. Events contain complete invoice state and a monotone per-booking version, so old confirmations cannot resurrect cancelled invoices.

## Research limits and next work

This is a simulated legacy system with shared supporting code, not a migrated real-world organisation. No conclusions about real companies' costs, team productivity, network partitions or production uptime follow. The modular version is a credible default, not a deliberately weakened competitor.

The implemented core covers correctness, component recovery and a paused migration. The controlled source-change study now retains baseline/changed source, patches, subprocess transcripts and upgrade databases. All three variants require the same two-line pricing addition; there is no separation advantage for this change. The baseline is reconstructed, not historical. Independent implementations, additional change types and an interactive showcase remain future extensions. Independent learning/defence must be assessed separately from generated code quality.
