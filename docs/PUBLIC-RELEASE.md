# Public release

The package is **release-ready but still private**. Nothing in the working tree is unpublished:
`main` and `origin/main` match, the tree is clean, and CI is green.

This file is the checklist for flipping it, in order. Steps 1–2 are done; 3–7 are yours to run
because they change ownership or visibility of a live repository.

## Pre-flight — verified

| Check | Result |
|---|---|
| Working tree clean, no unpushed commits | yes |
| History rewritten to a GitHub noreply identity, no upstream-platform references | yes |
| No credentials, tokens or API keys in tracked files or history | yes |
| No absolute personal paths in docs (all `<you>` placeholders) | yes |
| No personal email addresses in tracked files | yes |
| Licence and notice present; `license: Apache-2.0` in both manifests | yes |
| Manifest conforms to the published Agent Plugins v1 schema | CI step, green |
| Tests, MCP walkthrough, server selftest | 48 / 18 / 5 checks, green |
| `hermes plugins validate` security scan | safe |
| No build artefacts, caches or runtime data tracked (`.data/` ignored) | yes |

## 1. Transfer ownership

Transfer `ilbambinomx/upstream-agents-plugin` to your public account in **Settings → General →
Danger Zone → Transfer**. History, issues and stars move with it; the old URL redirects.

## 2. Update the four files that hardcode the slug

After the transfer the old owner is wrong in eight places across four files:

| File | What to change |
|---|---|
| `plugin.json` | `repository` |
| `.claude-plugin/plugin.json` | `repository` |
| `README.md` | two install commands and the install block |
| `docs/INSTALL.md` | Hermes, Codex and Claude install commands |

```bash
grep -rl "ilbambinomx/upstream-agents-plugin" . --exclude-dir=.git
```

Then re-pin every local clone, because the `ghauth` identity was tied to the old owner:

```bash
cd <each local clone> && ghauth albanc80
```

## 3. Flip visibility

```bash
gh repo edit <public-account>/upstream-agents-plugin \
  --visibility public \
  --accept-visibility-change-consequences
```

## 4. Re-verify as an outsider

The most important step, and the one that actually fails if anything is missed — clone with **no**
credentials:

```bash
GIT_TERMINAL_PROMPT=0 git clone https://github.com/<public-account>/upstream-agents-plugin.git /tmp/pubcheck
cd /tmp/pubcheck && uv run --script servers/advisory_core/main.py --selftest
```

Expect `selftest OK`. Then confirm each client installs from the public URL with no token, and that
CI still runs green after the transfer (workflows survive, but permissions and secrets do not
always).

## 5. Repository metadata

```bash
gh repo edit <public-account>/upstream-agents-plugin \
  --description "Upstream drilling and well-lifecycle advisory agents: 17 agent contracts, 10 skills and a deterministic advisory MCP. Advisory only — never actuates." \
  --add-topic upstream,drilling,well-control,agent-skills,mcp,witsml,etp
```

## 6. Enable the security channel

`SECURITY.md` points at GitHub private vulnerability reporting. Turn it on: **Settings → Code
security → Private vulnerability reporting**. Without it the file points at nothing.

## 7. Consider before flipping

- ~~**Commit author email**~~ — done. All 8 commits rewritten to
  `293514256+albanc80@users.noreply.github.com`; no other identity is reachable from any ref. Note
  that a rewrite does not necessarily purge GitHub's orphaned objects, so if total removal matters
  ask GitHub Support to garbage-collect, or squash to a single fresh commit.
- ~~**Tag the release**~~ — done. `v1.0.0` is tagged and pushed, matching `plugin.json`.
- **"Private reference implementation" phrasing** appears in `docs/THRESHOLDS-TRACE.md`,
  `docs/BOUNDARIES.md`, and every contract header. It is honest and does not name anything, but it
  does tell a reader an internal upstream exists. Keep or soften — your call.
- **No marketplace submission.** The Claude and Codex marketplace files make the repo
  self-installable; listing it in any directory is a separate review, and the icon/screenshot
  warnings from `claude plugin validate` only matter then.

## Rollback

```bash
gh repo edit <account>/upstream-agents-plugin --visibility private
```

Visibility, topics and description are reversible. A transfer is reversible (the receiving account
can transfer it back). Making it public is the only step with irreversible consequences: anyone may
have cloned it, and a later privatisation does not un-publish what was already taken.
