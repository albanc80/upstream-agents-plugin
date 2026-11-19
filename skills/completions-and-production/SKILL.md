---
name: completions-and-production
description: Completion design, stimulation and production surveillance — cluster spacing and stage limits, pump diagnostics for screenout, MAOP margins, artificial lift selection, liquid loading, decline analysis and sustained casing pressure. Use for perforation and stage design, a frac treating pressure anomaly, lift method choice, decline reforecasts, rate or pressure anomalies, or annular pressure integrity flags.
---

# Completions, Stimulation and Production

Three phases, one discipline: know which measurement would change your mind before you
recommend anything.

## Completion design

- Zonal isolation acceptance gate: **0.70**.
- Maximum clusters per stage: **5**; minimum cluster spacing **40 ft**.
- Lift selection reference: rod pump up to **400 stb/d**, ESP from **1,000 stb/d**; between
  them, the economics decide, not the table.

## Stimulation

- Screenout signature: treating pressure rising **500 psi/min sustained over 3 readings**.
- MAOP alert at **95%** of rating.

A pressure rise is not a screenout until it is sustained — the first reading is noise, the third
is a decision. Above the MAOP threshold the answer is "stop the job", not "watch it".

## Production surveillance

- Liquid loading: compare to Turner critical velocity with a **1.2** loading factor
  (`compute turner_critical_velocity_ft_per_s`).
- Sustained casing pressure: alert at **30 psi**, BSEE-style flag at **100 psi** rise over
  baseline. This is an integrity item, not a production optimisation.
- Decline: Arps hyperbolic via `compute arps_hyperbolic_rate`. Reforecast when EUR moves more
  than **20%**.

## Procedure

1. Quality-gate rate and pressure channels before interpreting a trend.
2. Name the mechanism (loading, skin, depletion, integrity) before proposing a fix.
3. Compute the diagnostic quantity with the tool; state its assumptions (b, Di, fluid properties).
4. For any treating-pressure or rate change: `check_safety_envelope` for MAOP exposure.
5. Integrity flags outrank production targets. Say so when both are in play.

## Refusals

- "Sustained casing pressure is an integrity flag, not a rate opportunity."
- "One pressure reading is not a screenout; three sustained readings is."
- "I can't reforecast decline from one point — the b-exponent changes the answer by more than the data."
- "Rod pump above 400 stb/d is outside the reference envelope; check lift capacity first."
