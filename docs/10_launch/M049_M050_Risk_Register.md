# M049 M050 Risk Register

## Key Risks

1. **Premature runtime opening**
   - risk: planning docs may be misread as runtime approval
   - control: keep explicit `RESERVED` posture in README and governance docs

2. **Hidden AI/runtime claims**
   - risk: architecture language may drift into implementation language
   - control: planning-only wording and no endpoint/model/runtime changes

3. **Governance without lifecycle controls**
   - risk: later runtime work could start before approval/versioning rules are explicit
   - control: future phase must define lifecycle and approval states first

4. **Prompt/schema sprawl**
   - risk: `M-050` could become an uncontrolled asset dump
   - control: future activation must include strict approval/version discipline

5. **Agent registry ambiguity**
   - risk: `M-049` could be treated as a vague concept instead of a governed registry
   - control: future activation must define concrete allowed entity types and states

## Risk Summary

Current state is safe only while runtime remains deferred.

## Plan Alignment

- Master Plan matched: yes
- What changed vs plan: risk register was formalized as a repo-local planning artifact
- Any drift introduced: `NO`
