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
GPM_PER_BBL = 42.0  # US gallons per barrel; converts gpm to bbl/min
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


@lru_cache(maxsize=1)
def agent_ids() -> frozenset[str]:
    """The agent ids declared by the packaged contracts in src/agents."""
    found: set[str] = set()
    root = plugin_root() / "src" / "agents"
    for path in sorted(root.glob("*.yaml")):
        data = _load(f"src/agents/{path.name}") or {}
        found.add(str(data.get("id") or data.get("name") or path.stem))
    return frozenset(found)


def safety_limits() -> dict[str, Any]:
    """Envelope limits from src/policies/safety-envelope.yaml."""
    return (_load("src/policies/safety-envelope.yaml") or {}).get("limits", {})


def calibration() -> dict[str, Any]:
    """The published defaults standing in for company-policy values, and what to replace them with."""
    return (_load("src/policies/safety-envelope.yaml") or {}).get("calibration", {}) or {}


def defaults_in_use() -> list[str]:
    """Keys whose current value is a default rather than a site answer."""
    return sorted((calibration().get("defaults") or {}).keys())


def calibration_note() -> str:
    return (
        "Values marked as defaults are industry averages, not site answers: "
        + ", ".join(defaults_in_use())
        + ". Update them from your well-control policy before site use."
    )


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
    unverified_checks: list[str] = []
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
    if samples_in_window is None:
        unverified_checks.append("completeness")
    if samples_in_window is not None:
        completeness = min(1.0, samples_in_window / expected)
        if completeness < INCOMPLETE_THRESHOLD:
            flags.append("INCOMPLETE")
        quality *= completeness

    quality = max(0.0, min(1.0, quality))
    if unverified_checks:
        flags.append("UNVERIFIED_CHECKS")
    return {
        "channel": channel,
        "unit": spec.unit,
        "quality_score": round(quality, 4),
        "flags": flags or (["OK"] if quality >= act_floor else ["BELOW_FLOOR"]),
        "ground_truth": ground_truth,
        # A perfect score from checks that never ran is not a clean bill of health: with no
        # history there is nothing to compare against, so the sample is not certifiable.
        "is_actionable": quality >= act_floor and not unverified_checks,
        "unverified_checks": unverified_checks,
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

_CHANNEL_TO_PARAM = {channel: param for param, channel in _PARAM_CHANNEL.items()}
_LIMIT_KEYS = frozenset(
    {"wob", "rpm", "standpipe_pressure", "torque", "ecd", "dls_per_100ft", "flow_rate", "mud_weight"}
)
_UNIT_SUFFIXES = ("_klbs", "_klbf", "_ppg", "_gpm", "_psi", "_ft_lbs", "_ft_lbf")


def canonical_parameter(name: str) -> str | None:
    """Resolve a proposed parameter to the key its limit is defined under.

    A safety gate that silently ignores a parameter it cannot name is worse than no gate: the
    channel id (weight_on_bit) and the unit-suffixed form (wob_klbf) must each reach the same
    limit as the bare parameter name.
    """
    key = name.strip().lower().replace(" ", "_")
    if key in ("mud_weight_ppg", "mw", "mw_ppg"):
        return "mud_weight"
    if key in _LIMIT_KEYS:
        return key
    if key in _CHANNEL_TO_PARAM:
        return _CHANNEL_TO_PARAM[key]
    for suffix in _UNIT_SUFFIXES:
        if key.endswith(suffix):
            base = key[: -len(suffix)]
            if base in _LIMIT_KEYS:
                return base
            if base in _CHANNEL_TO_PARAM:
                return _CHANNEL_TO_PARAM[base]
    return None


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

    # Normalise every proposed parameter name before any limit is compared, and keep track of what
    # could not be resolved: an unevaluable control parameter must not be certified as safe.
    resolved: dict[str, float] = {}
    unverified: list[str] = []
    for raw_name, raw_value in parameters.items():
        key = canonical_parameter(raw_name)
        # Resolvable but unlimited (flow_rate, say) is as unevaluable as unresolvable: the gate
        # would compare it against nothing and pass it.
        if key is None or key not in _LIMIT_KEYS:
            unverified.append(str(raw_name))
        else:
            resolved[key] = float(raw_value)
    parameters = resolved

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
            "unverified_parameters": unverified,
            "defaults_in_use": defaults_in_use(),
            "site_validated": envelope_site_validated(),
        }

    min_conf = float(prob.get("min_confidence_for_action", 0.75))
    if confidence < min_conf:
        violations.append(f"confidence {confidence:.2f} < floor {min_conf:.2f}")

    kick_ceiling = float(prob.get("max_kick_probability_for_autonomy", 0.60))
    # Inclusive: the ladder calls 0.60 a Well Control Alert, so the autonomy ceiling must bite at
    # exactly that point rather than one increment above it.
    if kick_probability >= kick_ceiling:
        violations.append(
            f"kick probability {kick_probability:.2f} exceeds autonomy ceiling {kick_ceiling:.2f}"
        )

    checks = [
        ("wob", float(equipment.get("max_wob_klbs", 40.0)), "WOB", "klbs"),
        ("rpm", float(equipment.get("max_rpm", 180)), "RPM", ""),
        ("standpipe_pressure", float(equipment.get("max_standpipe_pressure_psi", 4000.0)), "SPP", "psi"),
        ("torque", float(equipment.get("max_torque_ft_lbs", 15000.0)), "torque", "ft-lbs"),
        ("flow_rate", float(equipment.get("max_flow_rate_gpm", 1200.0)), "flow rate", "gpm"),
    ]
    for key, limit, label, unit in checks:
        asked = parameters.get(key)
        if asked is not None and asked > limit:
            violations.append(f"{label} {asked:.1f} > max {limit:.0f} {unit}".strip())
            hard = True

    # The mud weight window was applied to proposed ECD only, so a proposal of mud_weight 8.8 ppg
    # passed against a 9.0-14.5 ppg floor. Both are checked now.
    proposed_mw = parameters.get("mud_weight")
    mww_min = float(mww.get("min_ppg", 9.0))
    mww_max = float(mww.get("max_ppg", 14.5))
    if proposed_mw is not None and not (mww_min <= proposed_mw <= mww_max):
        violations.append(
            f"mud weight {proposed_mw:.2f} ppg outside MWW [{mww_min:.1f}, {mww_max:.1f}]"
        )
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

    if unverified:
        violations.append(
            "cannot evaluate " + ", ".join(sorted(unverified)) + ": no limit is defined for these "
            "parameter names, so the change is not certified"
        )

    return {
        "passed": not violations,
        "violations": violations,
        "hard_violation": hard,
        "unverified_parameters": unverified,
        "defaults_in_use": defaults_in_use(),
        "site_validated": envelope_site_validated(),
    }


