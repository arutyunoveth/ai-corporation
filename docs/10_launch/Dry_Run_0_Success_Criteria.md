# Dry Run 0 Success Criteria

## Purpose

Define what counts as success, blocker, and acceptable pre-pilot debt for `Dry Run 0`.

## Dry Run 0 Is Successful If

All of the following are true:

1. operators can follow the runbook without major ambiguity
2. all required control gates can be exercised manually
3. major lifecycle stages are traceable through persisted artifacts
4. helper visibility layers are sufficient for operator supervision
5. no hidden dependency on reserved AI/runtime slots is discovered
6. no one needs to describe the system as autonomous in order to justify the run

## Dry Run 0 Is A Blocker If

Any of the following occurs:

1. a critical lifecycle stage cannot be supervised safely by human operators
2. a control gate cannot be evaluated from existing persisted artifacts
3. important blocking signals cannot be surfaced without unrealistic manual effort
4. the documentation contradicts actual runtime behavior
5. the team is forced to rely on a reserved or deferred runtime capability

## Acceptable Pre-Pilot Debt

The following can remain acceptable after Dry Run 0 if explicitly acknowledged:

- minor operator friction with helper queries
- missing polish in docs or worksheet formatting
- medium/low-severity discoverability pain that still has a clear compensating control
- lack of real-time notifications, as long as the manual review cadence is workable

## Recommended Post-Run Decision Logic

- `GO to Controlled Pilot L1`
  - no blockers
  - no unresolved high-severity risk to operator control
  - dry-run documentation and runtime behavior are aligned

- `GO only after short blocker-fix step`
  - one or more blockers exist
  - blockers are small, scoped, and clearly fixable

- `NO-GO for Controlled Pilot L1`
  - blockers are structural
  - operator control remains unsafe
  - documentation and runtime are materially misaligned
