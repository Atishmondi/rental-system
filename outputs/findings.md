# Rental architecture experiment findings

AI-assisted implementation and analysis. Synthetic local experiment, not a production study.

Generated: 2026-10-15T11:58:13.425899+00:00
Python: 3.9.6; SQLite: 3.51.0

**Observed:** 36/36 applicable scenario runs passed; 18 runs were not applicable.

| Scenario | Coupled | Modular | Separated |
|---|---|---|---|
| normal | 3/3 passed | 3/3 passed | 3/3 passed |
| storage_failure | 3/3 passed | 3/3 passed | 3/3 passed |
| worker_unavailable | Not applicable | Not applicable | 3/3 passed |
| duplicate | 3/3 passed | 3/3 passed | 3/3 passed |
| exit_after_commit | Not applicable | Not applicable | 3/3 passed |
| cancel_during_outage | Not applicable | Not applicable | 3/3 passed |

## Interpretation

The coupled and modular versions retain transactional booking/invoice consistency. An injected invoice-storage error rejects the entire booking; the caller retries after restoration.

The separated version can confirm a booking with invoicing unavailable. A pending notification records the unfinished work. A separate process commits invoice state; retries and monotonically versioned full-state events converge without duplicate invoices in the tested scenarios.

This introduces a deliberate trade-off: booking availability during invoice failure versus immediate invoice consistency and additional recovery responsibilities. The dispatcher holds a booking database write lock during local delivery; therefore dispatch can temporarily block writes. This is not a demonstration of high throughput or independent scaling.

The modular version is the provisional default for this small case: it offers a clear invoice boundary while keeping atomic writes. Service separation is justified only if accepting bookings during invoice outages is worth pending states, retries and operating another process. That business priority has not been established with a real organisation.

## Migration and pricing

The populated migration preserved every invoice row: True. Source invoices remain archived in the booking database. Tests separately cover corruption, pause persistence and rollback boundaries.

For all three architectures, a seven-day rental at 500/day retains its historical 3500 invoice while the new 10% policy produces 3150 for a new booking. Amounts in JSON are integer minor units.

The shared pricing policy is intentionally reused across architectures. This is a behaviour-preservation demonstration, not an independently executed maintainability or developer-productivity experiment. No edit-count, effort or deployment superiority is claimed.

## Validity limits

- Same-host subprocess communication, SQLite and a single dispatcher; no network partitions or separate-machine failure tests.
- Synthetic fixtures and repeated deterministic scenarios; pass counts are correctness checks, not estimated reliability rates.
- Recovery timings include local process startup and scheduling. No statistical performance ranking is justified.
- Fault flags and a database trigger simulate outages/storage errors; only the worker exit is an actual abrupt process termination.
- Only invoice component recovery is demonstrated. Backup restoration, whole-host crashes and production migration readiness are not established.
- Architecture A and B share booking validation, storage and pricing infrastructure; this isolates the invoice boundary but does not represent independent development teams.
- A separate controlled source-change study is available through `python3 -m rental change-study --output <new-directory>`. It retains a reconstructed baseline and measures edit scope for one calculation change. Independent implementations and an interactive showcase remain future work.

## Reproduce

`python3 -m unittest discover -v`

`python3 -m rental experiment --output outputs --repeats 3`

The JSON includes before/after evidence, scenario applicability, environment versions and SHA-256 fingerprints of the implementation. Existing report files at the selected output path are replaced on rerun.
