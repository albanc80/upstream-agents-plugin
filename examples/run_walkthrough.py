#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["mcp>=2"]
# ///
"""Run the gas-influx walkthrough against the packaged server and assert every value.

This is the plugin's working example and its integration test at once: it boots the real MCP
server over stdio exactly as `mcp.json` declares it, drives the scenario in
`gas-influx-12in.json`, and fails if any expected value comes back different.

    uv run --script examples/run_walkthrough.py

Exit code 0 means the shipped artifact behaves as documented. 1 means it does not — do not
trust the example until it passes.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
TOLERANCE = 1e-3


def resolve(payload: Any, dotted: str) -> Any:
    """Walk a dotted path ('winner.parameters.wob') through nested dicts."""
    node = payload
    for part in dotted.split("."):
        if isinstance(node, dict):
            node = node[part]
        elif isinstance(node, list):
            node = node[int(part)]
        else:
            raise KeyError(dotted)
    return node


def matches(actual: Any, expected: Any) -> bool:
    if isinstance(expected, bool) or isinstance(actual, bool):
        return actual is expected
    if isinstance(expected, (int, float)) and isinstance(actual, (int, float)):
        return abs(float(actual) - float(expected)) <= TOLERANCE
    return actual == expected


def check(payload: dict, step: dict) -> list[str]:
    problems: list[str] = []
    for path, expected in step.get("expect", {}).items():
        try:
            actual = resolve(payload, path)
        except (KeyError, IndexError, TypeError):
            problems.append(f"{path}: missing from response")
            continue
        if not matches(actual, expected):
            problems.append(f"{path}: expected {expected!r}, got {actual!r}")

    for path, needle in step.get("expect_contains", {}).items():
        try:
            actual = resolve(payload, path)
        except (KeyError, IndexError, TypeError):
            problems.append(f"{path}: missing from response")
            continue
        haystack = " | ".join(str(x) for x in actual) if isinstance(actual, list) else str(actual)
        if needle not in haystack:
            problems.append(f"{path}: expected to contain {needle!r}, got {haystack!r}")
    return problems


async def run() -> int:
    scenario = json.loads((HERE / "gas-influx-12in.json").read_text(encoding="utf-8"))

    env = dict(os.environ)
    env["PLUGIN_ROOT"] = str(ROOT)
    env["PLUGIN_DATA"] = tempfile.mkdtemp(prefix="advisory-walkthrough-")
    params = StdioServerParameters(
        command="uv",
        args=["run", "--quiet", "--script", str(ROOT / "servers/advisory_core/main.py")],
        env=env,
    )

    print(f"\n{scenario['name']}")
    print(f"{scenario['context']['note']}\n")

    failures = 0
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            info = await session.initialize()
            print(f"server: {info.server_info.name} {info.server_info.version}\n")

            async def call(name: str, args: dict) -> dict:
                result = await session.call_tool(name, args)
                text = result.content[0].text
                try:
                    return json.loads(text)
                except json.JSONDecodeError:
                    return {"_raw": text, "_is_error": bool(getattr(result, "is_error", False))}

            for step in scenario["steps"]:
                payload = await call(step["tool"], step["args"])
                if payload.get("_is_error") or "_raw" in payload:
                    problems = [f"tool error: {payload.get('_raw', payload)!r}"]
                else:
                    problems = check(payload, step)
                status = "PASS" if not problems else "FAIL"
                print(f"  [{status}] {step['id']}")
                if problems:
                    failures += 1
                    for p in problems:
                        print(f"         - {p}")
                if step.get("why") and not problems:
                    print(f"         why: {step['why']}")

            # Audit trail: append two decisions and prove the hash chain holds.
            first = await call("audit_append", {"entry": {"decision": "level 4 emergency", "by": "walkthrough"}})
            second = await call("audit_append", {"entry": {"decision": "WOB 32 blocked", "by": "walkthrough"}})
            trace = await call("audit_trace", {"limit": 2})
            chain_ok = (
                second.get("entry_hash") != first.get("entry_hash")
                and len(trace.get("entries", [])) == 2
                and trace["entries"][1].get("previous_hash") == first.get("entry_hash")
            )
            print(f"  [{'PASS' if chain_ok else 'FAIL'}] 18 audit entries chain by hash")
            if not chain_ok:
                failures += 1
                print(f"         - first={first.get('entry_hash')} second_prev={trace.get('entries', [{}])[-1].get('previous_hash') if trace.get('entries') else None}")

    print()
    if failures:
        print(f"FAILED — {failures} of {len(scenario['steps']) + 1} checks did not match.\n")
        return 1
    print(f"PASSED — {len(scenario['steps']) + 1} checks, every value as documented.\n")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(run()))