# --- Routing ---------------------------------------------------------------


def route(level: int, confidence: float) -> dict[str, Any]:
    """Combine autonomy level with confidence. Mirrors the reference implementation's route(), except that this
    package exposes no execution path at all — the routing is reported, never applied."""
    if not 1 <= int(level) <= 5:
        raise ValueError(f"autonomy level must be 1..5; got {level}")
    if not 0.0 <= float(confidence) <= 1.0:
        raise ValueError(f"confidence must be 0..1; got {confidence}")

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

    # An id that is not in the roster is a typo or a different package; either way its tier means
    # nothing here, and a phantom safety agent would be trusted as if it existed.
    known_agents = agent_ids()
    if known_agents:
        claimed = {str(p.get("agent_id", "")) for p in proposals} | {str(v.get("by_agent", "")) for v in vetoes}
        unknown_agents = sorted(a for a in claimed if a not in known_agents)
        if unknown_agents:
            raise ValueError(
                "unknown agent id(s): " + ", ".join(unknown_agents)
                + " — not among the packaged contracts. Use the ids in src/agents so the tier a "
                "proposal claims can be checked against the contract that declares it."
            )

    # Tier and confidence are ordinal: a tier outside 1..4 or a confidence outside 0..1 does not
    # mean "unusual", it means the caller and the contract disagree about the scale.
    for label, item in [("proposal", p) for p in proposals] + [("veto", v) for v in vetoes]:
        tier = int(item.get("priority_tier", 4))
        if not 1 <= tier <= 4:
            raise ValueError(
                f"{label} priority_tier {tier} is outside 1..4 (1 = safety, 4 = optimisation)"
            )
        confidence = float(item.get("confidence", 0.0))
        if not 0.0 <= confidence <= 1.0:
            raise ValueError(f"{label} confidence {confidence} is outside 0..1")

    contenders = [p for p in proposals if p.get("action_type", "parameter_change") == "parameter_change"]

    by_id = {p.get("proposal_id", f"p{i}"): p for i, p in enumerate(contenders)}

    # A veto aimed at an id that does not exist is silently dropped, and the proposal it was meant
    # to block then wins unopposed. Refuse instead of certifying that consensus.
    unmatched = [
        v.get("target_proposal_id") for v in vetoes
        if v.get("target_proposal_id") not in by_id
    ]
    if unmatched:
        raise ValueError(
            "veto target_proposal_id not found in the proposals: "
            + ", ".join(repr(u) for u in unmatched)
            + f" (known ids: {sorted(by_id)}). A veto that cannot be matched is ignored and the "
            "proposal it targets would win, so the round is refused rather than resolved."
        )
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

    # negotiate is callable on its own, so it cannot assume the caller ran the envelope first. A
    # winner that breaches a hard limit would otherwise be returned as CONSENSUS.
    if winner is not None and winner.get("parameters"):
        try:
            verdict = check_envelope(dict(winner["parameters"]), action_type="parameter_change")
        except TypeError:
            verdict = check_envelope(dict(winner["parameters"]))
        if verdict.get("hard_violation"):
            raise ValueError(
                "the winning proposal breaches the safety envelope: "
                + "; ".join(verdict.get("violations", []))
                + f" (proposed by {winner.get('agent_id')}). A result that would breach a hard "
                "limit is not a resolution, so the round is refused."
            )

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
    flow_check_pumps_off: bool = False,
    hole_diameter_in: float | None = None,
    pipe_od_in: float | None = None,
    kick_tolerance_volume_bbl: float | None = None,
) -> dict[str, Any]:
    """Fuse the three kick signals into a probability, alert level and classification.

    Independent-signal fusion (Well Control Monitoring specification 5.2, Dempster-Shafer form): each signal is mapped
    to a mass, combined as 1 - prod(1 - m). Thresholds come from the packaged contract.

    An empty payload is refused rather than fused. All four signals default to 0.0, so a caller that mistypes a
    parameter name would otherwise receive a confident "Normal" on a well that is flowing.
    """
    supplied = {
        "pit_gain_bbl": pit_gain_bbl,
        "flow_diff_gpm": flow_diff_gpm,
        "gas_units_pct": gas_units_pct,
        "pwd_residual_sigma": pwd_residual_sigma,
    }
    # A positive flow check with pumps off is evidence in its own right, so it does not need a
    # channel reading alongside it.
    if not flow_check_pumps_off and not any(value != 0.0 for value in supplied.values()):
        raise ValueError(
            "well_control_assess needs at least one kick signal: pit_gain_bbl, flow_diff_gpm, "
            "gas_units_pct or pwd_residual_sigma. All four were zero or absent. A well with no "
            "readings is not evidence of a normal well, so no verdict is produced."
        )

    if not 0.0 <= gas_units_pct <= 100.0:
        raise ValueError(
            f"gas_units_pct {gas_units_pct} is not a physical reading: gas is a percentage of the "
            "return flow and must lie in [0, 100]. Refusing rather than scoring an impossible sample."
        )

    th = well_control_thresholds()
    kp = th.get("kick_probability", _WC_DEFAULT["kick_probability"])
    pg = th.get("pit_gain", _WC_DEFAULT["pit_gain"])
    background = float(th.get("background_gas_pct", 0.5))

    # Each mass is a probability of "this signal is present", so it is floored at 0. Negative
    # signals (a loss, or flow-in exceeding flow-out) carry no gain mass; they are handled as
    # losses below. Without the floor a loss produced a negative probability.
    m1 = min(max(pwd_residual_sigma / 3.0 * 0.90, 0.0), 0.90)
    m2 = min(max(pit_gain_bbl / 5.0 * 0.95, 0.0), 0.95)
    # Gas below the well's background is background, not evidence: the 0.5% figure is a subtraction,
    # not only a full-scale point. Without this, 0.4% gas carried a mass of 0.11.
    gas_excess = max(gas_units_pct - background, 0.0)
    m3_gas = min(gas_excess / (5.0 * background) * 0.70, 0.70) if background > 0 else 0.0
    m3_flow = min(max(flow_diff_gpm, 0.0) / 10.0 * 0.80, 0.80)
    # Gas and flow are independent indicators: agreement is corroboration, so they combine as a
    # noisy-OR rather than as max(). Under max(), 2% gas with +5 gpm scored exactly as gas alone.
    m3 = 1.0 - (1.0 - m3_gas) * (1.0 - m3_flow)
    probability = min(max(1.0 - (1.0 - m1) * (1.0 - m2) * (1.0 - m3), 0.0), 1.0)

    # A single signal must not carry the highest consequence on its own: PWD is capped at Alert and
    # gas at Advisory, so an Emergency needs corroboration or an explicit volume override. Pit totals
    # land on exact tenths, so the volume overrides compare with >= rather than >.
    gas_only = m3_gas > 0 and m2 == 0.0 and m3_flow == 0.0
    pwd_only = m1 > 0 and m2 == 0.0 and m3 == 0.0
    if pwd_only:
        probability = min(probability, float(kp["well_control_alert"]) - 1e-9)
    if gas_only:
        probability = min(probability, float(kp["advisory"]) + (float(kp["well_control_alert"]) - float(kp["advisory"])) / 2)

    if flow_check_pumps_off:
        # Evidence outranks the score: a positive flow check with pumps off is a shut-in proposal
        # whatever the fused number says. The score may raise attention early; it may never lower a
        # level the evidence sets.
        level = 4
    elif probability >= float(kp["emergency"]) or pit_gain_bbl >= float(pg["emergency_bbl"]):
        level = 4
    elif probability >= float(kp["well_control_alert"]) or pit_gain_bbl >= float(pg["advisory_bbl"]):
        level = 3
    elif probability >= float(kp["advisory"]):
        level = 2
    elif probability >= float(kp["monitor"]):
        level = 1
    else:
        level = 0

    # Losses: the packaged contract defines no loss threshold. Rather than leave every loss at one
    # level, a ladder is authored in the policy and marked authored_limits, so severity escalates
    # and the provenance is visible. It stops at 3: a well losing returns is not shut in.
    loss_cfg = safety_limits().get("losses", {}) or {}
    loss_advisory_bbl = float(loss_cfg.get("advisory_bbl", 2.0))
    loss_alert_bbl = float(loss_cfg.get("alert_bbl", 5.0))
    pit_loss_bbl = max(-pit_gain_bbl, 0.0)
    # A flow deficit is a loss while the pit can still read steady: nulled, being topped up, or
    # simply ahead of the trip-tank measurement. Convert it onto the same scale rather than letting
    # a -200 gpm loss read as Monitor. AUTHORED basis: 42 US gal to the barrel, over one minute.
    gpm_per_bbl = float(loss_cfg.get("flow_equivalent_gpm_per_bbl", GPM_PER_BBL))
    flow_loss_bbl = max(-flow_diff_gpm, 0.0) / gpm_per_bbl
    loss_magnitude = max(pit_loss_bbl, flow_loss_bbl)
    loss_basis = (
        "both" if pit_loss_bbl > 0 and flow_loss_bbl > 0
        else "pit_volume" if pit_loss_bbl > 0
        else "flow_equivalent" if flow_loss_bbl > 0
        else "none"
    )
    losses = pit_gain_bbl < 0.0 or flow_diff_gpm < 0.0
    escalated_for_losses = False
    # Loss classes follow the industry vocabulary. The bbl/hr boundaries are AUTHORED: the published
    # classes agree that seepage is under ~10 bbl/hr and disagree on everything above it.
    loss_rate_bbl_hr = max(-flow_diff_gpm, 0.0) * 60.0 / gpm_per_bbl
    seepage_max = float(loss_cfg.get("seepage_max_bbl_hr", 10.0))
    partial_max = float(loss_cfg.get("partial_max_bbl_hr", 50.0))
    if losses and not flow_check_pumps_off:
        target = 3 if loss_magnitude >= loss_alert_bbl else (2 if loss_magnitude >= loss_advisory_bbl else 1)
        if level < target:
            level = target
            escalated_for_losses = True
        if loss_rate_bbl_hr >= partial_max:
            loss_class = "severe"
        elif loss_rate_bbl_hr >= seepage_max or loss_magnitude >= loss_advisory_bbl:
            loss_class = "partial"
        else:
            loss_class = "seepage"
    else:
        loss_class = "none"

    # Losses plus any sign of influx is the underground-flow / loss-induced-kick signature. Neither
    # signal alone justifies it, and treating the pair as a plain loss is how it gets missed.
    loss_then_influx = losses and (max(gas_units_pct - background, 0.0) > 0 or flow_diff_gpm > 0)
    if loss_then_influx:
        level = 4

    # Fixed barrel thresholds are permissive in small hole: 5 bbl is 18 ft of influx in 17.5" hole
    # but 109 ft in 8.5". When the caller supplies hole geometry and the section's kick tolerance,
    # the cap becomes volumetric. The fraction is an industry average from the calibration block and
    # is reported as a default, not a site answer.
    cap_cfg = (calibration().get("defaults") or {}).get("pit_gain.kick_tolerance_fraction", {}) or {}
    kt_fraction = float(cap_cfg.get("value", 0.5))
    annular_capacity_bbl_ft: float | None = None
    influx_height_ft: float | None = None
    volumetric_cap_bbl: float | None = None
    if hole_diameter_in and pipe_od_in and hole_diameter_in > pipe_od_in:
        annular_capacity_bbl_ft = (hole_diameter_in**2 - pipe_od_in**2) / 1029.4
        if annular_capacity_bbl_ft > 0:
            influx_height_ft = pit_gain_bbl / annular_capacity_bbl_ft
    if kick_tolerance_volume_bbl and kick_tolerance_volume_bbl > 0:
        volumetric_cap_bbl = kt_fraction * kick_tolerance_volume_bbl
        if pit_gain_bbl >= volumetric_cap_bbl:
            level = 4

    if flow_check_pumps_off:
        classification = "KICK_CONFIRMED"
    elif loss_then_influx:
        classification = "UNDERGROUND_FLOW_SUSPECTED"
    elif pit_gain_bbl > 0.5 and flow_diff_gpm > 0:
        classification = "GAS_KICK" if gas_units_pct > background else "WATER_KICK"
    elif losses:
        # Any negative gain is a loss; the size decides the level, not the classification.
        classification = "LOST_CIRCULATION"
    else:
        classification = "NORMAL"

    # Invariant: an escalation is never labelled Normal. Gas with no flow or pit evidence is a
    # gas influx that the supplied channels cannot confirm, not a normal well.
    if level >= 3 and classification == "NORMAL":
        classification = "GAS_KICK" if gas_units_pct > background else "UNCONFIRMED_INFLUX"

    result_notes: list[str] = []
    if losses:
        basis_text = {
            "both": "pit volume and a flow deficit",
            "pit_volume": "pit volume",
            "flow_equivalent": "a flow deficit",
        }.get(loss_basis, "a negative signal")
        note = (
            f"Losses detected ({basis_text}). The packaged contract defines no loss threshold, so an "
            f"authored ladder is applied: this is level {level} ({_ALERT_NAMES.get(level, 'unknown')}), "
            "not a normal well."
        )
        if loss_basis in ("flow_equivalent", "both"):
            note += (
                f" The flow deficit was converted to an equivalent {flow_loss_bbl:.1f} bbl over one "
                f"minute ({gpm_per_bbl:.0f} gal/bbl): that is an equivalent, not a measured volume."
            )
        note += " Treat as lost circulation and verify against the drilling programme."
        result_notes.append(note)
    if level >= 3 and classification == "UNCONFIRMED_INFLUX":
        result_notes.append(
            "Escalation came from gas alone; no flow differential or pit gain was supplied to "
            "confirm an influx."
        )

    return {
        # The fused mass is a deterministic score, not a calibrated probability: renamed so nobody
        # reads 0.60 as "60% likely". kick_probability is kept as a deprecated alias.
        "kick_score": round(probability, 4),
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
        "losses_detected": losses,
        "loss_basis": loss_basis,
        "loss_class": loss_class,
        "influx_height_ft": round(influx_height_ft, 1) if influx_height_ft is not None else None,
        "annular_capacity_bbl_ft": (
            round(annular_capacity_bbl_ft, 4) if annular_capacity_bbl_ft is not None else None
        ),
        "volumetric_cap_bbl": round(volumetric_cap_bbl, 2) if volumetric_cap_bbl is not None else None,
        "defaults_in_use": defaults_in_use(),
        "calibration_note": calibration_note(),
        "loss_equivalent_bbl": round(loss_magnitude, 2),
        "notes": result_notes,
        "authority": "The Driller and Drilling Supervisor decide shut-in. This tool detects and escalates.",
        "thresholds_used": {
            "monitor": kp["monitor"], "advisory": kp["advisory"],
            "well_control_alert": kp["well_control_alert"], "emergency": kp["emergency"],
            "pit_gain_advisory_bbl": pg["advisory_bbl"], "pit_gain_emergency_bbl": pg["emergency_bbl"],
            "background_gas_pct": background,
            "loss_advisory_bbl": loss_advisory_bbl, "loss_alert_bbl": loss_alert_bbl,
        },
    }
