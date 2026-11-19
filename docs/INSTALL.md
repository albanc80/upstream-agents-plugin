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
