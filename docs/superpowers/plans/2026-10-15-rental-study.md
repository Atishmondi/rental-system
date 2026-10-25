# Rental Study Implementation Plan

> For agentic workers: implement inline using executing-plans principles and test-driven development. The user's instruction authorizes implementation without another review gate.

**Goal:** Deliver a runnable local three-architecture comparison with verified recovery and migration.
**Architecture:** A coupled SQLite application, modular in-process invoice persistence, and durable outbox delivery to an independent invoice process.
**Tech Stack:** Python 3.9+ standard library, sqlite3, unittest, subprocess.
**Spec:** docs/superpowers/specs/2026-10-15-rental-study.md

## Global Constraints
Free, local, no external dependencies. Half-open dates and minor-unit integer money. AI-assisted implementation disclosed. No changes to the P2P project. No Git repository exists; use a progress ledger without inventing commit evidence.

## Review Focus
- Simultaneous overlapping bookings must serialize.
- Duplicate command IDs must not silently accept changed payloads.
- Cancellation delivered before confirmation must not resurrect invoices.
- Migrated invoice corruption must prevent activation/resume.
- Invalid/nonfinite prices and malformed dates must leave no partial records.

## Task 1: Contracts and application
Files: tests/test_study.py, rental/storage.py, rental/pricing.py, rental/invoicing.py, rental/app.py.
Interface: Rental(path, mode='coupled'); book(id,item,start,end,rate); cancel(id); snapshot(); set_policy(name).
- [ ] Write shared tests with literal expected prices, dates, overlap, replay, cancellation and historical pricing assertions.
- [ ] Run unittest and observe missing implementation.
- [ ] Implement persistence and coupled/modular transactions, then split outbox.
- [ ] Run shared tests and inspect outcomes.

## Task 2: Process boundary and recovery
Files: rental/worker.py, rental/transport.py; additional tests in tests/test_study.py.
Interfaces: dispatch(path, fail_after_commit=False, unavailable=False), deliver(invoice_path,event,fail_after_commit=False); apply_event(connection,event).
- [ ] Write tests for outage, crash-after-commit, replay, reversed versions and concurrent booking.
- [ ] Observe RED before implementation.
- [ ] Implement worker subprocess with atomic commit, monotone versions and dispatcher acknowledgement.
- [ ] Verify full suite.

## Task 3: Migration and CLI
Files: rental/migration.py, rental/__main__.py; tests/test_migration.py, tests/test_cli.py.
Interfaces: pause(path), prepare(path), activate(path), resume(path), rollback(path).
- [ ] Write failing tests for persistence of pause, mixed-state exact copy, corrupt-copy rejection, pre-resume rollback and post-resume refusal.
- [ ] Implement and run entire suite.
- [ ] Add CLI end-to-end tests, observe RED, implement parser and errors.

## Task 4: Reproducible experiments and explanation
Files: rental/experiment.py, tests/test_experiment.py, README.md, outputs/results.json, outputs/findings.md.
Interface: run_experiments(repeats=3) -> JSON-serializable observations.
- [ ] Write failing tests for expected scenario outcomes and applicability.
- [ ] Implement real runs using fresh temporary databases; include migration and pricing demonstrations.
- [ ] Generate reports, run full tests, review independently and fix material findings.
- [ ] Record verified results and limitations in docs/progress.md.

## Improvement: controlled source-change evidence

Retain a reconstructed standard-price baseline and current changed sources for each architecture. Execute identical acceptance scripts in fresh processes: historical booking passes, new requirement fails for the expected undiscounted amounts, upgraded code passes on the preserved database. Include pending historical delivery in split mode, threshold exclusion and rounding checks. Retain source hashes, patch, transcripts and databases; refuse existing output destinations. Report edit scope without inferring effort or service superiority. The policy selector already exists in the baseline; this is a calculation change only. Verify the full suite and obtain independent review.
