"""Deterministic advisory logic: quality gate, safety envelope, routing, negotiation,
well-control fusion.

Ported from the reference implementation (quality_score_engine.py, safety_envelope.py, autonomy_manager.py,
negotiation_protocol.py, priority_hierarchy.py, well_control_agent.py). Policy numbers are
read from the packaged contracts in ``src/policies`` and ``src/agents`` so the tools and the
skills cite one source.

One deliberate departure: the reference implementation keeps rolling per-channel state in-process. These tools are
stateless, so the caller supplies the observation window (history, recent timestamps,
sequence number). Same arithmetic, no hidden state to go stale between calls.
"""

from __future__ import annotations

import os
import statistics
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from .channel_specs import CHANNEL_SPECS

# Channel ids follow the reference implementation's Channel enum values. A few parameter names differ (a proposal
# asks for "wob"; the channel is "weight_on_bit"), so accept the common aliases and resolve
# them to the canonical id.
CHANNEL_ALIASES = {
    "wob": "weight_on_bit",
    "spp": "standpipe_pressure",
    "flow_in": "flow_rate",
}

# Quality-engine constants, transcribed from the reference implementation data/quality_score_engine.py.
COMPLETENESS_WINDOW_S = 60.0
OUTLIER_Z_THRESHOLD = 3.5
DOWNHOLE_NOMINAL_PERIOD_S = 30.0
OUT_OF_SEQUENCE_PENALTY = 0.4
OUTLIER_PENALTY = 0.5
DRIFT_PENALTY = 0.5
DRIFT_REL_THRESHOLD = 0.10
INCOMPLETE_THRESHOLD = 0.9

# Well-control thresholds fall back to the packaged contract if it cannot be read.
_WC_DEFAULT = {
    "kick_probability": {"monitor": 0.20, "advisory": 0.40, "well_control_alert": 0.60, "emergency": 0.85},
    "pit_gain": {"advisory_bbl": 2.0, "emergency_bbl": 5.0},
    "pit_baseline_ema_alpha": 0.02,
    "background_gas_pct": 0.5,
}
_ROUTING_DEFAULT = {"auto_execute": 0.85, "human_confirm": 0.70}
_ALERT_NAMES = {
    0: "Normal",
    1: "Monitor",
    2: "Advisory",
    3: "Well Control Alert",
    4: "Emergency Shut-In Proposal",
}


def plugin_root() -> Path:
    """Resolve the package root. Clients set PLUGIN_ROOT; the file layout is the fallback."""
    env = os.environ.get("PLUGIN_ROOT")
    return Path(env).resolve() if env else Path(__file__).resolve().parents[2]


@lru_cache(maxsize=32)
def _load(rel: str) -> dict[str, Any]:
    path = plugin_root() / rel
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def safety_limits() -> dict[str, Any]:
    """Envelope limits from src/policies/safety-envelope.yaml."""
    return (_load("src/policies/safety-envelope.yaml") or {}).get("limits", {})


def envelope_site_validated() -> bool:
    return bool((_load("src/policies/safety-envelope.yaml") or {}).get("site_validated", False))


def well_control_thresholds() -> dict[str, Any]:
    return (_load("src/agents/well-control-monitoring-agent.yaml") or {}).get(
        "thresholds", _WC_DEFAULT
    ) or _WC_DEFAULT


def routing_thresholds() -> dict[str, float]:
    policy = _load("src/policies/veto-matrix.yaml") or {}
    return policy.get("routing_thresholds", _ROUTING_DEFAULT) or _ROUTING_DEFAULT


def tier_table() -> dict[int, dict[str, Any]]:
    policy = _load("src/policies/veto-matrix.yaml") or {}
    return {int(t["tier"]): t for t in policy.get("tiers", [])}


# --- Quality gate ----------------------------------------------------------


