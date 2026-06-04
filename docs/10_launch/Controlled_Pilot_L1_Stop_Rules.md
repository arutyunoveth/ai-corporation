# Controlled Pilot L1 Stop Rules

## Purpose

These rules define when a pilot deal or the whole pilot wave must pause or stop.

## Immediate Stop Conditions

Stop the active pilot deal immediately if any of the following occurs:

1. a control gate cannot be evaluated from persisted artifacts
2. a critical operator decision would require a false autonomy claim
3. the team is forced to rely on `M-049`, `M-050`, or any unopened deferred runtime capability
4. audit trail continuity becomes unclear for a business-significant step
5. the pilot is pressured into behaving like broad launch

## Pause And Review Conditions

Pause the active pilot deal for explicit reviewer sign-off if:

1. operator visibility becomes too fragmented to make a safe call
2. payment / claim / incident supervision requires ambiguous manual work
3. submission / procedure state is not confidently understandable
4. an approval or outcome would otherwise be inferred rather than documented

## Whole-Wave Stop Conditions

Pause the entire Controlled Pilot L1 wave if:

1. Deal #1 ends in `NO-GO`
2. repeated medium/high-severity issues show that Deal #2 would not add useful evidence
3. README/docs would need false claims to justify continuation
4. the pilot owner cannot accept the manual-control operating model

## Restart Rule

Any stopped or paused pilot step may restart only after:

- the issue is documented
- the owner/reviewer agree on the compensating control or fix
- the restart decision is written into the decision log

## Plan Alignment

- Master Plan matched: yes
- What changed vs plan: stop rules were expanded into explicit operational triggers
- Any drift introduced: `NO`
