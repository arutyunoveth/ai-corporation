# Limited Runtime Design — Master Plan

## Назначение
Этот файл — locked execution plan для фазы **Limited Runtime Design**.

Его цель:
- открыть не implementation, а строго ограниченную **runtime design phase**;
- перевести planning-решение в формальный design package;
- определить architecture boundaries, safety rules, phased contracts и implementation prerequisites;
- не допустить скрытого открытия runtime и не уйти в drift.

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
- Deferred Runtime Planning block completed.

Deferred Runtime Planning decision:
**Open limited runtime design phase**
without
**opening runtime implementation yet**

## Scope этой фазы
Это **design / architecture / governance / readiness phase**, а не runtime implementation.

### Разрешено
- runtime design docs
- design-level schemas/contracts
- dependency contracts
- control boundary design
- activation sequencing
- rollout rules
- safety rules
- phase roadmap
- governance tests

### Явно запрещено
- runtime implementation of M-049/M-050
- activation of M-052..M-055 as working runtime
- AI-native claims
- autonomous claims
- self-serve SaaS claims
- creation of new canonical IDs
- fake production/runtime endpoints/models for deferred slots
- hidden implementation under the label of design

## Locked phase structure
Фаза состоит из 4 спринтов:

1. **D1-S1 — Runtime Design Scope & Safety Rules**
2. **D1-S2 — M-049/M-050 Limited Runtime Design**
3. **D1-S3 — M-052..M-055 Supporting Runtime Design**
4. **D1-S4 — Runtime Design Review / Implementation Gate Decision**

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
- этот master plan

## Rule 2. Anti-drift
Каждый sprint result обязан:
1. явно ссылаться на соответствующий sprint-файл этой фазы;
2. в конце содержать section:
   - `Plan alignment`
   - `What changed vs plan`
   - `Any drift introduced: yes/no`
3. если есть drift — он не реализуется, а фиксируется как proposal для отдельного review.

## Rule 3. No hidden runtime opening
Во время этой фазы нельзя:
- незаметно открыть M-049/M-050;
- превратить design docs в implementation claims;
- выдать support/runtime design за full runtime completion;
- встроить AI/runtime claims в README/docs;
- silently convert deferred/platform slots into active runtime.

## Rule 4. Design discipline
Каждый design sprint должен иметь:
- owner
- reviewer
- explicit scope
- explicit non-goals
- explicit outputs
- explicit proceed/pause recommendation

## Rule 5. Exit discipline
Переход к следующему спринту допускается только после review предыдущего.

# Phase flow

## D1-S1 — Runtime Design Scope & Safety Rules
Цель:
- формально описать границы design-phase;
- зафиксировать safety rules, non-goals, blocked areas и implementation prerequisites.

Выход:
- repository ready for limited runtime design work

## D1-S2 — M-049/M-050 Limited Runtime Design
Цель:
- подготовить design package для `M-049 Agent Registry` и `M-050 Prompt / Schema Library`;
- без runtime implementation;
- с explicit design contracts, activation sequencing и safety boundaries.

Выход:
- M-049/M-050 limited runtime design documented

## D1-S3 — M-052..M-055 Supporting Runtime Design
Цель:
- подготовить design package для supporting runtime layers:
  - `M-052 Notification Layer`
  - `M-053 Red Flag Registry`
  - `M-054 Master Dashboard`
  - `M-055 SaaS Productization Tracker`
- не как immediate implementation, а как supporting design boundary work.

Выход:
- M-052..M-055 supporting runtime design documented

## D1-S4 — Runtime Design Review / Implementation Gate Decision
Цель:
- собрать финальный review design phase;
- решить, можно ли открывать отдельную limited runtime implementation phase.

# Deliverables by sprint

## D1-S1
- runtime design charter
- design constraints register
- safety rules
- non-goals
- implementation prerequisites
- decision log template

## D1-S2
- M-049/M-050 design package
- contracts and interfaces draft
- activation sequencing note
- safety/risk note

## D1-S3
- M-052..M-055 supporting design package
- dependency matrix
- coordination model
- implementation gate conditions

## D1-S4
- phase summary
- consolidated risks
- implementation gate recommendation
- next-phase roadmap

# Phase completion criteria
Фаза считается завершенной только если:
1. подготовлены explicit design packages for all deferred slots in scope;
2. есть consolidated design decision;
3. README/docs updated without false runtime claims;
4. reserved/deferred modules remain honestly marked where required;
5. final implementation-gate roadmap exists.

# Next step after phase
Следующий шаг после этой фазы определяется только финальным decision document.
До этого нельзя:
- открывать runtime implementation by implication;
- объявлять runtime readiness as achieved;
- превращать design into implementation silently.
