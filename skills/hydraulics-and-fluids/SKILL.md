---
name: hydraulics-and-fluids
description: Mud, hydraulics and hole cleaning for drilling — ECD and APL, the mud-weight window, cuttings transport and slip velocity, surge and swab, filter cake, shale inhibition, and the margins that keep ECD inside the fracture gradient. Use for high ECD, poor hole cleaning, cuttings beds, tight hole on trips, mud weight decisions, losses while circulating, or barite sag.
---

# Hydraulics and Fluids

Two failure directions, one window: stay above pore pressure and below the fracture gradient,
and keep the hole clean while you do it.

## The window and its margins

- Operating window is pore-pressure EMW (lower) to fracture gradient (upper).
- Minimum overbalance above pore pressure: **0.2 ppg**.
- Minimum ECD-to-fracture-gradient margin: **0.3 ppg**.
- ECD warning at **90% of the fracture gradient**.
- Observed MWW max is fracture gradient minus **0.3 ppg**.

ECD is not mud weight. `compute equivalent_circulating_density_ppg` with the annular pressure
loss; the difference is the whole point of the margin.

## Hole cleaning

| Quantity | Threshold |
|---|---|
| Cuttings transport ratio, adequate | ≥ 0.55 |
| CTR, deficit | < 0.40 |
| Slip velocity (default geometry) | 45 ft/min |
| Hole / pipe (default) | 8.5 in / 5.0 in |

CTR comes from `compute cuttings_transport_ratio` with annular velocity, slip velocity and
inclination — inclination is the term people forget, and it dominates above 60°.

## Fluid properties

Filter cake above **3.0 mm** and shale inhibition below **0.60** are the two property failures
that show up later as stuck pipe or instability, not as an immediate alert.

## Procedure

1. Quality-check ECD, flow and pit volume before anything (`qse_score_sample`).
2. Compute ECD and the margins; state both the value and the distance to the gradient.
3. Assess cleaning with CTR, annular velocity and the inclination profile.
4. For any mud-weight or flow change: `check_safety_envelope` — ECD outside the window is a
   **hard** violation, not a preference.
5. Say what the change buys and what it costs elsewhere; a heavier mud raises ECD and losses
   risk, a faster pump raises ECD and erosion.

## Refusals

- "ECD is 0.05 ppg from the fracture gradient; that is not a margin I would call safe."
- "I can't judge cleaning without inclination — on a 70° section the vertical answer is wrong."
- "That mud weight change fails the envelope; it isn't a trade-off, it's a violation."
- "Gas-cut mud makes this ECD read optimistic; no mud/gas model exists, so treat the margin as unverified."
