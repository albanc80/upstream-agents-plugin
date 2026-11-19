"""Parity and behaviour tests for the advisory spine.

The first block asserts the formulas against the reference implementation's own hand-calculated expectations
(``tests/unit/test_physics_models.py``). If these fail, the plugin and the platform
disagree and the plugin is wrong by definition.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "servers"))

from advisory_core import formulas as pm  # noqa: E402
from advisory_core import model  # noqa: E402


# --- parity with the reference implementation's physics assertions ---------------------------------


def test_pressure_and_gradient() -> None:
    assert pm.pressure_gradient_psi_per_ft(10.0) == pytest.approx(0.52)
    assert pm.hydrostatic_pressure_psi(10.0, 10_000.0) == pytest.approx(5200.0)
    assert pm.mud_weight_from_pressure_ppg(5200.0, 10_000.0) == pytest.approx(10.0)
    assert pm.mud_weight_from_pressure_ppg(100.0, 0.0) == 0.0


def test_buoyancy_factor() -> None:
    assert pm.buoyancy_factor(10.0) == pytest.approx(1.0 - 10.0 / 65.5)


def test_ecd() -> None:
    assert pm.equivalent_circulating_density_ppg(12.0, 200.0, 10_000.0) == pytest.approx(
        12.3846, abs=1e-3
    )


def test_maasp() -> None:
    assert pm.maasp_psi(14.5, 12.0, 5000.0) == pytest.approx(650.0)


def test_kill_sheet_values() -> None:
    assert pm.kill_mud_weight_ppg(12.0, 260.0, 10_000.0) == pytest.approx(12.5)
    assert pm.formation_pressure_psi(260.0, 12.0, 10_000.0) == pytest.approx(6500.0)
    assert pm.initial_circulating_pressure_psi(260.0, 500.0) == pytest.approx(760.0)
    assert pm.final_circulating_pressure_psi(500.0, 12.5, 12.0) == pytest.approx(520.833, abs=1e-2)


def test_mud_weight_window() -> None:
    assert pm.mud_weight_window_ppg(9.0, 14.5) == (9.0, 14.5)
    assert pm.is_within_mud_weight_window(12.0, 9.0, 14.5) is True
    assert pm.is_within_mud_weight_window(15.0, 9.0, 14.5) is False


def test_capacities_and_annular_velocity() -> None:
    assert pm.pipe_capacity_bbl_per_ft(5.0) == pytest.approx(25.0 / 1029.4)
    assert pm.annular_capacity_bbl_per_ft(8.5, 5.0) == pytest.approx(47.25 / 1029.4)
    cap = pm.annular_capacity_bbl_per_ft(8.5, 5.0)
    assert pm.annular_velocity_ft_per_min(5.0, cap) == pytest.approx(5.0 / cap)


def test_teale_mse() -> None:
    area = math.pi / 4.0 * 8.5**2
    expected = 25.0 * 1000.0 / area + 480.0 * 120.0 * 8000.0 / (area * 60.0)
    assert pm.teale_mse_psi(25.0, 120.0, 8000.0, 8.5, 60.0) == pytest.approx(expected)


def test_dogleg_and_min_curvature() -> None:
    assert pm.dogleg_severity_deg_per_100ft(0.0, 0.0, 10.0, 0.0, 100.0) == pytest.approx(10.0)
    result = pm.minimum_curvature(0.0, 0.0, 0.0, 100.0, 0.0, 0.0)
    assert result.delta_tvd_ft == pytest.approx(100.0)
    assert result.delta_north_ft == pytest.approx(0.0)
    assert result.dls_deg_per_100ft == pytest.approx(0.0)


def test_turner_velocity() -> None:
    assert pm.turner_critical_velocity_ft_per_s(60.0, 67.0, 2.7) == pytest.approx(7.64, abs=0.1)


def test_kalman_converges() -> None:
    kf = pm.KalmanFilter1D(0.0, 1.0, 0.01, 0.1)
    kf.predict()
    assert kf.variance == pytest.approx(1.01)
    estimate = kf.update(10.0)
    assert 0.0 < estimate < 10.0
    assert kf.variance < 1.01
    for _ in range(30):
        kf.predict()
        kf.update(10.0)
    assert kf.estimate == pytest.approx(10.0, abs=0.5)


# --- formulas the reference implementation does not unit-test, checked against the algebra ---------


def test_tubular_and_petrophysics() -> None:
    assert pm.vshale_linear(85.0) == pytest.approx((85.0 - 20.0) / (150.0 - 20.0))
    assert pm.vshale_linear(500.0) == 1.0  # clamped
    assert pm.density_porosity(2.15) == pytest.approx((2.65 - 2.15) / (2.65 - 1.0))
    assert pm.archie_water_saturation(10.0, 0.25) == pytest.approx(
        ((1.0 * 0.05) / (0.25**2 * 10.0)) ** 0.5
    )
    wall = pm.casing_wall_thickness_in(47.0, 9.625)
    assert wall == pytest.approx(47.0 / (10.68 * 9.625))
    assert pm.barlow_burst_psi(80_000.0, wall, 9.625) == pytest.approx(
        0.875 * 2.0 * 80_000.0 * wall / 9.625
    )
    dt = 9.625 / wall
    assert pm.api_collapse_yield_psi(80_000.0, 9.625, wall) == pytest.approx(
        2.0 * 80_000.0 * (dt - 1.0) / (dt * dt)
    )
    assert pm.pipe_body_yield_lbs(80_000.0, 5.0, 4.276) == pytest.approx(
        80_000.0 * math.pi / 4.0 * (5.0**2 - 4.276**2)
    )
    assert pm.cbl_bond_index(5.0, 20.0, 2.0) == pytest.approx(1.0 - 3.0 / 18.0)
    assert pm.cbl_bond_index(20.0, 20.0, 2.0) == 0.0  # free pipe
    assert pm.arps_hyperbolic_rate(1000.0, 0.01, 0.0, 365.0) == pytest.approx(
        1000.0 * math.exp(-0.01 * 365.0)
    )
    assert pm.arps_hyperbolic_rate(1000.0, 0.01, 1.0, 0.0) == 1000.0


# --- quality gate ---------------------------------------------------------


def test_qse_physics_impossible_reading_scores_zero() -> None:
    out = model.score_sample("wob", 9_999.0)
    assert out["quality_score"] == 0.0
    assert "PHYSICALLY_INVALID" in out["flags"]
    assert out["is_actionable"] is False


def test_qse_clean_sample_is_actionable() -> None:
    out = model.score_sample("wob", 25.0, samples_in_window=60)
    assert out["quality_score"] == pytest.approx(1.0)
    assert out["is_actionable"] is True


def test_qse_out_of_sequence_and_outlier_penalise() -> None:
    seq = model.score_sample("rpm", 120.0, sequence_number=10, last_sequence=12, samples_in_window=60)
    assert seq["quality_score"] == pytest.approx(0.4, abs=1e-3)
    assert "OUT_OF_SEQUENCE" in seq["flags"]

    history = [25.0, 25.1, 24.9, 25.0, 25.05]
    out = model.score_sample("wob", 39.0, history=history, samples_in_window=60)
    assert "OUTLIER" in out["flags"]
    assert out["ground_truth"] == pytest.approx(25.0)  # median substituted


def test_channel_alias_resolves_to_canonical_id() -> None:
    by_alias = model.score_sample("wob", 25.0, samples_in_window=60)
    by_id = model.score_sample("weight_on_bit", 25.0, samples_in_window=60)
    assert by_alias["unit"] == by_id["unit"] == "klbs"
    assert by_alias["quality_score"] == by_id["quality_score"]


def test_qse_drift_and_completeness() -> None:
    drift = model.score_sample("flow_rate", 600.0, redundant_values=[600.0, 900.0], samples_in_window=60)
    assert "DRIFT_DETECTED" in drift["flags"]
    sparse = model.score_sample("flow_rate", 600.0, samples_in_window=20)
    assert "INCOMPLETE" in sparse["flags"]


# --- safety envelope -----------------------------------------------------


def test_envelope_blocks_equipment_limit_as_hard_violation() -> None:
    out = model.check_envelope({"wob": 55.0}, confidence=0.9)
    assert out["passed"] is False
    assert out["hard_violation"] is True
    assert any("WOB" in v for v in out["violations"])


def test_envelope_soft_violations_do_not_demote() -> None:
    low_conf = model.check_envelope({"wob": 25.0}, confidence=0.50)
    assert low_conf["passed"] is False
    assert low_conf["hard_violation"] is False

    kick = model.check_envelope({"wob": 25.0}, confidence=0.95, kick_probability=0.80)
    assert kick["passed"] is False
    assert kick["hard_violation"] is False


def test_envelope_lets_alerts_through_but_not_h2s() -> None:
    alert = model.check_envelope({}, action_type="alert", confidence=0.1, kick_probability=0.99)
    assert alert["passed"] is True  # alerts must reach a human

    h2s = model.check_envelope({}, action_type="alert", h2s_ppm=25.0)
    assert h2s["passed"] is False
    assert any("H2S" in v for v in h2s["violations"])


def test_envelope_mud_window_and_stale_quality() -> None:
    outside = model.check_envelope({"wob": 20.0}, confidence=0.9, rig_ecd_ppg=15.2)
    assert outside["hard_violation"] is True
    stale = model.check_envelope({"wob": 20.0}, confidence=0.9, quality={"wob": 0.55})
    assert stale["passed"] is False
    assert stale["hard_violation"] is False


# --- routing -------------------------------------------------------------


def test_routing_matrix() -> None:
    assert model.route(3, 0.95)["routing"] == "auto_execute"
    assert model.route(3, 0.95)["pack_executes"] is False
    assert model.route(1, 0.95)["routing"] == "human_confirm"
    assert model.route(4, 0.80)["routing"] == "human_confirm"
    assert model.route(4, 0.60)["routing"] == "advisory_only"


# --- negotiation ---------------------------------------------------------


def _p(agent, tier, conf, **params):
    return {"agent_id": agent, "priority_tier": tier, "confidence": conf,
            "action_type": "parameter_change", "parameters": params}


def test_negotiation_safety_beats_confidence() -> None:
    out = model.negotiate([_p("drilling-optimization-agent", 4, 0.99, wob=30.0),
                           _p("well-control-monitoring-agent", 1, 0.80)])
    assert out["outcome"] == "CONSENSUS"
    assert out["winner"]["agent_id"] == "well-control-monitoring-agent"


def test_negotiation_veto_generates_alternative() -> None:
    proposals = [_p("drilling-optimization-agent", 4, 0.95, wob=32.0)]
    vetoes = [{"by_agent": "stuck-pipe-prevention-agent", "priority_tier": 2,
               "target_proposal_id": "p0", "reason": "risk 72/100",
               "suggested_parameters": {"wob": 29.0, "rpm": 130.0}}]
    out = model.negotiate(proposals, vetoes)
    assert out["outcome"] == "CONSENSUS"
    assert out["alternatives"], "veto carrying safer parameters must re-enter"
    assert out["winner"]["parameters"] == {"wob": 29.0, "rpm": 130.0}
    assert out["rejections"]


def test_negotiation_deadlock_timeout_and_empty() -> None:
    dead = model.negotiate(
        [_p("a", 4, 0.9, wob=30.0)],
        [{"by_agent": "b", "priority_tier": 2, "target_proposal_id": "p0", "reason": "no"}],
    )
    assert dead["outcome"] == "DEADLOCK"
    assert model.negotiate([_p("a", 4, 0.9)], elapsed_ms=2000.0)["outcome"] == "TIMEOUT"
    assert model.negotiate([])["outcome"] == "CONSENSUS"


# --- well control --------------------------------------------------------


def test_well_control_normal_is_quiet() -> None:
    out = model.well_control_assess(pit_gain_bbl=0.0, flow_diff_gpm=0.0, gas_units_pct=0.3)
    assert out["alert_level"] == 0
    assert out["classification"] == "NORMAL"


def test_well_control_gas_alone_escalates() -> None:
    out = model.well_control_assess(gas_units_pct=4.0)
    assert out["kick_probability"] >= 0.60
    assert out["alert_level"] >= 3
    assert out["regulatory_notification_required"] is True


def test_well_control_pit_gain_drives_emergency() -> None:
    out = model.well_control_assess(pit_gain_bbl=6.0, flow_diff_gpm=15.0, gas_units_pct=2.0)
    assert out["alert_level"] == 4
    assert out["classification"] == "GAS_KICK"


def test_well_control_losses_are_classified() -> None:
    out = model.well_control_assess(pit_gain_bbl=-2.0, flow_diff_gpm=-8.0)
    assert out["classification"] == "LOST_CIRCULATION"


def test_well_control_never_claims_actuation() -> None:
    out = model.well_control_assess(pit_gain_bbl=3.0)
    assert "Driller" in out["authority"]
