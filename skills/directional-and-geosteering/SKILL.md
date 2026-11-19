---
name: directional-and-geosteering
description: Well placement and trajectory control — survey quality and spacing, dogleg severity against the limit, toolface and steering decisions, structural dip and TVD uncertainty, landing and staying in target. Use for high DLS, unvalidated surveys, wellbore collision risk, geosteering decisions at the bit, target exits, or when a planned trajectory change needs checking against the envelope.
---

# Directional and Geosteering

Placement is a measurement problem first and a steering problem second. An unvalidated survey
makes every subsequent decision an opinion.

## Survey discipline

- Minimum spacing between stations: **5 ft** measured depth.
- Fold a new station in only after **≥ 50 ft** of advance (lateral offset limit), otherwise the
  projection amplifies noise.
- DLS is `compute dogleg_severity_deg_per_100ft`; the envelope limit is **5.0 deg/100 ft** and
  exceeding it is a hard violation, not a preference.
- Position from `compute minimum_curvature` — never from a straight-line interpolation.

## Anti-collision

- Well separation factor **< 1.5** — caution; **≤ 1.0** — mandatory stop.
- Collision boundary reference: **25 ft**.

These are not advisory niceties. Below a WSF of 1.0 the correct output is "stop and re-plan",
not "proceed with care".

## Geosteering

- Target window: TVD top **9,000 ft** to base **9,400 ft** in the reference case.
- Exit warning at **50 ft** outside the window.
- Automatic TVD correction threshold: **1 ft** — below that, do not chase noise.

Structural dip interpretation is where geosteering fails: a dip misread by a degree moves the
landing by tens of feet. State the dip assumption and what would falsify it.

## Procedure

1. Validate the survey set before using it: spacing, toolface consistency, DLS against the limit.
2. Compute DLS and position with the tools, not by hand.
3. Check the envelope on any trajectory change (`dls_per_100ft` in the proposal).
4. Separate measurement uncertainty from geological uncertainty — they have different fixes.
5. For a landing or a target change, name the decision owner and the evidence needed.

## Refusals

- "This survey hasn't been validated; steering on it compounds the error."
- "DLS 6.2 exceeds the 5.0 limit — that's an envelope violation."
- "WSF below 1.0 means stop, not slow down."
- "I can't place the well from an interpolated position; run minimum curvature on real stations."
