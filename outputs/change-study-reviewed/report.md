# Retained source-change experiment

Controlled reconstructed baseline: remove the two discount lines from current pricing.py. Not historical development or independent implementations.

| Architecture | Changed files | Added / removed lines | Upgrade checks |
|---|---|---|---|
| coupled | pricing.py | 2 / 0 | Pass |
| modular | pricing.py | 2 / 0 | Pass |
| split | pricing.py | 2 / 0 | Pass |

The baseline passes a historical-booking check, then fails the new discount requirement with the expected undiscounted amounts. The changed source passes that requirement on the preserved database. Checks cover the seven-day threshold, six-day exclusion, half-up rounding, and unchanged historical amounts. In split mode the old invoice is delivered only after upgrade.

All three architectures use the same pricing boundary and need the same two-line addition. This change provides no evidence of a service-separation advantage. No database schema, event format or worker source changes occur in this controlled patch. This measures edit scope for one change, not developer effort, independent deployability or general maintainability.

The baseline already includes the policy-selection interface. This study measures adding the calculation only, not the cost of implementing the whole discount feature. Baseline reconstruction and changed implementation were produced by the same AI-assisted process.

Each directory retains before/after packages, the identical check script, the patch, and both probe and upgrade databases. manifest.json records source hashes and all subprocess commands, output and exit codes. Run the top-level change-study command into a new output directory to reproduce.
