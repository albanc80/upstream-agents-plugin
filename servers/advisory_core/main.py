#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["mcp>=2,<3", "pyyaml>=6,<7"]
# ///
"""advisory-core — the deterministic advisory spine as an MCP server.

Speaks MCP over stdio. Every tool is pure computation or append-only bookkeeping: no network,
no writes outside the plugin data directory, no actuation. Numbers come from the same formulas
and thresholds as the reference implementation, so a client cannot get a different answer than the platform.

Run:  uv run --script servers/advisory_core/main.py
"""

from __future__ import annotations

import hashlib
import inspect
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# The package is imported absolutely so this file works both as a PEP 723 script and as a
# module inside the package.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mcp.server.mcpserver import MCPServer  # noqa: E402
from mcp.server.mcpserver.exceptions import ToolError  # noqa: E402

from advisory_core import formulas, model  # noqa: E402
from advisory_core.channel_specs import CHANNEL_SPECS  # noqa: E402

def _package_version() -> str:
    """Single source of truth: the manifest version, so the server cannot drift from it."""
    try:
        import json as _json
        manifest = Path(os.environ.get("PLUGIN_ROOT") or Path(__file__).resolve().parents[2]) / "plugin.json"
        return str(_json.loads(manifest.read_text(encoding="utf-8"))["version"])
    except Exception:
        return "0.0.0+unknown"


VERSION = _package_version()
# mcp 2.x: FastMCP was renamed to MCPServer; the @tool() decorator and stdio run() are the
# same shape as before.
mcp = MCPServer("advisory-core", version=VERSION)

UNITS = {
    "pressure_gradient_psi_per_ft": "psi/ft",
    "hydrostatic_pressure_psi": "psi",
    "mud_weight_from_pressure_ppg": "ppg",
    "buoyancy_factor": "fraction",
    "equivalent_circulating_density_ppg": "ppg",
    "maasp_psi": "psi",
    "kill_mud_weight_ppg": "ppg",
    "formation_pressure_psi": "psi",
    "initial_circulating_pressure_psi": "psi",
    "final_circulating_pressure_psi": "psi",
    "kick_tolerance_intensity_ppg": "ppg",
    "pipe_capacity_bbl_per_ft": "bbl/ft",
    "annular_capacity_bbl_per_ft": "bbl/ft",
    "annular_velocity_ft_per_min": "ft/min",
    "teale_mse_psi": "psi",
    "vshale_linear": "fraction",
    "density_porosity": "fraction",
    "archie_water_saturation": "fraction",
    "cuttings_transport_ratio": "ratio",
    "dogleg_angle_deg": "deg",
    "dogleg_severity_deg_per_100ft": "deg/100ft",
    "turner_critical_velocity_ft_per_s": "ft/s",
    "casing_wall_thickness_in": "in",
    "barlow_burst_psi": "psi",
    "api_collapse_yield_psi": "psi",
    "pipe_body_yield_lbs": "lbf",
    "cbl_bond_index": "fraction",
    "arps_hyperbolic_rate": "stb/d",
}

# Only functions defined in the formulas module: imported helpers (dataclass) and the
# KalmanFilter1D class are not formulas.
FORMULAS: dict[str, Any] = {
    name: obj
    for name, obj in vars(formulas).items()
    if inspect.isfunction(obj) and not name.startswith("_") and obj.__module__ == formulas.__name__
}


def _resolve_data_dir() -> tuple[Path, bool]:
    """Pick a directory that survives a plugin update.

    The install folder is replaced on upgrade, so anything written inside it — including the
    hash-chained audit trail — is lost exactly when it is worth having. Prefer the data directory
    the client provides; otherwise use a per-user location. Returns (path, is_volatile).
    """
    for var in ("ADVISORY_DATA_DIR", "PLUGIN_DATA", "CLAUDE_PLUGIN_DATA"):
        value = os.environ.get(var)
        if value:
            return Path(value), False
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
    else:
        base = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
    return Path(base) / "upstream-agents-plugin", False


def _migrate_legacy_audit(target_dir: Path) -> None:
    """Carry an existing trail forward from the old in-plugin location rather than abandoning it."""
    legacy = model.plugin_root() / ".data" / "audit.jsonl"
    target = target_dir / "audit.jsonl"
    try:
        if legacy.exists() and not target.exists() and legacy.parent != target_dir:
            target.write_bytes(legacy.read_bytes())
    except OSError:
        pass


