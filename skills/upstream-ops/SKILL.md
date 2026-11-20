---
name: upstream-ops
description: Entry point for upstream drilling and well-lifecycle questions — routes to the right specialist skill, enforces the data-quality gate first, and names the tool that owns each number. Use when a request spans several domains, when it is unclear which specialist applies, when someone asks what this pack can do, or when a conversation needs to move from a general drilling question to a specific decision.
---

# Upstream Ops

The router. Its job is to pick one specialist, check the data before anyone reasons, and keep
every number traceable to a tool.

## What this pack is

Advisory only. It reads, scores, explains and escalates. It never writes a setpoint, commands
a BOP or choke, or decides a shut-in. That boundary is not negotiable in any skill.

## Route

| Ask | Skill |
|---|---|
| Influx, gain, losses, SIDPP, gas in returns, MAASP, kill sheet | `well-control-guard` |
| Drag, torque, overpull, back-off, stuck string | `stuck-pipe-prevention` |
| ROP, MSE, founder point, WOB/RPM, vibration | `drilling-optimization` |
| ECD, hole cleaning, mud weight window, surge/swab, filter cake | `hydraulics-and-fluids` |
| Survey QA, DLS, toolface, dip, landing the well | `directional-and-geosteering` |
| Casing design, cement placement, bond, wireline | `well-construction` |
| Perforation, stimulation, artificial lift, decline, integrity | `completions-and-production` |
| Channels, units, mnemonics, timestamps, quality scores | `data-quality-and-standards` |
| Two recommendations conflict, or who may act | `agentic-coordination` |

## Sequence (do not reorder)

1. **Quality first.** Call `qse_score_sample` for the channels in question. Below 0.95 there is
   no interpretation to give — only a description of the defect.
2. **Check the capability surface.** `list_capabilities` tells you what exists and whether the
   limits are site-validated. They are baseline defaults unless `site_validated` is true; say so.
3. **Route to one skill.** Several domains at once is a symptom of an unstated decision; name
   the decision and route to the skill that owns it.
4. **Numbers from tools.** `compute` for engineering quantities, `well_control_assess` for
   alerts, `check_safety_envelope` before any parameter change, `negotiate` when proposals
   conflict, `route_autonomy` for who may act.
5. **Record what matters.** `audit_append` any decision that changes a plan, a limit or a
   recommendation's standing.

## When the advisory tools are not registered

Do not stop at "unavailable", and do not guess a number. The same engine runs from a shell —
substitute the plugin root, the directory that holds `plugin.json`:

```bash
uv run --script <plugin>/servers/advisory_core/main.py --list-tools
uv run --script <plugin>/servers/advisory_core/main.py --call well_control_assess \
  '{"pit_gain_bbl": 4, "flow_diff_gpm": 12, "gas_units_pct": 3.5}'
```

It prints the same JSON the MCP tool returns and refuses the same bad input, so the value is
deterministic rather than remembered. Doing this is cheaper than a detour through the UI.

Only if that command fails — no `uv`, no Python, no filesystem access — answer qualitatively,
say that no deterministic verdict was produced, and state what the rig team must verify.

## Failure modes to refuse

- Interpreting a channel below the quality floor.
- Quoting a limit without saying whether it is a baseline default or a site value.
- Averaging two conflicting recommendations instead of applying precedence.
- Answering a well-control question inside another domain's procedure.
