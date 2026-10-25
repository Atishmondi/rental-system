# When Should Invoicing Become a Separate Service?

## Problem Statement

How might a small equipment-rental organisation choose between internal restructuring and service separation while preserving booking and invoicing correctness?

## Recommended Direction

Build and compare three functionally equivalent systems: a coupled application, a modular application and an application with independently running invoicing.

Make migration and recovery the central investigation. Use a controlled transfer of existing invoice records, repeatable failure scenarios and a shared business-rule change to produce evidence for an architecture recommendation. Keeping the modular application is a valid outcome.

The contribution is a transparent, reproducible comparison and an explanation of its limitations. It does not depend on inventing a new architectural pattern.

## Key Assumptions to Validate

- **The comparison is fair.** All versions must pass the same normal-operation checks before failure experiments. Document differences in transaction boundaries and failure exposure.
- **Recovery preserves business meaning.** After recovery, each confirmed booking has exactly one correct invoice; cancelled bookings retain a voided invoice record.
- **The migration preserves existing information.** Compare identifiers, record counts, amounts and statuses before resuming bookings.
- **The changeability experiment reveals meaningful differences.** Record affected components, interfaces, tests and deployment steps. Similar results across versions are legitimate findings.
- **The work demonstrates personal ownership.** The learner must explain the design, modify a rule and diagnose a failure without simply reproducing generated instructions.

## MVP Scope

Use Python, SQL, SQLite and a command-line interface, entirely locally and at zero cost.

Include one-item bookings, overlapping-date rejection, fixed daily pricing, invoicing and cancellation. Compare the three architectures using shared fixtures and expected outcomes.

Test invoicing unavailability, duplicate notifications, interruption after invoice creation, and cancellation during an outage. Include a paused migration with verification and rollback before new writes resume.

Apply the same seven-day rental discount change to each version. Preserve previously issued invoice amounts.

Deliver reproducible experiments, a concise case study and an explainable demonstration.

## Not Doing

- **Production or industry-wide claims:** the system and organisation are simulated.
- **Paid services, cloud infrastructure or actual payments:** unnecessary for the research question and incompatible with the budget.
- **Additional services or a full rental platform:** they expand scope without strengthening the central comparison.
- **A universal architecture score:** correctness, recovery and operational burden involve trade-offs that should remain visible.
- **Claims that service separation improves scalability:** scalability is outside the agreed evaluation.
- **A polished interface before validated results:** the demonstration follows the evidence.

## Remaining Design Details

Before coding, specify date boundaries, cancellation ordering, retry behaviour and the point at which recovery is considered complete. These are implementation decisions to document, not reasons to reopen the project choice.

## Execution Update

The user subsequently chose autonomous Codex implementation with explanations of progress, replacing learner-led implementation. Code and experiments must disclose AI assistance; independent learner competence is not claimed by completion alone.