def _data_dir() -> Path:
    root, _ = _resolve_data_dir()
    root.mkdir(parents=True, exist_ok=True)
    _migrate_legacy_audit(root)
    return root


def _audit_path() -> Path:
    return _data_dir() / "audit.jsonl"


def _audit_location() -> dict[str, Any]:
    """Report where the trail lives, so a caller can tell that it is not inside the install folder."""
    path = _audit_path()
    return {"audit_path": str(path), "survives_update": ".data" not in str(path.parent)}


def _last_hash() -> str:
    path = _audit_path()
    if not path.exists():
        return "genesis"
    last = None
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                last = line
    if last is None:
        return "genesis"
    try:
        return json.loads(last).get("entry_hash", "genesis")
    except json.JSONDecodeError:
        return "unverified"


# --------------------------------------------------------------------------- tools


@mcp.tool()
def list_capabilities() -> dict[str, Any]:
    """Report what this server can and cannot do. Call this first when a client is unsure.

    Returns the tool inventory, the formula count, whether the packaged limits are
    site-validated, and the hard boundary: this server never actuates and never executes.
    """
    return {
        "server": "advisory-core",
        "version": VERSION,
        "plugin_root": str(model.plugin_root()),
        "tools": [
            "list_capabilities", "list_channels", "list_formulas", "compute",
            "qse_score_sample", "check_safety_envelope", "route_autonomy",
            "negotiate", "well_control_assess", "audit_append", "audit_trace",
        ],
        "formulas_available": len(FORMULAS),
        "envelope_site_validated": model.envelope_site_validated(),
        "limits_are_baseline_defaults_not_site_limits": not model.envelope_site_validated(),
        "boundary": (
            "Advisory only. No tool writes a setpoint, commands a BOP or choke, or executes a "
            "recommendation. Shut-in authority rests with the Driller and Drilling Supervisor."
        ),
    }


@mcp.tool()
def list_channels() -> dict[str, Any]:
    """List telemetry channels with units, physical bounds and typical operating range.

    Use before scoring a sample or interpreting a value: a reading outside hard bounds is
    physically impossible, and the unit is part of the answer.
    """
    return {
        "channels": {
            name: {
                "unit": spec.unit,
                "source": spec.source,
                "hard_bounds": [spec.hard_min, spec.hard_max],
                "typical_range": [spec.typical_min, spec.typical_max],
            }
            for name, spec in sorted(CHANNEL_SPECS.items())
        }
    }


@mcp.tool()
def list_formulas() -> dict[str, Any]:
    """List computable formulas with their units and required arguments."""
    out = {}
    for name, fn in sorted(FORMULAS.items()):
        params = inspect.signature(fn).parameters
        out[name] = {
            "unit": UNITS.get(name),
            "arguments": [
                {
                    "name": p.name,
                    "type": "number",
                    "required": p.default is inspect.Parameter.empty,
                    "default": None if p.default is inspect.Parameter.empty else p.default,
                }
                for p in params.values()
            ],
        }
    return {"formulas": out, "count": len(out)}


@mcp.tool()
def compute(formula: str, arguments: dict[str, float]) -> dict[str, Any]:
    """Evaluate one named formula deterministically.

    Never estimate these values yourself — call this tool. Returns the value, its unit, and
    the exact arguments used so the answer is reproducible and auditable.
    """
    fn = FORMULAS.get(formula)
    if fn is None:
        raise ValueError(
            f"unknown formula {formula!r}; call list_formulas() for the {len(FORMULAS)} available"
        )
    clean = {k: float(v) for k, v in (arguments or {}).items()}
    try:
        result = fn(**clean)
    except ValueError as exc:
        # A formula that refuses its inputs (an impossible depth, say) must reach the client as a
        # readable refusal, not a traceback.
        raise ToolError(f"{formula}: {exc}") from exc
    if hasattr(result, "__dict__"):
        result = dict(result.__dict__)
    elif isinstance(result, tuple):
        result = list(result)
    return {"formula": formula, "arguments": clean, "value": result, "unit": UNITS.get(formula)}


