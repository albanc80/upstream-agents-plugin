# Upstream Agents Plugin

A portable **[Agent Plugins v1](https://agent-plugins.org)** package carrying upstream drilling
and well-lifecycle advisory agents, derived from a private reference implementation.

**Advisory only.** Nothing here commands a rig, a BOP or a choke, and nothing writes a setpoint.
Every numeric recommendation is expected to come from the deterministic advisory server, not
from a model's own arithmetic.

## Status

| Phase | Scope | State |
|---|---|---|
| P0 | Manifest, two proof contracts, policies, provenance trace, validator | done |
| P1 | All 17 contracts + 4 skills — installable package | done |
| **P2** | `servers/advisory_core` deterministic MCP + `mcp.json` | **done** |
| P3 | Install verification in Hermes and Codex | done for Hermes |
| P4 | Remaining 6 skills | done |
| P5 | Claude shim | done; OpenClaw / Copilot untested |
| P6 | CI, docs, release | CI + docs done; no tagged release |

## What is in the package

```
plugin.json          Agent Plugins v1 manifest
mcp.json             declares the advisory-core stdio server
skills/              10 Agent Skills (SKILL.md + references)
src/agents/          17 agent contracts: tier, veto, thresholds, citations
src/policies/        safety envelope, veto matrix, never-do list, site defaults
servers/advisory_core deterministic advisory spine — 11 MCP tools, 31 formulas
tests/               engine parity + behaviour tests (30)
docs/                INSTALL, BOUNDARIES, THRESHOLDS-TRACE
tools/validate.py    manifest + contract + skill + provenance gate
.claude-plugin/      Claude shim (Claude is not a v1 client)
.github/workflows/   CI: validate, test, schema conformance
LICENSE · NOTICE     Apache-2.0 + engineering safety notice
```

## Skills

| Skill | Domain |
|---|---|
| `upstream-ops` | Router: quality gate first, then one specialist |
| `well-control-guard` | Tier-1: kick/loss detection, alert ladder, kill sheet |
| `stuck-pipe-prevention` | Risk score, four mechanisms, movement veto |
| `drilling-optimization` | MSE, founder point, dysfunction diagnosis |
| `hydraulics-and-fluids` | ECD, mud-weight window, hole cleaning |
| `directional-and-geosteering` | Survey QA, DLS, collision, landing |
| `well-construction` | Casing design factors, cementing, bond logs |
| `completions-and-production` | Stage design, screenout, lift, decline, integrity |
| `data-quality-and-standards` | Six-check quality gate, units, WITSML/ETP identity |
| `agentic-coordination` | Tiers, vetoes, negotiation, routing, audit |

## Advisory tools

`list_capabilities`, `list_channels`, `list_formulas`, `compute`, `qse_score_sample`,
`check_safety_envelope`, `route_autonomy`, `negotiate`, `well_control_assess`, `audit_append`,
`audit_trace`.

They read their thresholds from the packaged contracts, so a tool and the skill that cites it
cannot disagree. `compute` covers 31 formulas transcribed verbatim from the engine, including MAASP,
kill-mud weight, ICP/FCP, ECD, MSE, dogleg and minimum curvature, casing burst/collapse/tension,
CBL bond index and Arps decline.

## Install

See [docs/INSTALL.md](docs/INSTALL.md). Short form:

```bash
hermes plugins install ilbambinomx/upstream-agents-plugin && hermes plugins enable upstream-agents-plugin
codex plugin marketplace add https://github.com/ilbambinomx/upstream-agents-plugin && codex plugin add upstream-agents-plugin
claude --plugin-dir .          # Claude uses the .claude-plugin shim
```

The tools need [`uv`](https://docs.astral.sh/uv/) on `PATH`; dependencies are declared inside the
server script and resolved on first run.

## Verify

```bash
python tools/validate.py                                         # expect PASS 0 failures
uv run --with pytest --with pyyaml -- python -m pytest tests -q   # expect 30 passed
hermes plugins validate .                                        # portable v1 accepted
```

## Reading order

1. [docs/BOUNDARIES.md](docs/BOUNDARIES.md) — what this refuses to do, and the model gaps.
2. [docs/THRESHOLDS-TRACE.md](docs/THRESHOLDS-TRACE.md) — every number and its source line.
3. `src/agents/*.yaml` — the contracts, including `known_gaps` per agent.

## Contract rules

1. **Numbers are transcribed, never tuned.** Every threshold cites an engine module and line in
   `docs/THRESHOLDS-TRACE.md`. To change a value, change the reference implementation and re-extract.
2. **Known gaps are recorded, not smoothed over.** Where the reference implementation does not do what
   its spec claims, `known_gaps` says so, and the discrepancies found so far are recorded in
   `src/policies/veto-matrix.yaml`.
3. **Guarantees live in tools, not prose.** A skill that *explains* the safety envelope without
   invoking it is a liability.
4. **Site values are not shipped as truth.** `src/policies/site-defaults.yaml` is flagged
   `site_validated: false` until a named well or field provides real limits.

## Licence

Apache License 2.0 — see `LICENSE` and `NOTICE`. The package includes an engineering safety notice: it is decision
support, not a control system, and outputs must be verified against the applicable drilling programme before use.
