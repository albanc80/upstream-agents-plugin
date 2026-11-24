# Upstream Agents Plugin

A portable **[Agent Plugins v1](https://agent-plugins.org)** package carrying upstream drilling
and well-lifecycle advisory agents, derived from a private reference implementation.

**Advisory only.** Nothing here commands a rig, a BOP or a choke, and nothing writes a setpoint.
Every numeric recommendation is expected to come from the deterministic advisory server, not
from a model's own arithmetic.

## What it does

Nine advisory domains across the well lifecycle, one deterministic engine behind them. It reads
telemetry, scores it, applies thresholds, and tells you what the numbers mean and what is allowed.
It never touches the rig.

### What you can ask it

| Ask about | You get | Skill |
|---|---|---|
| Influx, gain, losses, SIDPP, MAASP, kill sheet | Alert level and fused probability, kick/loss class, MAASP, kill MW, ICP, FCP | `well-control-guard` |
| Drag, torque, overpull, a string that will not move | 0–100 risk score, mechanism, intervention, movement veto | `stuck-pipe-prevention` |
| ROP, MSE, founder point, vibration | MSE, founder-point call, envelope-checked WOB/RPM change | `drilling-optimization` |
| ECD, hole cleaning, mud weight, surge and swab | ECD against the window, transport ratio, margins | `hydraulics-and-fluids` |
| Surveys, DLS, toolface, collision, landing | DLS and min-curvature position, separation factor, target position | `directional-and-geosteering` |
| Casing design, cement job, bond log, wireline | Design factors, placement vs isolation, bond index | `well-construction` |
| Perforation, stages, lift, decline, integrity | Stage and cluster checks, screenout, loading, decline, SCP | `completions-and-production` |
| Channels, units, mnemonics, timestamps | Six-check quality score and the specific defect | `data-quality-and-standards` |
| Who may act, conflicting advice, audit trail | Tier precedence, veto outcome, routing, chained record | `agentic-coordination` |
| Anything spanning several domains | One specialist, chosen after the quality gate | `upstream-ops` |

### What it identifies

**Influx and losses.** A kick or loss on a five-step ladder — Normal, Monitor, Advisory, Well
Control Alert, Emergency Shut-In Proposal — fused from pit gain, flow differential, gas and the PWD
residual. Classifies `GAS_KICK`, `WATER_KICK` or `LOST_CIRCULATION`, and level 3 upward flags
regulatory notification. Bands: probability 0.20 / 0.40 / 0.60 / 0.85, pit gain above 2 bbl
advisory, above 5 bbl emergency.

**Stuck pipe.** A 0–100 risk score from torque excess (0.40), overpull (0.30), overbalance (0.20)
and inclination (0.10), banded at 25 advisory, 40 active, 60 immediate, 80 critical. Names the
mechanism — differential sticking, pack-off, key seat, collapse — and above 60 it vetoes any WOB
increase, offering WOB −3 klbs and RPM +10 instead.

**Hole cleaning and hydraulics.** Cuttings transport ratio below 0.55 is a problem and below 0.40 a
deficit; slip velocity 45 ft/min; ECD warning at 90% of fracture gradient and critical at 95%. The
mud weight window wants 0.2 ppg overbalance and a 0.3 ppg ECD-to-gradient margin.

**Drilling performance.** Teale MSE and the founder point: rising MSE at flat ROP means additional
weight is buying heat, not hole. Changes below 2% are not worth making; vibration above 0.7 is
dysfunction, not optimisation.

**Trajectory.** DLS against a 5.0 deg/100 ft limit, position by minimum curvature rather than
interpolation, 5 ft minimum survey spacing, well separation factor caution at 1.5 with a mandatory
stop at 1.0, 25 ft collision boundary.

**Tubulars and cement.** Design factors of 1.10 burst, 1.00 collapse and 1.30 tension, with drag
above 15% of model as an alert. Cement: density channeling at 0.5 ppg or 10% of pressure, job
pressure 200 psi over design, zonal isolation 0.70 to pass and 0.50 to fail, bond index 0.80 good
and 0.60 marginal.

**Completions and production.** Isolation gate of 0.70, at most 5 clusters per stage at 40 ft
spacing, screenout on a 500 psi/min rise sustained over 3 readings, MAOP alert at 95%, liquid
loading against a 1.2 Turner factor, sustained casing pressure flagged at 30 psi rising to 100 psi,
reforecast when EUR moves 20%.

**Formation evaluation.** Net-pay screens: water saturation at or below 0.65, porosity at least
0.08, resistivity at least 20 ohm·m, shows where Sw is at or below 0.5.

**Data defects.** Six checks — physical bounds, sequence, redundancy drift, outliers, completeness
and voting — collapsed into one 0–1 score. Below 0.95 the sample is not actionable, and the correct
answer becomes the defect rather than the value.

**Conflicts and authority.** Which proposal wins by tier, which vetoes were raised, what safer
alternative was generated, whether a human must confirm, and a hash-chained record of the decision.

### What it computes

31 formulas behind one tool, so no client does the arithmetic itself: pressure gradient,
hydrostatic pressure, mud weight from pressure, buoyancy, ECD, MAASP, mud weight window, kick
tolerance, kill mud weight, formation pressure, ICP, FCP · pipe and annular capacity, annular
velocity, cuttings transport · Teale MSE · dogleg angle and severity, minimum curvature · Vshale,
density porosity, Archie saturation · casing wall thickness, Barlow burst, API collapse, body yield
· CBL bond index · Turner critical velocity, Arps hyperbolic decline.

### Who decides

17 agent contracts in four tiers: **3 safety** (well control, PWD, MWD), **12 NPT** (casing,
cementing, completions, fluids, geosteering, hydraulics, LWD, production, stimulation, stuck pipe,
well planning, wireline), **1 performance** (directional steering) and **1 cost** (drilling
optimisation). The lower tier wins a conflict; safety outranks confidence.

### What it will not do

- **No actuation.** No BOP, choke, pump or setpoint command exists anywhere in the package.
- **No safety verdict from prose.** The gates are tools; a skill that skips one is a defect.
- **No invented thresholds.** Every number traces to a module and line in
  [`docs/THRESHOLDS-TRACE.md`](docs/THRESHOLDS-TRACE.md).
- **No site limits.** `site_validated` stays false until a named well supplies real ones.

## Status

| Phase | Scope | State |
|---|---|---|
| P0 | Manifest, two proof contracts, policies, provenance trace, validator | done |
| P1 | All 17 contracts + 4 skills — installable package | done |
| P2 | `servers/advisory_core` deterministic MCP + `mcp.json` | done |
| P3 | Install verification in Hermes, Codex and Claude Code | done |
| P4 | Remaining 6 skills | done |
| P5 | Claude shim + marketplace, so clients install from the repo | done; OpenClaw untested |
| P6 | CI, docs, example, security policy | done |
| **Release** | **public, `v1.0.0` tagged** | **[docs/PUBLIC-RELEASE.md](docs/PUBLIC-RELEASE.md)** |

## What is in the package

```
plugin.json          Agent Plugins v1 manifest
mcp.json             declares the advisory-core stdio server
skills/              10 Agent Skills (SKILL.md + references)
src/agents/          17 agent contracts: tier, veto, thresholds, citations
src/policies/        safety envelope, veto matrix, never-do list, site defaults
servers/advisory_core deterministic advisory spine — 11 MCP tools, 31 formulas
tests/               93 tests: parity, behaviour, audit regressions, claim guard
examples/            gas-influx walkthrough — 18 asserted values, runs in CI
docs/                INSTALL, BOUNDARIES, THRESHOLDS-TRACE, REVIEW-BRIEF
tools/validate.py    manifest + contract + skill + provenance gate
.claude-plugin/      Claude shim + marketplace.json (Codex reads it too)
.github/workflows/   CI: validate, tests, walkthrough, selftest, schema
LICENSE · NOTICE     Apache-2.0 + engineering safety notice
SECURITY.md          what to report, and how
```

## Advisory tools

`list_capabilities`, `list_channels`, `list_formulas`, `compute`, `qse_score_sample`,
`check_safety_envelope`, `route_autonomy`, `negotiate`, `well_control_assess`, `audit_append`,
`audit_trace`.

They read their thresholds from the packaged contracts, so a tool and the skill that cites it
cannot disagree. `compute` covers 31 formulas transcribed verbatim from the engine, including MAASP,
kill-mud weight, ICP/FCP, ECD, MSE, dogleg and minimum curvature, casing burst/collapse/tension,
CBL bond index and Arps decline.

## Harness support

The package is portable, but *portable* is not the same as *every client*. What matters is whether
the harness can spawn a **local stdio process**, because that is how the advisory tools are served.

| Harness | Skills | Advisory tools | Path |
|---|---|---|---|
| **Hermes** | yes | yes | `hermes plugins install` — verified |
| **Codex** | yes | yes | `codex plugin marketplace add` + `plugin add` — reads `mcp.json`, verified |
| **Claude Code** | yes | yes | `.claude-plugin/` shim, `claude plugin validate` passes, verified |
| **OpenClaw** | v1 client | expected | bundles path — not exercised here |
| **Copilot / Cursor / VS Code / Kiro** | v1 clients | client-dependent | they install the package; spawning the stdio server is their setting |
| **ChatGPT desktop / Codex runtime** | yes | yes | MCP entry in `~/.codex/config.toml` — verified in a live session |
| **chatgpt.com, ChatGPT mobile** | no | no | no local process; needs a remote HTTPS MCP endpoint |

**The dividing line is whether the surface runs a local process**, not whose brand is on it. Anything
running the Codex runtime — Codex CLI or the ChatGPT desktop app — hosts the bundled server; register
it once in `~/.codex/config.toml` (see [docs/INSTALL.md](docs/INSTALL.md)). A browser tab or a phone
cannot, so on chatgpt.com you get a competent qualitative answer with no deterministic verdict — and
that is the design working, not a defect:

> The advisory server was unavailable, so no data-quality score, formal alert level, kick
> probability, or validated kill-sheet values were produced.

Every skill is written to say exactly that rather than invent a threshold. Putting the tools in a
browser session means hosting the server as a remote MCP endpoint with authentication — a deployment
and security decision, not a packaging one.

## Install

See [docs/INSTALL.md](docs/INSTALL.md). Verified against the real clients:

```bash
# Hermes
hermes plugins install albanc80/upstream-agents-plugin && hermes plugins enable upstream-agents-plugin

# Codex — the repo declares itself as a marketplace (.claude-plugin/marketplace.json)
codex plugin marketplace add albanc80/upstream-agents-plugin
codex plugin add upstream-agents-plugin@upstream-agents-plugin

# Claude Code
/plugin install upstream-agents-plugin --marketplace albanc80/upstream-agents-plugin
```

Or from a working copy, without installing: `hermes plugins install .`, `claude --plugin-dir .`.

The repository is public: no token or GitHub identity is needed. The plugin's tools need
[`uv`](https://docs.astral.sh/uv/) on `PATH`; dependencies are declared inside the server script and
resolved on first run — see [First run](docs/INSTALL.md).

## Harnesses without MCP registration

The tools are also callable from a shell, through the same engine and the same refusals. Useful
where MCP is unavailable, misconfigured, or hosted in a surface that cannot spawn a process:

```bash
uv run --script servers/advisory_core/main.py --list-tools
uv run --script servers/advisory_core/main.py --call well_control_assess \
  '{"pit_gain_bbl": 4, "flow_diff_gpm": 12, "gas_units_pct": 3.5}'
```

It prints the JSON the MCP tool would return, and exits non-zero on a refusal or bad arguments
rather than answering anyway. The skills use this path before falling back to prose, so an agent
without a working MCP connection still gets deterministic values instead of an estimate.

## Try it

[`examples/`](examples/) holds one worked scenario — a gas influx on a 12¼ in section while the
optimisation agent is still asking for more weight on bit — with 18 asserted values:

```bash
uv run --script examples/run_walkthrough.py      # expect: PASSED — 18 checks
```

It boots the real MCP server over stdio, so it doubles as the integration test and fails on any
drift. [`examples/README.md`](examples/README.md) also gives the three client-side prompts worth
pasting into Hermes, Codex or Claude, and the anti-patterns that mean a client is bluffing.

## Verify

```bash
python tools/validate.py                                         # expect PASS 0 failures
uv run --with pytest --with pyyaml -- python -m pytest tests -q   # expect 93 passed
uv run --script servers/advisory_core/main.py --selftest         # expect 5 [OK] lines
hermes plugins validate .                                        # portable v1 accepted
```

## Reading order

1. [docs/BOUNDARIES.md](docs/BOUNDARIES.md) — what this refuses to do, and the model gaps.
2. [docs/THRESHOLDS-TRACE.md](docs/THRESHOLDS-TRACE.md) — every number and its source line.
3. [docs/REVIEW-BRIEF.md](docs/REVIEW-BRIEF.md) — what a drilling reviewer should check in the numbers, and what to ignore.
4. `src/agents/*.yaml` — the contracts, including `known_gaps` per agent.

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