@mcp.tool()
def qse_score_sample(
    channel: str,
    value: float,
    history: list[float] | None = None,
    sequence_number: int | None = None,
    last_sequence: int | None = None,
    redundant_values: list[float] | None = None,
    samples_in_window: int | None = None,
    window_seconds: float = 60.0,
    publish_interval_s: float = 1.0,
) -> dict[str, Any]:
    """Score one telemetry sample against the six-check quality gate.

    Covers physics bounds, sequence, redundancy drift, outliers, completeness and voting.
    A sample below the 0.95 floor is not actionable: describe the defect instead of
    interpreting the value. Pass the observation window you have; the tool keeps no history.
    """
    return model.score_sample(
        channel,
        value,
        history=history,
        sequence_number=sequence_number,
        last_sequence=last_sequence,
        redundant_values=redundant_values,
        samples_in_window=samples_in_window,
        window_seconds=window_seconds,
        publish_interval_s=publish_interval_s,
    )


@mcp.tool()
def check_safety_envelope(
    parameters: dict[str, float],
    action_type: str = "parameter_change",
    confidence: float = 1.0,
    kick_probability: float = 0.0,
    h2s_ppm: float = 0.0,
    rig_ecd_ppg: float | None = None,
    quality: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Run the pre-execution safety gate on a proposed parameter change.

    Returns passed, the specific violations, and hard_violation (the ask itself was
    physically unsafe). Alerts and advisories only face the H2S regulatory check, because
    they must always reach a human.
    """
    return model.check_envelope(
        parameters,
        action_type=action_type,
        confidence=confidence,
        kick_probability=kick_probability,
        h2s_ppm=h2s_ppm,
        rig_ecd_ppg=rig_ecd_ppg,
        quality=quality,
    )


@mcp.tool()
def route_autonomy(level: int, confidence: float) -> dict[str, Any]:
    """Map an autonomy level and confidence onto advisory-only, human-confirm or auto.

    This pack exposes no execution path: an auto_execute result means a human could approve
    the change, never that anything ran.
    """
    return model.route(level, confidence)


@mcp.tool()
def negotiate(
    proposals: list[dict[str, Any]],
    vetoes: list[dict[str, Any]] | None = None,
    window_ms: float = 2000.0,
    elapsed_ms: float = 0.0,
) -> dict[str, Any]:
    """Resolve conflicting proposals through the four-step negotiation.

    Proposals: agent_id, priority_tier, confidence, action_type, parameters. Vetoes:
    by_agent, priority_tier, target_proposal_id, reason, suggested_parameters. Returns the
    winner, every rejection, generated alternatives and the outcome.
    """
    return model.negotiate(proposals, vetoes, window_ms=window_ms, elapsed_ms=elapsed_ms)


@mcp.tool()
def well_control_assess(
    pit_gain_bbl: float = 0.0,
    flow_diff_gpm: float = 0.0,
    gas_units_pct: float = 0.0,
    pwd_residual_sigma: float = 0.0,
) -> dict[str, Any]:
    """Fuse kick signals into a probability, alert level and classification.

    Inputs: pit gain (bbl), flow-out minus flow-in (gpm), gas (%), and the PWD Kalman
    residual (sigma). Never derive an alert level by eye — this tool owns the thresholds.
    It detects and escalates; the Driller decides shut-in.

    An empty or all-zero payload is refused rather than fused: the signals default to 0.0,
    so a mistyped argument name would otherwise read as a confident all-clear.
    """
    try:
        return model.well_control_assess(
            pit_gain_bbl=pit_gain_bbl,
            flow_diff_gpm=flow_diff_gpm,
            gas_units_pct=gas_units_pct,
            pwd_residual_sigma=pwd_residual_sigma,
        )
    except ValueError as exc:
        raise ToolError(str(exc)) from exc


@mcp.tool()
def audit_append(entry: dict[str, Any]) -> dict[str, Any]:
    """Append a decision record to the tamper-evident audit trail.

    Include agent, tier, confidence, rejections, winner and approver. Each entry is chained
    to the previous one by hash so a silent edit is detectable.
    """
    path = _audit_path()
    previous = _last_hash()
    record = {
        "timestamp": datetime.now(UTC).isoformat(),
        "previous_hash": previous,
        "entry": entry,
    }
    blob = json.dumps(record, sort_keys=True, default=str).encode()
    record["entry_hash"] = hashlib.sha256(blob).hexdigest()
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, sort_keys=True, default=str) + "\n")
    return {"appended": True, "path": str(path), "entry_hash": record["entry_hash"]}


@mcp.tool()
def audit_trace(limit: int = 20) -> dict[str, Any]:
    """Read the most recent audit entries, oldest first."""
    path = _audit_path()
    if not path.exists():
        return {"entries": [], **_audit_location()}
    lines = [ln for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    return {
        **_audit_location(),
        "entries": [json.loads(ln) for ln in lines[-max(1, limit):]],
        "total": len(lines),
    }


def selftest() -> int:
    """Verify the install without starting a session: deps resolved, files intact, limits load.

    This is also the cheapest way to warm the uv cache before a first session
    (`uv run --script servers/advisory_core/main.py --selftest`), which avoids a slow cold
    start colliding with a client's MCP startup timeout.
    """
    root = model.plugin_root()
    checks: list[tuple[str, bool, str]] = []

    manifest = root / "plugin.json"
    checks.append(("plugin.json", manifest.exists(), str(manifest)))

    contracts = sorted((root / "src/agents").glob("*.yaml"))
    checks.append(("agent contracts", len(contracts) == 17, f"{len(contracts)} found"))

    skills = sorted((root / "skills").glob("*/SKILL.md"))
    checks.append(("skills", len(skills) == 10, f"{len(skills)} found"))

    checks.append(("formulas", len(FORMULAS) == 31, f"{len(FORMULAS)} available"))

    # Exercises the YAML policy load path, which is where a bad install fails first.
    try:
        validated = model.envelope_site_validated()
        checks.append(("policy limits load", True, f"site_validated={str(validated).lower()}"))
    except Exception as exc:  # noqa: BLE001 - the point is to report, not to raise
        checks.append(("policy limits load", False, str(exc)))

    failed = [name for name, ok, _ in checks if not ok]
    for name, ok, detail in checks:
        print(f"  [{'OK' if ok else 'FAIL'}] {name}: {detail}")
    print(f"\n{'selftest FAILED' if failed else 'selftest OK'} — "
          f"advisory-core {VERSION}, {len(FORMULAS)} formulas, plugin root {root}")
    return 1 if failed else 0


_CLI_TOOLS: dict[str, Any] = {
    "list_capabilities": list_capabilities,
    "list_channels": list_channels,
    "list_formulas": list_formulas,
    "compute": compute,
    "qse_score_sample": qse_score_sample,
    "check_safety_envelope": check_safety_envelope,
    "route_autonomy": route_autonomy,
    "negotiate": negotiate,
    "well_control_assess": well_control_assess,
    "audit_append": audit_append,
    "audit_trace": audit_trace,
}


def cli_call(tool: str, raw_args: str) -> int:
    """Run one tool without an MCP client, printing the same JSON the tool returns.

    An agent cannot obtain tools by starting a stdio MCP server itself — the process just
    blocks waiting for JSON-RPC on stdin. This gives a harness that has a shell but no MCP
    registration the same deterministic answer, through the same code path and the same
    refusals, instead of a qualitative guess.
    """
    fn = _CLI_TOOLS.get(tool)
    if fn is None:
        print(json.dumps({"error": f"unknown tool: {tool}", "available": sorted(_CLI_TOOLS)}), file=sys.stderr)
        return 2
    try:
        args = json.loads(raw_args) if raw_args.strip() else {}
    except json.JSONDecodeError as exc:
        print(json.dumps({"error": f"arguments are not valid JSON: {exc}"}), file=sys.stderr)
        return 2
    if not isinstance(args, dict):
        print(json.dumps({"error": "arguments must be a JSON object"}), file=sys.stderr)
        return 2
    try:
        result = fn(**args)
    except ToolError as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return 1
    except TypeError as exc:
        accepted = list(inspect.signature(fn).parameters)
        print(json.dumps({"error": f"bad arguments: {exc}", "accepted": accepted}), file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, default=str))
    return 0


def main() -> None:
    if "--selftest" in sys.argv:
        raise SystemExit(selftest())
    if "--list-tools" in sys.argv:
        print(json.dumps(sorted(_CLI_TOOLS), indent=2))
        return
    if "--call" in sys.argv:
        i = sys.argv.index("--call")
        if len(sys.argv) <= i + 1:
            print("usage: --call <tool> [json-args]", file=sys.stderr)
            raise SystemExit(2)
        raise SystemExit(cli_call(sys.argv[i + 1], sys.argv[i + 2] if len(sys.argv) > i + 2 else "{}"))
    mcp.run("stdio")


if __name__ == "__main__":
    main()
