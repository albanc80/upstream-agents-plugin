# Public release

**Status: public and released.** `v1.0.0` is tagged, the repository is live at
`github.com/albanc80/upstream-agents-plugin`, and every install command in the docs works with no
credential.

This file records what was verified, why it was safe to publish, and what remains optional.

## What was done, in order

| Step | Result |
|---|---|
| Ownership transferred to the public account | done - history and the `v1.0.0` tag survived |
| Visibility flipped to public | done |
| Repository URL updated in both manifests and all docs | done - `albanc80/upstream-agents-plugin` |
| Commit identity rewritten | 8 commits, all `293514256+albanc80@users.noreply.github.com` |
| Release tagged | `v1.0.0` annotated, matching `plugin.json` |
| Metadata | description and 7 topics set |

## Pre-flight, verified before publishing

| Check | Result |
|---|---|
| Tree clean, no unpushed commits | yes |
| No upstream-platform references in history or files | yes |
| No credentials, tokens or API keys | yes |
| No absolute personal paths in docs (all `<you>` placeholders) | yes |
| No personal email reachable from any ref | yes - noreply identity only |
| Apache-2.0 in both manifests, `LICENSE` + `NOTICE` present | yes |
| Manifest conforms to the Agent Plugins v1 schema | CI step, green |
| Tests / MCP walkthrough / install selftest | 48 / 18 / 5, green |
| Security scan (`hermes plugins validate`) | safe |
| No build artefacts, caches or runtime data tracked | yes |

## Known residual

- **A history rewrite is not a guaranteed purge.** The commits were rewritten and force-pushed before
  publication, so no reference reaches the old identity - but GitHub may retain orphaned objects by
  direct SHA. If total removal matters, ask GitHub Support to garbage-collect, or squash to a fresh
  commit.
- **The transfer leaves a redirect.** GitHub redirects the previous owner's path to this repository,
  which keeps existing clones working and also makes that previous path publicly discoverable. If
  that association should not be visible, it is a GitHub Support request, not a repository change.

## Optional, not required

- **Private vulnerability reporting** is referenced by `SECURITY.md` and must be enabled under
  Settings -> Code security, or the file points at nothing.
- **Tag protection** for `v*`, if the release pointer should not be movable.
- **A CHANGELOG** - the README phase table and the annotated tag message currently carry that
  history.
- **Directory listing** in the Claude or Codex marketplace. The repo is self-installable without it;
  listing adds icon and screenshot requirements that are deliberately absent.
- **"Private reference implementation" phrasing** in `docs/THRESHOLDS-TRACE.md`,
  `docs/BOUNDARIES.md` and every contract header. It names nothing and states the provenance rule a
  reader needs to interpret the numbers; soften only if the existence of an internal upstream should
  not be implied.

## Rollback

```bash
gh repo edit albanc80/upstream-agents-plugin --visibility private
```

Visibility, topics and description are reversible. Publication is the step with irreversible
consequences: a clone taken while public cannot be un-published by later privatising.
