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

## No MCP? Call the engine directly

If a client cannot spawn the server, or the registration is wrong, the same tools run from a shell:

```bash
uv run --script <plugin>/servers/advisory_core/main.py --list-tools
uv run --script <plugin>/servers/advisory_core/main.py --call well_control_assess '{"pit_gain_bbl": 4}'
```

Same code path, same thresholds, same refusals; exit code 1 on a refusal, 2 on bad arguments or an
unknown tool. This is also the fastest way to prove an install works before wiring a client.

## Hermes

```bash
hermes plugins install albanc80/upstream-agents-plugin
hermes plugins enable upstream-agents-plugin
```

Portable v1 packages install **disabled** by design; enabling is the trust decision. Verify
what you are trusting first:

```bash
hermes plugins validate .          # from a clone
hermes plugins show upstream-agents-plugin
```

The repository is public, so no token is needed. If the profile still holds a stale
`GITHUB_TOKEN`, clear it — a bad credential fails with `Repository not found` even on a public repo.

## Codex

```bash
codex plugin marketplace add albanc80/upstream-agents-plugin
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
claude plugin marketplace add albanc80/upstream-agents-plugin
claude plugin install upstream-agents-plugin@upstream-agents-plugin
claude --plugin-dir .                                           # or load a working copy without installing
```

`claude plugin list` reports the version, source and enabled state. The marketplace entry is
deliberately minimal — no icon, no screenshots — because the listing assets only matter if the
plugin is submitted to a directory, and that is a separate decision.

## ChatGPT desktop / Codex runtime

The ChatGPT desktop app runs the Codex runtime, so it **can** host the bundled server — verified in a
live session. Register it once in `~/.codex/config.toml`:

```toml
[mcp_servers.advisory-core]
command = 'C:\Users\<you>\.local\bin\uv.exe'        # run `where uv` to find yours
args = ["run", "--quiet", "--script", 'C:\Users\<you>\.codex\plugins\cache\upstream-agents-plugin\<version>\servers\advisory_core\main.py']

[mcp_servers.advisory-core.env]
UV_CACHE_DIR = 'C:\Users\<you>\AppData\Local\Codex\advisory-core\uv-cache'
```

Two details make this robust: an **absolute path to `uv.exe`**, because a GUI-launched app may not
inherit your shell's `PATH`, and a **dedicated `UV_CACHE_DIR`**, so dependency resolution is isolated
and can be pre-warmed. Confirm with `codex mcp list` → `advisory-core … enabled`.

## chatgpt.com and mobile

Not supported, and not fixable by packaging: a browser tab or a phone has no local process to spawn.
There the skills answer qualitatively and state that no deterministic verdict was produced, which is
the designed refusal rather than a failure.

Putting the tools in a browser session means hosting `servers/advisory_core` as a remote HTTPS MCP
endpoint — streamable-HTTP transport, TLS, authentication, rate limiting, logging and a kill switch.
A deployment and security decision, not a packaging one, and worth it only if browser sessions are a
real usage target.

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
