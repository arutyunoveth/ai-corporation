# Limited Runtime Design — Sprint D1-S2: M-049/M-050 Limited Runtime Design

## Назначение
Подготовка design package для M-049 и M-050.

## Цель
Спроектировать limited runtime design для:
- M-049 Agent Registry
- M-050 Prompt / Schema Library

без открытия runtime implementation.

## Вход
- D1-S1 completed
- design scope approved
- safety rules documented

## Что должно быть сделано
1. Описать target design role of M-049 and M-050
2. Описать:
   - runtime-facing contracts
   - internal interfaces
   - dependency requirements
   - governance controls
   - activation sequencing
   - safety boundaries
3. Сформировать phased design sketch:
   - design-complete
   - limited internal implementation candidate
   - later broader runtime
4. Заполнить design decision log

## Обязательные deliverables
- `M049_M050_Limited_Runtime_Design.md`
- `M049_M050_Contracts_and_Interfaces_Draft.md`
- `M049_M050_Activation_Sequencing.md`
- `M049_M050_Safety_and_Risk_Note.md`

## Ограничения
- без runtime implementation
- без новых endpoints/models for M-049/M-050
- без AI/native claims
- без implicit opening of reserved slots

## Acceptance criteria
1. Limited runtime design exists
2. Contracts/interfaces draft exists
3. Activation sequencing exists
4. Safety/risk note exists
5. No false runtime claim introduced

## Explicit exit wording
`M-049/M-050 limited runtime design documented`

## Plan alignment
Этот спринт обязан соответствовать `Limited_Runtime_Design_Master_Plan.md` section `D1-S2`.
Any drift introduced: NO
