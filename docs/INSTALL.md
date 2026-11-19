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
codex plugin marketplace add https://github.com/ilbambinomx/upstream-agents-plugin
codex plugin add upstream-agents-plugin
```

Codex consumes the same `plugin.json` and the same `skills/` directory. For a local working
copy during development, `~/.codex/skills` accepts the skill folders directly.

## Claude (Code, Desktop)

Claude is **not** an Agent Plugins v1 client, so the package ships a shim at
`.claude-plugin/plugin.json` plus a `.mcp.json` that points at the same server:

```bash
claude --plugin-dir .          # load this working copy
claude plugin validate .       # manifest and component check
```

The skills are the same files; only the manifest differs. A marketplace listing is deliberately
not included — that needs the marketplace schema and a distribution decision.

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
