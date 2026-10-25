# Rental architecture study design

Approved concept: outputs/invoicing-service-decision-brief.md. User subsequently instructed Codex to implement autonomously and explain progress. No further exercise or approval gates; preserve honest AI-assisted authorship. Existing workspace is a dedicated new non-Git directory, so no existing branch/worktree needs protection.

## Contract
Python 3.9+ standard library only; no paid tools, hosted services, downloads or infrastructure. Half-open ISO date intervals [start,end), end strictly after start. Exact decimal daily rates converted to integer minor units; positive finite amounts with at most two decimal places. One named item per booking. Reject overlaps among confirmed bookings, including concurrent attempts. Booking IDs are idempotency keys: identical repeat returns existing booking, changed payload rejects, cancelled IDs cannot reconfirm. Cancellation is idempotent and frees availability; invoice retained as void. No payment, tax or legal accounting claims.

Architecture A inlines invoice persistence in booking transactions. B calls an invoice module inside the same database transaction. C commits booking state plus a full-state event to an outbox in one transaction; a dispatcher invokes a separate invoice worker process using JSON stdin. Worker owns a separate SQLite DB, never accesses booking DB. Each event carries booking ID, immutable amount, state and monotone version. Worker updates only on newer versions; replay and reversed delivery converge. Acknowledgement follows worker commit. Failures leave events pending; retries are manual dispatcher calls, not an always-running daemon. No network/distributed-host claims.

Invoice pending is permitted only in C before recovery; after drain every confirmed booking has exactly one active invoice and every cancelled booking has one void invoice. Baseline and modular writes remain atomic on failure. Frozen pricing amount is copied into events. Price change experiment enables 10% discount for new bookings of >=7 days using half-up rounding; historical invoices unchanged.

## Migration
Persist write pause in source DB. Seed nonempty, mixed confirmed/cancelled source records. Prepare copies invoices to an empty target DB, keeping source intact. Verify exact invoice rows (IDs, amount, state, version), not only counts/totals. Activate split mode only after verification. Resume re-verifies before accepting writes. Rollback allowed only while paused and before resume; source retained, target retained as evidence. Once resumed, rollback rejected even without new writes. Paused dispatcher cannot deliver. Restart must preserve pause and phase. DB files remain local trusted experiment inputs, not public hostile endpoints.

## Evaluation
Predefine normal scenarios, unavailable worker, duplicate delivery, worker process exit after commit before acknowledgement, and cancellation while unavailable. Run each from clean data repeatedly. Distinguish common invoice-storage failure (atomic rejection in A/B) from process-only failures in C, which are not applicable to A/B. Record scenario applicability, observed state, recovery correctness, pending events and timing context. A passed assertion is not a production reliability estimate. Whole-host failures, concurrent dispatchers and network partitions remain outside scope.

Shared business-rule change is controlled via an explicit pricing policy (standard/weekly-discount). Report it as a policy-change demonstration, not independently measured developer effort or historical refactoring evidence. No fabricated productivity, scalability or admissions claims.

## Deliverables
Three implementations, CLI, shared tests, reproducible experiment runner, JSON observations and Markdown findings, migration demonstration, README and progress ledger. UI deferred until evidence exists. User learns through commentary and runnable examples; no homework required.
