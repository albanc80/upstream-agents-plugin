# Boundaries

What this package refuses to do, and why. These are non-goals, not configuration.

## No actuation

No tool writes a setpoint, commands a BOP or choke, or executes an approved recommendation. The
advisory server has eleven tools and none of them has that capability. `route_autonomy` can
return `auto_execute` because the engine would, and it then says plainly that this pack never executes.

## No safety verdict from prose

The safety envelope, the quality gate, the veto matrix and the alert ladder are enforced by
tools. A skill that reasons about them without calling the tool is a defect, not a shortcut. If
the server is unavailable the skills are written to say "no deterministic verdict is
available" — never to produce a plausible number.

## No invented thresholds

Every number in `src/agents/` and `src/policies/` is transcribed from the engine with
`file:line` provenance in `docs/THRESHOLDS-TRACE.md`, and `tools/validate.py` fails if a
contract threshold has no trace entry. Where the implementation and its own specification
disagree — the tier table, the gas signal, the unreachable alert level 5 — the disagreement is
recorded rather than resolved silently.

## Defaults are not limits

`src/policies/site-defaults.yaml` ships with `site_validated: false` and no well, field or
approver. Every limit therefore comes from baseline engineering defaults. Presenting one as a
site limit is a factual error, and the tools report `site_validated` on every envelope result so
the claim is checkable.

## Known model gaps

- No mud/gas model, so gas-cut mud makes ECD and MAASP read optimistic.
- The stuck-pipe mechanism classifier is heuristic, not a trained model; its weights are
  engineering defaults.
- The PWD kick residual reaches well control one cycle late (agents run concurrently).
- Alert level 5 ("Blowout Risk") is defined in the engine but unreachable.

Each is recorded in the relevant contract's `known_gaps`.

## Argument names are validated by the client, not the server

The MCP layer builds a per-tool argument model from the function signature and ignores names it does
not recognise, so a misspelt argument arrives as a default value rather than an error. Two
mitigations are in place: the empty-payload guard refuses a call where every signal is zero (which is
what a fully misspelt call looks like), and likely names are accepted as aliases
(`flow_check_positive` -> `flow_check_pumps_off`).

A server-side strict rejection of unknown names cannot be expressed through this MCP layer without
changing the tools' argument shape to a single `args` object, which would break every existing
caller. That is a deliberate trade, recorded here rather than left as a silent hole.
