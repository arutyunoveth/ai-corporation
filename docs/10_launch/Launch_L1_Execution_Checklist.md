# Launch L1 Execution Checklist

## Pre-Launch Checks

- [ ] Recovery and reconciliation docs are accepted as current source of truth.
- [ ] Repository sync / integrity report is reviewed.
- [ ] Dry Run 0 entry criteria are reviewed.
- [ ] Dry Run 0 scenario package is reviewed.
- [ ] [Launch_Readiness_Gap_Audit.md](/Users/master/Documents/AI-Corporation/docs/10_launch/Launch_Readiness_Gap_Audit.md) is reviewed.
- [ ] [Launch_L1_Restrictions.md](/Users/master/Documents/AI-Corporation/docs/10_launch/Launch_L1_Restrictions.md) is reviewed.
- [ ] Operator owners are assigned for each pilot deal.
- [ ] Reserved modules `M-049` and `M-050` remain closed.
- [ ] No launch communication describes the system as autonomous, unattended, or self-serve.

## Runtime Verification Checks

- [ ] `GET /health` responds successfully.
- [ ] full migration chain applies on a clean database.
- [ ] full pytest suite is green.
- [ ] event log query works for active deals.
- [ ] dashboard snapshot build works for active deal scope.
- [ ] workspace feed build works for active deal scope.
- [ ] action queue build works where approvals matter.

## Pilot Deal Readiness Checks

For each pilot deal:

- [ ] canonical `deal_id` exists
- [ ] intake / normalization artifacts exist
- [ ] screening result reviewed manually
- [ ] requirement extraction / compliance outputs reviewed manually
- [ ] supplier shortlist / comparison reviewed manually
- [ ] finance / risk / approval artifacts reviewed manually
- [ ] bid completeness reviewed manually
- [ ] procedure outcome review owner assigned
- [ ] execution / logistics / acceptance / payment review owner assigned

## Documentation Checks

- [ ] operator runbook exists and is shared
- [ ] control gates document exists and is shared
- [ ] pilot playbook exists and is shared
- [ ] deferred module risk assessment exists and is shared
- [ ] dry-run execution log template exists and is shared
- [ ] dry-run review template exists and is shared
- [ ] dry-run success criteria exist and are shared

## During-Run Checks

- [ ] review `/events?deal_id=...` at every critical phase transition
- [ ] rebuild dashboard snapshot when major state changes occur
- [ ] rebuild workspace feed before operational handoffs
- [ ] review incident, payment, and claim records explicitly
- [ ] record human decisions rather than imply them

## Post-Run Review Checks

- [ ] confirm closure report was built
- [ ] confirm postmortem was built
- [ ] confirm supplier rating update was built
- [ ] confirm knowledge asset was built
- [ ] capture launch pain points and operator friction
- [ ] decide whether next step is another pilot, mini-gap closure, or later phase planning

## Current Integrity Note

Dry Run 0 has already been executed as a controlled rehearsal under the existing `L1` restrictions.

Before any real pilot run, the repository must satisfy the Dry Run 0 review outcome and close or consciously accept the minor follow-up list.
