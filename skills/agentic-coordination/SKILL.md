---
name: agentic-coordination
description: Resolve disagreement between drilling advisors the way this package does — four-tier priority, the veto matrix, the four-step negotiation with its timeout budget, five autonomy levels, human-in-the-loop routing and an audit trail. Use when two recommendations conflict, when a recommendation would raise a parameter another domain protects, when asked whether an agent may act on its own, or when a decision needs to be recorded and traceable.
---

# Agentic Coordination

When two specialists disagree, the answer is not the average. It is a precedence rule, a
veto, or an escalation — in that order.

## Precedence (verified against the implementation)

| Tier | Name | Ranked members | Veto |
|---|---|---|---|
| 1 | SAFETY | well control, PWD, MWD | well control only, absolute |
| 2 | NPT | casing, cementing, completions, fluids, geosteering, hydraulics, LWD, production, stimulation, stuck pipe, well planning, wireline | stuck pipe only, movement |
| 3 | PERFORMANCE | directional steering | directional steering, trajectory |
| 4 | COST | drilling optimisation | none |

Tier ranks proposals and breaks ties by composite confidence. **Veto is separate** — only
three agents override `veto()`. PWD and MWD rank Tier 1 and hold no veto.

## The four-step negotiation

1. **Publication** — collect proposals (parameter changes contend; alerts and advisories do not).
2. **Constraint evaluation** — safety envelope plus agent vetoes reject non-compliant asks.
3. **Alternative generation** — a veto that carries safer parameters re-enters as a candidate.
4. **Consensus** — highest tier wins, then highest confidence.

Outcomes: CONSENSUS, SAFETY_VETO, DEADLOCK, TIMEOUT. Total budget is 2,000 ms
(500 publication / 400 constraint / 600 alternative / 500 consensus).

## Autonomy and routing

Five levels. Routing: confidence below 0.70 is advisory-only; level 1 is human-confirm;
confidence at or above 0.85 at level 2+ would auto-execute **in a controlling runtime**. Promotion above 0.85
over 50 cycles needs a human; a safety violation demotes to level 1 immediately.

**In this pack nothing auto-executes, at any level.** If asked whether an agent may act
alone, the answer is no.

## Procedure

1. Name the proposals and the agents that own them.
2. Run `check_safety_envelope` first — an unsafe ask never reaches the tie-break.
3. Apply vetoes; if one fires, look for the alternative it carries before concluding deadlock.
4. Call `negotiate` with the proposals and veto records. Show the losing proposal and why it lost.
5. Call `route_autonomy` for the routing, then state human-confirm or advisory-only — nothing here executes.
6. Call `audit_append` with agent, tier, confidence, rejections, winner and approver.

## Refusal sentences

- "Two of these conflict; the safety-tier veto decides, and it is not a negotiation."
- "I can't average these recommendations. One is rejected and here is the rejection record."
- "Nothing here executes on its own. This needs a named human approver."
- "That decision needs an audit entry: agent, tier, confidence, rebuttal, approver."

## Degraded mode

Without the advisory server, present the precedence table and the conflict explicitly, and
state that the negotiation verdict was not computed. First try the shell fallback in `upstream-ops`:
`--call negotiate` returns the same JSON the tool would.
