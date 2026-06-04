# Launch L1 Go / No-Go Checklist

Use this checklist before approving Launch Sprint `L1`.

In the current repository phase, Dry Run 0 has been executed and reviewed, so this checklist now supports the post-dry-run `L1` approval decision.

## Go / No-Go Checks

- [ ] Dry Run 0 has been executed and reviewed.
- [ ] Dry Run 0 review recommends `GO to Controlled Pilot L1` or only small accepted follow-up debt.
- [ ] Any minor dry-run follow-ups are either closed or explicitly accepted by the pilot owner.
- [ ] Full recovery and registry reconciliation remain accepted in governance docs.
- [ ] `M-049` and `M-050` are still explicitly out of scope for L1.
- [ ] `M-052..M-055` are still documented as deferred non-runtime slots, not misrepresented as complete runtime modules.
- [ ] Clean `alembic upgrade head` succeeds on a fresh database.
- [ ] Full `pytest` suite succeeds.
- [ ] Operator owners are assigned for active launch deals.
- [ ] Operators know how to query and review `/events?deal_id=...`.
- [ ] Operators know how to build and review `/dashboards/build` for active launch scopes.
- [ ] Operators know how to build and review `/workspace-feed/build` for active launch scopes.
- [ ] Operators know how to build and review `/action-queue/build` when approvals matter.
- [ ] Incident, payment, and claim review cadence is defined.
- [ ] Launch communication does not promise AI autonomy, real-time alerts, or self-serve SaaS behavior.

## Immediate No-Go Conditions

- [ ] No-Go if launch assumes autonomous or unattended operations.
- [ ] No-Go if launch assumes real-time critical notification delivery.
- [ ] No-Go if launch assumes an executive portfolio dashboard is already a finished runtime surface.
- [ ] No-Go if launch assumes prompt/agent runtime exists.
- [ ] No-Go if manual operator review controls are not staffed.

## Final Decision Rule

- If Dry Run 0 is incomplete -> `NO-GO`
- If Dry Run 0 review still has unresolved blockers -> `NO-GO`
- If all Go checks pass, no No-Go condition is true, and the minor follow-up list is accepted -> `GO with restrictions`
- If any No-Go condition is true -> `NO-GO`