def _is_outlier(value: float, history: list[float], typical_range: float) -> bool:
    median = statistics.median(history)
    deviations = [abs(v - median) for v in history]
    mad = statistics.median(deviations)
    if mad > 1e-9:
        return 0.6745 * abs(value - median) / mad > OUTLIER_Z_THRESHOLD
    stdev = statistics.pstdev(history)
    if stdev > 1e-9:
        return abs(value - median) / stdev > OUTLIER_Z_THRESHOLD
    return typical_range > 0 and abs(value - median) > 0.10 * typical_range


def score_sample(
    channel: str,
    value: float,
    *,
    history: list[float] | None = None,
    sequence_number: int | None = None,
    last_sequence: int | None = None,
    redundant_values: list[float] | None = None,
    samples_in_window: int | None = None,
    window_seconds: float = COMPLETENESS_WINDOW_S,
    publish_interval_s: float = 1.0,
) -> dict[str, Any]:
    """Six-check quality score for one sample.

    Returns the score, the flags that reduced it, the chosen ground-truth value, and whether
    it clears the act floor. A sample below the floor is not actionable: describe the defect,
    do not interpret the value.
    """
    channel = CHANNEL_ALIASES.get(channel, channel)
    spec = CHANNEL_SPECS.get(channel)
    if spec is None:
        raise ValueError(f"unknown channel {channel!r}; call list_channels()")

    floors = safety_limits().get("probabilistic", {})
    act_floor = float(floors.get("min_data_quality_to_act", 0.95))

    flags: list[str] = []
    quality = 1.0
    history = list(history or [])
    ground_truth = value

    # 3. Physics validation (hard bounds) — an impossible value scores zero.
    physically_valid = spec.hard_min <= value <= spec.hard_max
    if not physically_valid:
        flags.append("PHYSICALLY_INVALID")
        quality = 0.0

    # 1. Sequence validation.
    if last_sequence is not None and sequence_number is not None and sequence_number < last_sequence:
        flags.append("OUT_OF_SEQUENCE")
        quality *= OUT_OF_SEQUENCE_PENALTY

    # 2. Drift (redundant sensors disagree beyond a fraction of the typical range).
    if redundant_values and len(redundant_values) > 1 and spec.typical_range > 0:
        spread = max(redundant_values) - min(redundant_values)
        if spread / spec.typical_range > DRIFT_REL_THRESHOLD:
            flags.append("DRIFT_DETECTED")
            quality *= DRIFT_PENALTY

    # 5. Outlier detection (modified z-score against the supplied history).
    if physically_valid and len(history) >= 3:
        if _is_outlier(value, history, spec.typical_range):
            flags.append("OUTLIER")
            quality *= OUTLIER_PENALTY
            ground_truth = statistics.median(history)

    # 4. Completeness over the window.
    period = publish_interval_s if spec.source == "surface" else DOWNHOLE_NOMINAL_PERIOD_S
    period = max(period, 1e-3)
    expected = max(1, round(min(window_seconds, max(window_seconds, period)) / period))
    if samples_in_window is not None:
        completeness = min(1.0, samples_in_window / expected)
        if completeness < INCOMPLETE_THRESHOLD:
            flags.append("INCOMPLETE")
        quality *= completeness

    quality = max(0.0, min(1.0, quality))
    return {
        "channel": channel,
        "unit": spec.unit,
        "quality_score": round(quality, 4),
        "flags": flags or ["OK"],
        "ground_truth": ground_truth,
        "is_actionable": quality > act_floor,
        "act_floor": act_floor,
        "expected_samples": expected,
        "hard_bounds": [spec.hard_min, spec.hard_max],
    }


# --- Safety envelope -------------------------------------------------------


_PARAM_CHANNEL = {
    "wob": "weight_on_bit",
    "rpm": "rpm",
    "flow_rate": "flow_rate",
    "torque": "torque",
    "ecd": "ecd",
    "standpipe_pressure": "standpipe_pressure",
}


