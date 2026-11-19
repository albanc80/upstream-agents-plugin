---
name: stuck-pipe-prevention
description: Track and reduce stuck-pipe risk — 0-100 risk score, drag and torque trends, overpull, the four mechanisms and their interventions, and the movement veto on WOB increases. Use for increasing torque or drag, overpull on connections, a string that will not move, back-off or jarring decisions, or when an optimisation proposes more WOB while risk is already elevated.
---

# Stuck Pipe Prevention

A 0-100 risk score, four mechanisms, and one hard rule: when risk is high, more weight is the
wrong answer.

## The score

Computed from four weighted terms: torque excess (0.40), overpull (0.30), overbalance
(0.20), inclination (0.10), each normalised against a scale (6,000 ft-lbs, 60 klbf). Bands:

| Score | Level | Meaning |
|---|---|---|
| < 25 | MONITOR | Baseline |
| 25–39 | ADVISORY | Trend is wrong, change something small |
| 40–59 | ACTIVE | Act now, before it locks |
| 60–79 | IMMEDIATE | Veto territory; string contact must stop |
| ≥ 80 | CRITICAL | Assume stuck; escalation procedure |

Two honest caveats: the mechanism classifier is heuristic, not a trained model, and the
weights are engineering defaults, not field-calibrated. Use the score as a relative trend for
one well, never as an absolute probability.

## The four mechanisms

| Mechanism | Signature | Intervention |
|---|---|---|
| Differential sticking | Overbalance, low side, no rotation | Reduce overbalance, lubricant pill, reduce WOB, circulate |
| Pack-off | Torque up, pressure up, flow restricted | Increase flow, pick up off bottom, high-vis sweep |
| Key seat | Torque up in a tight spot while tripping | Ream with low WOB, consider key-seat wiper |
| Wellbore collapse | Torque and drag up after instability | Increase mud weight, slow down, consider backreaming |

## The movement veto

Above a risk score of 60, any proposal that **increases WOB** is rejected and an alternative
is offered: WOB − 3 klbs and RPM + 10. Pass both proposals to `negotiate` with the veto record
rather than deciding yourself — the alternative belongs in the round.

## Procedure

1. Score it (`compute` the trend terms if needed; call `well_control_assess` only for influx).
2. Name the mechanism and its probability spread; do not assert one cause.
3. Give the smallest intervention that changes the trend, and what would confirm it worked.
4. If a parameter change is proposed, run `check_safety_envelope` — a stuck-pipe alternative is
   still a parameter change and still faces the envelope.
5. Escalate jarring and back-off as **later** steps, after circulation and freeing attempts fail.

## Refusals

- "I can't give a stuck point without a free-point or string-weight measurement."
- "Not more WOB at this risk score — the movement veto blocks it and offers a safer alternative."
- "One mechanism is not established; here is the spread and what would discriminate it."
