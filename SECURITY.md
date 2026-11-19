# Security policy

## What this package is

Decision support for well construction and drilling operations. It is **advisory only**: no tool
writes a setpoint, commands a BOP or choke, or executes a recommendation. Shut-in and execution
authority rest with the Driller and Drilling Supervisor.

It is not a control system, not a certified safety instrument, and not a substitute for the
applicable drilling programme, site-specific data or governing regulation.

## Reporting a vulnerability

Use GitHub's private vulnerability reporting: **Security → Advisories → Report a vulnerability**.
Please do not open a public issue for a security matter.

Useful reports include:

- a tool returning a value that contradicts its contract or `docs/THRESHOLDS-TRACE.md`
- a safety gate that passes something it should block, or the reverse
- prompt-injection resistance: a skill or tool being steered by telemetry or document content
- the advisory server writing outside its data directory, or reaching the network
- a dependency or packaging flaw that lets an install execute something unexpected

This is a single-maintainer project with no support contract. Reports are handled on a best-effort
basis; there is no SLA and no bug bounty.

## Scope

In scope: the code, contracts, policy files, skills and packaging in this repository.

Out of scope: disagreement with an engineering threshold on domain grounds — those are transcribed
and cited, so raise it as an issue against the value and its source, not as a vulnerability. Also out
of scope: the private reference implementation the thresholds were extracted from, which is not
distributed here.

## Supported versions

The `main` branch and the latest tagged release. This package is pre-1.0 and makes no compatibility
promises across minor versions; a threshold or output-shape change is a minor-version bump.