def check_envelope(
    parameters: dict[str, float],
    *,
    action_type: str = "parameter_change",
    confidence: float = 1.0,
    kick_probability: float = 0.0,
    h2s_ppm: float = 0.0,
    rig_ecd_ppg: float | None = None,
    quality: dict[str, float] | None = None,
) -> dict[str, Any]:
    """The L3 pre-execution gate. Pure, deterministic, and not overridable.

    Returns passed / violations / hard_violation. ``hard_violation`` means the ask itself was
    physically unsafe (equipment limits, mud-weight window, DLS) — not merely unproven.
    """
    limits = safety_limits()
    equipment = limits.get("equipment", {})
    mww = limits.get("mud_weight_window", {})
    wellbore = limits.get("wellbore", {})
    regulatory = limits.get("regulatory", {})
    prob = limits.get("probabilistic", {})
    quality = quality or {}

    violations: list[str] = []
    hard = False

    h2s_alarm = float(regulatory.get("h2s_alarm_ppm", 10.0))
    if h2s_ppm >= h2s_alarm:
        violations.append(f"H2S {h2s_ppm:.1f} ppm >= alarm {h2s_alarm:.1f} ppm")

    # Alerts and advisories must always reach a human: only the regulatory gate applies.
    if action_type != "parameter_change":
        return {
            "passed": not violations,
            "violations": violations,
            "hard_violation": False,
            "site_validated": envelope_site_validated(),
        }

    min_conf = float(prob.get("min_confidence_for_action", 0.75))
    if confidence < min_conf:
        violations.append(f"confidence {confidence:.2f} < floor {min_conf:.2f}")

    kick_ceiling = float(prob.get("max_kick_probability_for_autonomy", 0.60))
    if kick_probability > kick_ceiling:
        violations.append(
            f"kick probability {kick_probability:.2f} exceeds autonomy ceiling {kick_ceiling:.2f}"
        )

    checks = [
        ("wob", float(equipment.get("max_wob_klbs", 40.0)), "WOB", "klbs"),
        ("rpm", float(equipment.get("max_rpm", 180)), "RPM", ""),
        ("standpipe_pressure", float(equipment.get("max_standpipe_pressure_psi", 4000.0)), "SPP", "psi"),
        ("torque", float(equipment.get("max_torque_ft_lbs", 15000.0)), "torque", "ft-lbs"),
    ]
    for key, limit, label, unit in checks:
        asked = parameters.get(key)
        if asked is not None and asked > limit:
            violations.append(f"{label} {asked:.1f} > max {limit:.0f} {unit}".strip())
            hard = True

    ecd = parameters.get("ecd", rig_ecd_ppg)
    emw_min = float(mww.get("min_ppg", 9.0))
    emw_max = float(mww.get("max_ppg", 14.5))
    if ecd is not None and not (emw_min <= ecd <= emw_max):
        violations.append(f"ECD {ecd:.2f} ppg outside MWW [{emw_min:.1f}, {emw_max:.1f}]")
        hard = True

    dls = parameters.get("dls_per_100ft")
    max_dls = float(wellbore.get("max_dls_per_100ft", 5.0))
    if dls is not None and dls > max_dls:
        violations.append(f"DLS {dls:.2f} > max {max_dls:.2f} deg/100ft")
        hard = True

    min_quality = float(prob.get("min_data_quality_to_act", 0.95))
    for key in parameters:
        channel = _PARAM_CHANNEL.get(key)
        if channel is None:
            continue
        # Accept either the canonical channel id or the proposal parameter name.
        sample_quality = quality.get(channel, quality.get(key))
        if sample_quality is not None and sample_quality < min_quality:
            violations.append(
                f"data quality for {key} ({sample_quality:.2f}) < floor {min_quality:.2f}"
            )

    return {
        "passed": not violations,
        "violations": violations,
        "hard_violation": hard,
        "site_validated": envelope_site_validated(),
    }


# --- Routing ---------------------------------------------------------------


