# Install

The repo root **is** the package. Every client below installs it directly; nothing is generated
first.

## Prerequisite for the tools

The advisory MCP runs as a PEP 723 script, so it needs [`uv`](https://docs.astral.sh/uv/) on
`PATH`. Its dependencies (`mcp>=2`, `pyyaml`) are declared inside
`servers/advisory_core/main.py` and resolved on first run. There is no virtualenv to manage and
nothing to `pip install`.

Without `uv`, the skills still load — you lose the deterministic verdicts and the skills will
say so instead of guessing.

## First run

Registration is automatic — every verified client reads the package's own manifests, so nothing has
to be wired by hand:

| Client | What registers the server | When it takes effect |
|---|---|---|
| Hermes | `mcp.json` | next session ("deferred: MCP servers") |
| Codex | `mcp.json`, via the plugin | next session — `codex mcp list` shows `advisory-core` |
| Claude Code | `.mcp.json`, via `.claude-plugin/` | next session — `claude mcp list` shows the plugin entry |

The **dependencies** are the part that resolves lazily, on first boot: about 9 s with an empty `uv`
cache (`mcp`, `pydantic`, `pyyaml`). Warm them before a session, so a cold start cannot collide with
a client's MCP startup timeout:

```bash
uv run --script servers/advisory_core/main.py --selftest
```

Expect five `[OK]` lines and `selftest OK`. It checks the install as well as warming it — 17
contracts, 10 skills, 31 formulas and the policy YAML — and exits non-zero if any is missing. If a
client still times out on its very first launch, raise its startup allowance (Codex:
`startup_timeout_sec` in `config.toml`).

## Hermes

```bash
hermes plugins install ilbambinomx/upstream-agents-plugin    # private: add a token first
hermes plugins enable upstream-agents-plugin
```

Portable v1 packages install **disabled** by design; enabling is the trust decision. Verify
what you are trusting first:

```bash
hermes plugins validate .          # from a clone
hermes plugins show upstream-agents-plugin
```

For a private repo, `hermes plugins install` needs a token. If the profile's `GITHUB_TOKEN` is
stale it will report `Repository not found`; pass a token URL or sign in with `gh auth login`.

## Codex

```bash
codex plugin marketplace add ilbambinomx/upstream-agents-plugin
codex plugin add upstream-agents-plugin@upstream-agents-plugin
```

Codex needs a **marketplace**, not just a plugin: it reads
`.agents/plugins/marketplace.json` or, as here, a Claude-compatible
`.claude-plugin/marketplace.json` at the repository root. The `add` step requires the
`<plugin>@<marketplace>` form — a bare name fails with "plugin requires --marketplace".
`codex plugin list` shows the version and status.

For a local working copy during development, `codex plugin marketplace add ./` from the repo root
works too, and `~/.codex/skills` accepts the skill folders directly.

## Claude (Code, Desktop)

Claude is **not** an Agent Plugins v1 client, so the package ships a shim at
`.claude-plugin/plugin.json` plus a `.mcp.json` that points at the same server, and declares itself
as a marketplace in `.claude-plugin/marketplace.json` (which also carries the required `owner`).

```bash
claude plugin validate .                                        # verified: passes
claude plugin marketplace add ilbambinomx/upstream-agents-plugin
claude plugin install upstream-agents-plugin@upstream-agents-plugin
claude --plugin-dir .                                           # or load a working copy without installing
```

`claude plugin list` reports the version, source and enabled state. The marketplace entry is
deliberately minimal — no icon, no screenshots — because the listing assets only matter if the
plugin is submitted to a directory, and that is a separate decision.

## ChatGPT (web, mobile, desktop chat)

Not supported, and not fixable by packaging. ChatGPT only consumes **remote** HTTPS MCP servers
with OAuth; a bundled stdio server cannot be reached from a chat window. Ask it a well-control
question and you will get a competent qualitative answer that explicitly says no deterministic
verdict was produced — the skills are written to refuse rather than invent a threshold.

Making it work is a deployment project, not a packaging one:

- `servers/advisory_core/main.py` already speaks MCP; it needs a streamable-HTTP transport instead
  of stdio, a public TLS endpoint, authentication and rate limiting.
- Treat it as a production service. The package has no actuation path, but the thresholds and the
  17 contracts are commercially sensitive and must not be publicly reachable without auth, logging
  and a way to disable it.

## OpenClaw

OpenClaw is a v1 client; install through its plugin bundles path
(`docs.openclaw.ai/plugins/bundles`), or point it at the skill folders in `skills/` and register
the MCP server with `openclaw mcp set`.

## Copilot, Cursor, VS Code, Kiro, Antigravity

All are v1 clients. Point them at this repository through their own plugin UI; no additional
files are needed.

## Verifying an install

```bash
python tools/validate.py                                   # manifest, contracts, skills, provenance
uv run --with pytest --with pyyaml -- python -m pytest tests -q
```

Expected: `PASS 0 failures` and 30 passing tests. Then, in the client, ask what the pack can do
— `list_capabilities` should report 31 formulas and `envelope_site_validated: false`.

That `false` is important: the limits shipped are baseline engineering defaults, not any well's
approved drilling programme.
