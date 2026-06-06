# Limited Runtime Implementation Gate — Master Plan

## Назначение
Этот файл — locked execution plan для **финального архитектурного прогона перед MVP runtime**.

Его цель:
- закрыть design-only фазу;
- формально открыть **ограниченный implementation gate**;
- зафиксировать самый узкий допустимый MVP runtime slice;
- не допустить скрытого scope expansion;
- после этого перейти уже к реальной разработке MVP.

## Статус перед входом в фазу
На входе уже выполнены:
- recovery phase;
- governance reconciliation;
- launch readiness audit;
- Launch Sprint L1 package;
- pre-L1 ops visibility helper;
- repository sync / launch integrity fix;
- Dry Run 0 execution and review;
- Controlled Pilot L1 block completed;
- Broader Internal Usage block completed;
- Broader Internal Steady-State Usage block completed;
- Internal Steady-State Optimization block completed;
- Deferred Runtime Planning block completed;
- Limited Runtime Design block completed.

Limited Runtime Design decision:
**Open limited runtime implementation phase**
but
**only with explicit boundaries and without broad runtime claims**

## Scope этой фазы
Это **implementation gate / MVP slice definition phase**, а не broad implementation phase.

### Разрешено
- final implementation boundary docs
- MVP slice selection
- implementation prerequisites
- implementation safety rules
- phased implementation roadmap
- explicit go/no-go decision for first runtime slice
- governance docs
- decision docs

### Явно запрещено
- broad runtime implementation
- opening all deferred slots at once
- self-serve SaaS claims
- autonomous claims
- AI-native claims
- creation of new canonical IDs
- hidden expansion beyond approved MVP slice

## Locked phase structure
Фаза состоит из 4 спринтов:

1. **G1-S1 — Implementation Gate Scope & Safety Lock**
2. **G1-S2 — MVP Runtime Slice Definition**
3. **G1-S3 — Implementation Readiness & Delivery Plan**
4. **G1-S4 — Gate Review / MVP Go-NoGo Decision**

Нельзя перескакивать этапы без явного review result предыдущего этапа.

# Phase-wide control rules

## Rule 1. Source of truth
Source of truth:
- locked registry `M-001..M-055`
- governance docs
- launch docs
- recovery docs
- steady-state docs
- optimization docs
- deferred runtime planning docs
- limited runtime design docs
- этот master plan

## Rule 2. Anti-drift
Каждый sprint result обязан:
1. явно ссылаться на соответствующий sprint-файл этой фазы;
2. в конце содержать section:
   - `Plan alignment`
   - `What changed vs plan`
   - `Any drift introduced: yes/no`
3. если есть drift — он не реализуется, а фиксируется как proposal для отдельного review.

## Rule 3. No hidden implementation expansion
Во время этой фазы нельзя:
- незаметно открыть больше одного MVP slice;
- выдать planning docs за implemented runtime;
- встроить AI/runtime claims в README/docs;
- silently convert deferred/platform slots into full runtime.

## Rule 4. MVP discipline
Эта фаза должна закончиться не абстрактным design-output, а:
- explicit first MVP slice,
- explicit in-scope items,
- explicit out-of-scope items,
- explicit readiness criteria,
- explicit go/no-go decision.

## Rule 5. Exit discipline
Переход к следующему этапу допускается только после final gate decision.

# Phase flow

## G1-S1 — Implementation Gate Scope & Safety Lock
Цель:
- зафиксировать final safety lock перед runtime implementation;
- описать, что можно делать, а что запрещено в первом MVP slice.

Выход:
- repository ready for MVP runtime slice definition

## G1-S2 — MVP Runtime Slice Definition
Цель:
- выбрать самый узкий реалистичный runtime slice;
- определить in-scope / out-of-scope;
- описать first implementation target.

Выход:
- first MVP runtime slice formally defined

## G1-S3 — Implementation Readiness & Delivery Plan
Цель:
- подготовить delivery-level readiness:
  - prerequisites
  - sequencing
  - acceptance criteria
  - rollback boundaries
  - test strategy

Выход:
- MVP implementation package ready for execution

## G1-S4 — Gate Review / MVP Go-NoGo Decision
Цель:
- собрать итоговый gate review;
- принять решение:
  - GO to MVP implementation
  - GO with restrictions
  - mini-gap closure required
  - NO-GO

# Deliverables by sprint

## G1-S1
- implementation gate charter
- implementation safety lock
- blocked areas list
- gate decision log template

## G1-S2
- MVP runtime slice definition
- in-scope / out-of-scope matrix
- first implementation target note
- deferred remainder note

## G1-S3
- implementation readiness checklist
- delivery sequence
- acceptance criteria
- rollback boundaries
- test strategy

## G1-S4
- final gate review
- MVP go/no-go decision
- MVP phase roadmap

# Phase completion criteria
Фаза считается завершенной только если:
1. first MVP slice explicitly selected;
2. scope boundaries explicitly fixed;
3. implementation readiness documented;
4. final gate decision exists;
5. README/docs updated without false runtime claims.

# Next step after phase
Следующий шаг после этой фазы:
**MVP Runtime Implementation — Phase 1**
Но только если final gate decision explicitly says GO.