def route(level: int, confidence: float) -> dict[str, Any]:
    """Combine autonomy level with confidence. Mirrors the reference implementation's route(), except that this
    package exposes no execution path at all — the routing is reported, never applied."""
    th = routing_thresholds()
    auto = float(th.get("auto_execute", 0.85))
    confirm = float(th.get("human_confirm", 0.70))

    if confidence < confirm:
        routing = "advisory_only"
    elif level <= 1:
        routing = "human_confirm"
    elif confidence >= auto:
        routing = "auto_execute"
    else:
        routing = "human_confirm"

    return {
        "level": level,
        "confidence": round(confidence, 4),
        "routing": routing,
        "pack_executes": False,
        "note": (
            "the reference implementation would auto-execute this at the reported level and confidence. This pack "
            "never executes: treat auto_execute as 'a human could approve a parameter change'."
        )
        if routing == "auto_execute"
        else "Human confirmation required." if routing == "human_confirm"
        else "Advisory only: confidence is below the human-confirm floor.",
    }


# --- Negotiation -----------------------------------------------------------


def negotiate(
    proposals: list[dict[str, Any]],
    vetoes: list[dict[str, Any]] | None = None,
    *,
    window_ms: float = 2000.0,
    elapsed_ms: float = 0.0,
) -> dict[str, Any]:
    """Four-step negotiation among proposals.

    ``proposals``: [{agent_id, priority_tier, confidence, action_type, parameters}]
    ``vetoes``:    [{by_agent, priority_tier, target_proposal_id, reason, suggested_parameters}]

    Steps: publication (parameter changes contend) -> constraint evaluation (vetoes) ->
    alternative generation (a veto carrying safer parameters re-enters) -> consensus by tier
    then confidence. Outcomes: CONSENSUS, SAFETY_VETO, DEADLOCK, TIMEOUT.
    """
    vetoes = vetoes or []
    contenders = [p for p in proposals if p.get("action_type", "parameter_change") == "parameter_change"]

    by_id = {p.get("proposal_id", f"p{i}"): p for i, p in enumerate(contenders)}
    rejections: list[dict[str, Any]] = []
    safety_veto = False

    def _apply(target_id: str, params: dict[str, float]) -> list[dict[str, Any]]:
        nonlocal safety_veto
        hits = []
        for v in vetoes:
            if v.get("target_proposal_id") != target_id:
                continue
            hits.append(v)
            if int(v.get("priority_tier", 0)) == 1:
                safety_veto = True
            rejections.append({
                "proposal_id": target_id,
                "by_agent": v.get("by_agent"),
                "reason": v.get("reason", ""),
                "source": f"veto:{v.get('by_agent')}",
            })
        return hits

    surviving: list[dict[str, Any]] = []
    for pid, p in by_id.items():
        hits = _apply(pid, p.get("parameters", {}))
        if not hits:
            surviving.append(p)

    # Step 3: a veto that carries safer parameters re-enters as an alternative.
    alternatives: list[dict[str, Any]] = []
    for v in vetoes:
        suggested = v.get("suggested_parameters")
        if not suggested:
            continue
        candidate = {
            "proposal_id": f"alt-{v.get('target_proposal_id')}",
            "agent_id": v.get("by_agent"),
            "priority_tier": int(v.get("priority_tier", 4)),
            "confidence": 0.9,
            "action_type": "parameter_change",
            "parameters": suggested,
            "rationale": f"Alternative to {v.get('target_proposal_id')}: {v.get('reason', '')}",
            "_alternative": True,
        }
        if any(x.get("target_proposal_id") == candidate["proposal_id"] for x in vetoes):
            continue
        alternatives.append(candidate)
    surviving.extend(alternatives)

    winner = min(
        surviving, key=lambda p: (int(p.get("priority_tier", 4)), -float(p.get("confidence", 0.0)))
    ) if surviving else None

    if elapsed_ms >= window_ms:
        outcome = "TIMEOUT"
        winner = None
        rationale = f"Negotiation exceeded the {window_ms:.0f} ms window."
    elif winner is not None:
        outcome = "CONSENSUS"
        rationale = (
            f"{winner.get('agent_id')} won at tier {int(winner.get('priority_tier', 4))} "
            f"(confidence {float(winner.get('confidence', 0.0)):.2f})."
        )
    elif not contenders:
        outcome = "CONSENSUS"
        rationale = "No contenders."
    elif safety_veto:
        outcome = "SAFETY_VETO"
        rationale = "Tier-1 safety veto: all parameter changes frozen."
    else:
        outcome = "DEADLOCK"
        rationale = "All contenders rejected; no alternative survived."

    return {
        "outcome": outcome,
        "winner": winner,
        "rationale": rationale,
        "rejections": rejections,
        "alternatives": [{k: v for k, v in a.items() if k != "_alternative"} for a in alternatives],
        "contenders": len(contenders),
        "window_ms": window_ms,
    }


