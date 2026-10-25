# Rental study progress

Plan: docs/superpowers/plans/2026-10-15-rental-study.md
Execution: inline by Codex, per user's explicit correction. No learner exercises.
Workspace: new dedicated non-Git directory; Git-specific task helper scripts and commits do not apply.
Preflight: app/transport share outbox schema; migration/transport share invoice schema; runner uses public app and migration APIs. Full-state events retain immutable price. No conflicting interfaces.
- Planning complete; implementation pending.

## Implementation evidence
- Task 1: shared contract tests first failed because rental.app did not exist; implementation passed shared contracts for all three architectures.
- Task 2: recovery tests written before worker/transport; 17 tests passed including repeated shared contracts and real process exit after commit.
- Task 3: migration tests first failed for absent migration module; full suite then passed 24 tests. CLI round-trip test failed at absent entrypoint, then passed after implementation.
- Task 4: experiment tests first failed for absent runner; runner/CLI implementation passed full 26-test suite before review.

## Decisions and limitations
- User explicitly replaced learner-led work with autonomous implementation. Brief and design record this; no further exercise/approval gate.
- No Git repository or commits exist, so Git task-helper bookkeeping is replaced by this durable ledger. No worktree was necessary in the new dedicated directory.
- Pricing is shared across architectures to preserve equivalence. The implemented policy toggle is not a measured changeability experiment; that deeper study remains pending. Cost: cannot claim reduced change effort from current evidence.
- Local dispatcher holds the booking write lock during subprocess delivery to serialize migration and delivery. Cost: writes wait during dispatch, so independent throughput is not demonstrated.
- Experiment runner marks worker-specific failures not applicable to A/B, rather than manufacturing direct equivalents. Common storage-error tests show atomic rejection versus pending work.
- Repeated deterministic fixtures are correctness evidence, not reliability probabilities or statistical architecture rankings.
- Review pending.

## Review and final verification
- Independent reviewer reported two material issues before its turn was interrupted by a usage limit. No completed independent-review verdict exists.
- Fixed: exact rate validation previously rounded long fractional-minor-unit input and could raise decimal.Overflow for large exponents. Regression tests first reproduced both failures; integer coefficient/exponent conversion now rejects them without context rounding.
- Fixed: CLI constructed Rental before rollback, blocking recovery when the migrated invoice database was missing. Regression test first reproduced the CLI failure; rollback now restores source ownership before opening application state.
- Additional regression: largest supported one-day minor-unit amount remains exact; overflowing duration rejected.
- Removed repeated inherited contract execution from the Recovery test class. Earlier counts included seven duplicate test executions; final suite has 23 distinct test methods, many with architecture subtests.
- Final verification: `python3 -m unittest discover -v` -> 23 tests passed.
- Final experiment run: `python3 -m rental experiment --output outputs --repeats 3` -> 36/36 applicable runs passed; 18 worker-specific runs explicitly not applicable to single-process architectures.
- Author follow-up inspection: checked event version ordering, atomic booking/outbox writes, migration state persistence, exact copy comparisons and CLI recovery reachability. This does not substitute for a completed independent review.
- Deferred scope: true independent changeability study with retained baseline/change artifacts; interactive showcase; production deployment. These are not claimed complete.
- Known design limits: dispatcher serializes writes while delivering, same-host process transport, trusted local fixtures, manual recovery invocation. No throughput, independent scaling or production reliability claims.

## Completed improvement: retained source-change experiment

Added `change-study` command, retained before/after sources for all three modes, exact patches, source fingerprints, subprocess transcripts, and persisted upgrade/probe databases. Current reviewed evidence: `outputs/change-study-reviewed/report.md` and `manifest.json`; the initial `outputs/change-study` run is retained as earlier evidence.

The reconstructed baseline already has policy selection; only the discount calculation is removed. Each mode passes the historical seed check, fails the new requirement with the expected undiscounted amounts, then passes after the two-line addition. Historical invoices remain unchanged, including pending delivery across a split-mode upgrade. This establishes edit scope for one shared calculation, not independent implementation effort or general maintainability. All modes tie; no service advantage is inferred.

Independent review completed for the new study, CLI, documentation and a scoped inspection of core modules. One important issue found: failure reports could retain success prose. Fixed by emitting a failure-only interpretation when any architecture fails; regression forces after-stage failure and verifies all FAIL rows and absence of success prose. No other critical/important issues reported within review scope; not an exhaustive concurrency or destructive-fault audit.

Final verification: 25 tests pass; recovery experiment 36/36 applicable runs pass with 18 inapplicable; all three source-change experiments pass. Retained snapshot hashes match their manifest and the current implementation. Zero paid services used.
