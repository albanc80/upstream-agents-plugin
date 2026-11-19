#!/usr/bin/env python3
"""Gate for the Upstream Agents Plugin.

Three checks, in order of what actually breaks a client:

  1. plugin.json   — required fields, closed top-level schema, Agent Plugins name rules.
  2. agent contracts — required keys, unknown-key policy, tier bounds, provenance coverage.
  3. policies      — required keys and provenance coverage.

Provenance rule: every leaf under an agent contract's `thresholds` block must appear in
docs/THRESHOLDS-TRACE.md as a dotted path (e.g. `kick_probability.monitor`). Policy files
are checked by leaf key name only — their numbers are grouped prose rather than scalars.

Exit code 0 = pass, 1 = failures, 2 = cannot run.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TRACE = ROOT / "docs" / "THRESHOLDS-TRACE.md"

MANIFEST_KEYS = {
    "$schema", "name", "version", "description", "author", "homepage",
    "repository", "license", "keywords", "extensions",
}
MANIFEST_REQUIRED = {"$schema", "name"}
SCHEMA_URI = "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json"
AUTHOR_KEYS = {"name", "email", "url"}

CONTRACT_REQUIRED = {
    "schema", "id", "title", "tier", "tier_name", "summary",
    "autonomy", "veto", "inputs", "thresholds", "actions", "refusals", "citations",
}
CONTRACT_OPTIONAL = {
    "phase", "alert_ladder", "compute", "known_gaps", "mechanisms", "notes",
}

failures: list[str] = []
warnings: list[str] = []


def fail(msg: str) -> None:
    failures.append(msg)


def warn(msg: str) -> None:
    warnings.append(msg)


def leaf_paths(node, prefix="") -> list[str]:
    """Yield dotted paths for every scalar leaf (used for agent thresholds)."""
    out: list[str] = []
    if isinstance(node, dict):
        for k, v in node.items():
            out.extend(leaf_paths(v, f"{prefix}.{k}" if prefix else str(k)))
    elif isinstance(node, list):
        for v in node:
            out.extend(leaf_paths(v, prefix))
    elif isinstance(node, (str, int, float)) and not isinstance(node, bool):
        out.append(prefix)
    return out


def numeric_leaves(node, prefix="", chain=()) -> list[tuple[str, tuple[str, ...]]]:
    """Yield (dotted path, ancestor chain) for every *numeric* leaf.

    Policies mix numbers with prose (notes, rationales, refusals). Only numbers need
    provenance; prose is reviewed by a human, not traced to a line number.
    """
    out: list[tuple[str, tuple[str, ...]]] = []
    if isinstance(node, dict):
        for k, v in node.items():
            out.extend(numeric_leaves(v, f"{prefix}.{k}" if prefix else str(k), chain + (str(k),)))
    elif isinstance(node, list):
        for v in node:
            out.extend(numeric_leaves(v, prefix, chain))
    elif isinstance(node, (int, float)) and not isinstance(node, bool):
        out.append((prefix, chain))
    return out


# --- 1. manifest -----------------------------------------------------------
def check_manifest() -> None:
    path = ROOT / "plugin.json"
    if not path.exists():
        fail("plugin.json is missing")
        return
    try:
        m = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        fail(f"plugin.json is not valid JSON: {exc}")
        return
    if not isinstance(m, dict):
        fail("plugin.json must be a JSON object")
        return

    missing = MANIFEST_REQUIRED - m.keys()
    if missing:
        fail(f"plugin.json missing required field(s): {sorted(missing)}")
    unknown = set(m) - MANIFEST_KEYS
    if unknown:
        fail(f"plugin.json has unknown top-level field(s) (closed schema): {sorted(unknown)}")

    if m.get("$schema") != SCHEMA_URI:
        fail(f"plugin.json $schema must be exactly {SCHEMA_URI}")

    name = m.get("name", "")
    if not isinstance(name, str) or not name:
        fail("plugin.json name must be a non-empty string")
    else:
        if not 1 <= len(name) <= 64:
            fail("plugin.json name must be 1-64 characters")
        if not re.fullmatch(r"[a-z0-9]([a-z0-9.-]*[a-z0-9])?", name):
            fail(f"plugin.json name {name!r} violates v1 rules "
                 "(lowercase ascii, digits, hyphens, periods; must start/end alphanumeric)")
        if "--" in name or ".." in name:
            fail("plugin.json name must not contain '--' or '..'")

    author = m.get("author")
    if author is not None:
        if not isinstance(author, dict):
            fail("plugin.json author must be an object")
        else:
            if set(author) - AUTHOR_KEYS:
                fail(f"author has unknown field(s): {sorted(set(author) - AUTHOR_KEYS)}")
            if "name" not in author:
                fail("author.name is required when author is present")

    if "keywords" in m and not isinstance(m["keywords"], list):
        fail("plugin.json keywords must be an array")
    if "extensions" in m and not isinstance(m["extensions"], dict):
        fail("plugin.json extensions must be an object keyed by reverse-domain namespace")


# --- 2. skills -------------------------------------------------------------
def check_skills() -> None:
    skills_dir = ROOT / "skills"
    if not skills_dir.exists():
        warn("skills/ does not exist — valid at P0, required from P1")
        return
    found = 0
    for skill in sorted(p for p in skills_dir.iterdir() if p.is_dir()):
        md = skill / "SKILL.md"
        if not md.exists():
            fail(f"skills/{skill.name}: missing SKILL.md")
            continue
        found += 1
        text = md.read_text(encoding="utf-8")
        if not text.startswith("---"):
            fail(f"skills/{skill.name}/SKILL.md: missing YAML frontmatter")
            continue
        end = text.find("\n---", 3)
        if end == -1:
            fail(f"skills/{skill.name}/SKILL.md: unterminated frontmatter")
            continue
        fm = text[3:end]
        name = re.search(r"^name:\s*(.+)$", fm, re.M)
        desc = re.search(r"^description:\s*(.+)$", fm, re.M)
        if not name:
            fail(f"skills/{skill.name}/SKILL.md: frontmatter missing name")
        elif name.group(1).strip().strip("'\"") != skill.name:
            fail(f"skills/{skill.name}/SKILL.md: frontmatter name "
                 f"{name.group(1).strip()!r} != directory {skill.name!r}")
        if not desc:
            fail(f"skills/{skill.name}/SKILL.md: frontmatter missing description")
        if len(desc.group(1)) > 1024:
            warn(f"skills/{skill.name}: description is long; clients truncate it")
    print(f"  skills checked: {found}")


# --- 3. contracts + policies ----------------------------------------------
def check_contracts(trace_text: str) -> None:
    try:
        import yaml
    except ModuleNotFoundError:
        fail("PyYAML is required to validate contracts (pip install pyyaml)")
        return

    agents_dir = ROOT / "src" / "agents"
    contracts = sorted(agents_dir.glob("*.yaml")) if agents_dir.exists() else []
    if not contracts:
        warn("src/agents has no contracts yet")

    for path in contracts:
        rel = path.relative_to(ROOT).as_posix()
        try:
            doc = yaml.safe_load(path.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            fail(f"{rel}: invalid YAML: {exc}")
            continue
        if not isinstance(doc, dict):
            fail(f"{rel}: top level must be a mapping")
            continue

        missing = CONTRACT_REQUIRED - doc.keys()
        if missing:
            fail(f"{rel}: missing required key(s): {sorted(missing)}")
        unknown = set(doc) - CONTRACT_REQUIRED - CONTRACT_OPTIONAL
        if unknown:
            fail(f"{rel}: unknown key(s) — declare them in CONTRACT_OPTIONAL first: {sorted(unknown)}")

        if path.stem != doc.get("id"):
            fail(f"{rel}: id {doc.get('id')!r} must equal the filename stem {path.stem!r}")

        tier = doc.get("tier")
        if not isinstance(tier, int) or not 1 <= tier <= 4:
            fail(f"{rel}: tier must be an integer 1-4")
        if not doc.get("citations"):
            fail(f"{rel}: citations must be non-empty")
        if not doc.get("inputs") and not doc.get("notes"):
            fail(f"{rel}: inputs are empty — add notes explaining why there are none")
        if not doc.get("refusals"):
            fail(f"{rel}: refusals must be non-empty")

        for gap in doc.get("known_gaps") or []:
            for key in ("id", "detail", "source"):
                if not gap.get(key):
                    fail(f"{rel}: known_gaps entry missing {key!r}")

        # provenance: every threshold leaf must be traced as a dotted path
        for dotted in leaf_paths(doc.get("thresholds") or {}):
            if dotted not in trace_text:
                fail(f"{rel}: threshold {dotted!r} has no entry in docs/THRESHOLDS-TRACE.md")

    print(f"  agent contracts checked: {len(contracts)}")

    policies_dir = ROOT / "src" / "policies"
    policies = sorted(policies_dir.glob("*.yaml")) if policies_dir.exists() else []
    for path in policies:
        rel = path.relative_to(ROOT).as_posix()
        try:
            doc = yaml.safe_load(path.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            fail(f"{rel}: invalid YAML: {exc}")
            continue
        if not isinstance(doc, dict):
            fail(f"{rel}: top level must be a mapping")
            continue
        if doc.get("schema") != "upstream-agents-plugin/policy/v1":
            fail(f"{rel}: schema must be 'upstream-agents-plugin/policy/v1'")
        if not doc.get("id"):
            fail(f"{rel}: missing id")

        # A policy number is traced if the leaf name or any ancestor key is named in the
        # trace. Ancestor matching is what makes grouped values legal: the trace names
        # `mud_weight_window`, while the contract carries `.min_ppg` / `.max_ppg` leaves.
        body = {k: v for k, v in doc.items() if k not in {"schema", "id"}}
        numeric = numeric_leaves(body)
        if not numeric:
            warn(f"{rel}: contains no numeric assertions — nothing to trace")
        for dotted, chain in numeric:
            leaf = chain[-1] if chain else dotted
            if not any(part in trace_text for part in (leaf, *chain[:-1], dotted)):
                fail(f"{rel}: numeric value {dotted!r} has no entry in "
                     f"docs/THRESHOLDS-TRACE.md (by leaf or parent key)")
    print(f"  policy files checked: {len(policies)}")


def main() -> int:
    if not TRACE.exists():
        print("cannot run: docs/THRESHOLDS-TRACE.md is missing", file=sys.stderr)
        return 2
    trace_text = TRACE.read_text(encoding="utf-8")

    print("upstream-agents-plugin validation")
    check_manifest()
    check_skills()
    check_contracts(trace_text)

    for w in warnings:
        print(f"WARN  {w}")
    if failures:
        print()
        for f in dict.fromkeys(failures):
            print(f"FAIL  {f}")
        print(f"\n{len(failures)} failure(s), {len(warnings)} warning(s)")
        return 1
    print(f"\nPASS  0 failures, {len(warnings)} warning(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