# --- Well control ----------------------------------------------------------


def well_control_assess(
    *,
    pit_gain_bbl: float = 0.0,
    flow_diff_gpm: float = 0.0,
    gas_units_pct: float = 0.0,
    pwd_residual_sigma: float = 0.0,
) -> dict[str, Any]:
    """Fuse the three kick signals into a probability, alert level and classification.

    Independent-signal fusion (Well Control Monitoring specification 5.2, Dempster-Shafer form): each signal is mapped
    to a mass, combined as 1 - prod(1 - m). Thresholds come from the packaged contract.
    """
    th = well_control_thresholds()
    kp = th.get("kick_probability", _WC_DEFAULT["kick_probability"])
    pg = th.get("pit_gain", _WC_DEFAULT["pit_gain"])
    background = float(th.get("background_gas_pct", 0.5))

    m1 = min(pwd_residual_sigma / 3.0 * 0.90, 0.90)
    m2 = min(pit_gain_bbl / 5.0 * 0.95, 0.95)
    m3_gas = min(gas_units_pct / (5.0 * background) * 0.70, 0.70)
    m3_flow = min(max(0.0, flow_diff_gpm) / 10.0 * 0.80, 0.80)
    m3 = max(m3_gas, m3_flow)
    probability = 1.0 - (1.0 - m1) * (1.0 - m2) * (1.0 - m3)

    if probability >= float(kp["emergency"]) or pit_gain_bbl > float(pg["emergency_bbl"]):
        level = 4
    elif probability >= float(kp["well_control_alert"]) or pit_gain_bbl > float(pg["advisory_bbl"]):
        level = 3
    elif probability >= float(kp["advisory"]):
        level = 2
    elif probability >= float(kp["monitor"]):
        level = 1
    else:
        level = 0

    if pit_gain_bbl > 0.5 and flow_diff_gpm > 0:
        classification = "GAS_KICK" if gas_units_pct > background else "WATER_KICK"
    elif flow_diff_gpm < -5.0 or pit_gain_bbl < -1.0:
        classification = "LOST_CIRCULATION"
    else:
        classification = "NORMAL"

    return {
        "kick_probability": round(probability, 4),
        "alert_level": level,
        "alert_name": _ALERT_NAMES[level],
        "classification": classification,
        "mass": {"pwd_residual": round(m1, 4), "pit_gain": round(m2, 4), "gas_or_flow": round(m3, 4)},
        "basis": (
            "Deterministic fusion of three independent signal masses (PWD residual, pit gain, gas or "
            "flow). Not a trained model and not a calibrated probability: do not describe it as a "
            "confidence level or an ML score."
        ),
        "regulatory_notification_required": level >= 3,
        "authority": "The Driller and Drilling Supervisor decide shut-in. This tool detects and escalates.",
        "thresholds_used": {
            "monitor": kp["monitor"], "advisory": kp["advisory"],
            "well_control_alert": kp["well_control_alert"], "emergency": kp["emergency"],
            "pit_gain_advisory_bbl": pg["advisory_bbl"], "pit_gain_emergency_bbl": pg["emergency_bbl"],
            "background_gas_pct": background,
        },
    }
