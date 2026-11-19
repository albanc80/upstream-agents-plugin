---
name: well-construction
description: Casing, cementing and wireline evaluation — design factors for burst, collapse and tension, drag against model, cement placement and channeling, job pressure against design, and bond evaluation from CBL. Use for string design checks, casing wear or drag anomalies, cement job problems, lost returns during cementing, or interpreting a bond log.
---

# Well Construction

Design factors, job execution, and what the log actually proves. The three fail in different
ways and the fixes are not interchangeable.

## Casing design

| Check | Minimum | Advisory at |
|---|---|---|
| Burst | 1.10 | 1.20 |
| Collapse | 1.00 | 1.10 |
| Tension | 1.30 | — |

Compute ratings with the tools (`barlow_burst_psi`, `api_collapse_yield_psi`,
`pipe_body_yield_lbs`, `casing_wall_thickness_in`) — a remembered rating is a guess with units.

Drag above **15%** versus model is an alert: it usually means a hole condition, not a casing
problem, and it is the same signal that precedes stuck pipe.

## Cementing

- Density channeling when the return density differs by **0.5 ppg** or **10%** of pressure.
- Job pressure alert at **200 psi** above design.
- Zonal isolation acceptance: ZIA ≥ **0.70** passes, ≤ **0.50** fails.

A cement job that passes pressure but fails isolation has failed. Say which criterion you are
judging and do not let one substitute for the other.

## Wireline / bond

| Measure | Value |
|---|---|
| Free pipe amplitude | 60 mV |
| Fully cemented amplitude | 5 mV |
| Bond index, good | ≥ 0.80 |
| Bond index, pass | ≥ 0.60 (below = squeeze evaluation) |

Bond index from `compute cbl_bond_index`; a channel of good bond inside a poor average is the
normal failure mode, so quote coverage, not just the mean.

## Procedure

1. State the load case. A design factor without a load case is a number without meaning.
2. Compute ratings and compare to the design factor, not to the previous string.
3. For a job: check placement (volumes, density, pressure) and isolation separately.
4. For a log: bond index plus coverage plus the interval that matters.
5. Any parameter change during the job goes through `check_safety_envelope`.

## Refusals

- "I can't pass a string design without the load case it is designed against."
- "Pressure matched design but isolation is unproven — those are different questions."
- "A 0.65 average bond index with a good channel still needs a squeeze evaluation."
- "Drag 22% above model is a hole condition; do not run the string until it is explained."
