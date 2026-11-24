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
    with pytest.raises(ValueError, match="positive true vertical depth"):
        pm.mud_weight_from_pressure_ppg(100.0, 0.0)


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
        [_p("drilling-optimization-agent", 4, 0.9, wob=30.0)],
        [{"by_agent": "well-control-monitoring-agent", "priority_tier": 2, "target_proposal_id": "p0", "reason": "no"}],
    )
    assert dead["outcome"] == "DEADLOCK"
    assert model.negotiate([_p("drilling-optimization-agent", 4, 0.9)], elapsed_ms=2000.0)["outcome"] == "TIMEOUT"
    assert model.negotiate([])["outcome"] == "CONSENSUS"


# --- well control --------------------------------------------------------


def test_well_control_normal_is_quiet() -> None:
    out = model.well_control_assess(pit_gain_bbl=0.0, flow_diff_gpm=0.0, gas_units_pct=0.3)
    assert out["alert_level"] == 0
    assert out["classification"] == "NORMAL"


def test_well_control_gas_alone_is_capped_at_advisory() -> None:
    """A single signal must not carry Emergency on its own; gas is capped at Advisory."""
    out = model.well_control_assess(gas_units_pct=4.0)
    assert out["alert_level"] == 2
    corroborated = model.well_control_assess(gas_units_pct=4.0, flow_diff_gpm=12.0)
    assert corroborated["alert_level"] > out["alert_level"]



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


def test_well_control_refuses_an_empty_payload() -> None:
    """A typo'd parameter name leaves every signal at its 0.0 default.

    Fusing that would return a confident "Normal" on a well that is flowing, so the
    function must refuse rather than answer.
    """
    with pytest.raises(ValueError, match="at least one kick signal"):
        model.well_control_assess()


def test_well_control_refuses_a_payload_of_only_zeros() -> None:
    with pytest.raises(ValueError, match="at least one kick signal"):
        model.well_control_assess(
            pit_gain_bbl=0.0, flow_diff_gpm=0.0, gas_units_pct=0.0, pwd_residual_sigma=0.0
        )


# --- regressions from the external audit (1.1.2) --------------------------


def test_well_control_losses_are_never_normal() -> None:
    """A loss is a lost-circulation event. It must not report Normal, and the probability of a
    gain cannot go negative because a signal is absent."""
    out = model.well_control_assess(pit_gain_bbl=-8.0)
    assert out["alert_level"] >= 2
    assert out["alert_name"] != "Normal"
    assert out["classification"] == "LOST_CIRCULATION"
    assert out["kick_probability"] >= 0.0
    assert out["losses_detected"] is True


def test_well_control_refuses_an_impossible_gas_reading() -> None:
    with pytest.raises(ValueError, match="not a physical reading"):
        model.well_control_assess(gas_units_pct=250.0)


def test_well_control_escalation_is_never_classified_normal() -> None:
    out = model.well_control_assess(gas_units_pct=4.0, flow_diff_gpm=12.0)
    assert out["alert_level"] >= 3
    assert out["classification"] != "NORMAL"


def test_envelope_resolves_the_channel_name() -> None:
    """weight_on_bit is the channel id; wob is the parameter name. Both reach the same limit."""
    for naming in ({"weight_on_bit": 250.0}, {"wob": 250.0}, {"wob_klbf": 250.0}):
        out = model.check_envelope(naming)
        assert out["passed"] is False, naming
        assert out["hard_violation"] is True, naming


def test_envelope_refuses_a_parameter_it_cannot_evaluate() -> None:
    out = model.check_envelope({"bit_size_in": 12.25})
    assert out["passed"] is False
    assert out["unverified_parameters"] == ["bit_size_in"]
    assert any("cannot evaluate" in v for v in out["violations"])


def test_envelope_still_passes_a_safe_change_by_channel_name() -> None:
    out = model.check_envelope({"weight_on_bit": 38.0, "rpm": 150.0})
    assert out["passed"] is True
    assert out["unverified_parameters"] == []


def test_kill_mud_weight_requires_a_positive_tvd() -> None:
    with pytest.raises(ValueError, match="positive true vertical depth"):
        pm.kill_mud_weight_ppg(12.0, 260.0, 0.0)


def test_ecd_requires_a_positive_tvd() -> None:
    with pytest.raises(ValueError, match="positive TVD"):
        pm.equivalent_circulating_density_ppg(10.3, 250.0, 0.0)


# --- regressions from the second audit pass (1.1.4) -----------------------


def test_negotiation_refuses_an_unmatched_veto() -> None:
    """A veto pointed at the wrong id is dropped and its target wins unopposed."""
    proposals = [_p("drilling-optimization-agent", 4, 0.95, wob=38.0)]
    vetoes = [{"by_agent": "stuck-pipe-prevention-agent", "priority_tier": 1,
               "target_proposal_id": "typo-id", "reason": "drag"}]
    with pytest.raises(ValueError, match="target_proposal_id not found"):
        model.negotiate(proposals, vetoes)


def test_negotiation_refuses_out_of_range_tier() -> None:
    for tier in (0, 5, 99):
        with pytest.raises(ValueError, match="priority_tier"):
            model.negotiate([_p("drilling-optimization-agent", tier, 0.9)], [])


def test_negotiation_refuses_out_of_range_confidence() -> None:
    for confidence in (-1.0, 5.0):
        with pytest.raises(ValueError, match="confidence"):
            model.negotiate([_p("drilling-optimization-agent", 4, confidence)], [])


def test_route_refuses_an_impossible_autonomy_level() -> None:
    for level in (-3, 0, 6, 99):
        with pytest.raises(ValueError, match="autonomy level"):
            model.route(level, 0.99)


def test_route_refuses_an_impossible_confidence() -> None:
    for confidence in (-0.5, 7.0):
        with pytest.raises(ValueError, match="confidence"):
            model.route(2, confidence)


def test_route_never_claims_execution() -> None:
    out = model.route(2, 0.9)
    assert out["routing"] == "auto_execute"
    assert out["pack_executes"] is False


# --- regressions from the third audit pass (1.1.5) -----------------------


def test_pressure_formulas_refuse_impossible_inputs() -> None:
    with pytest.raises(ValueError, match="positive mud weight"):
        pm.hydrostatic_pressure_psi(-100.0, 10_000.0)
    with pytest.raises(ValueError, match="negative"):
        pm.hydrostatic_pressure_psi(12.0, -100.0)
    with pytest.raises(ValueError, match="negative"):
        pm.mud_weight_from_pressure_ppg(-500.0, 10_000.0)


def test_maasp_refuses_a_negative_margin() -> None:
    """A current mud weight above the maximum means the shoe margin is gone, not -260 psi."""
    with pytest.raises(ValueError, match="exceeds the maximum"):
        pm.maasp_psi(14.5, 15.0, 5_000.0)
    assert pm.maasp_psi(14.5, 12.0, 5_000.0) == pytest.approx(650.0)


def test_qse_bare_sample_is_not_certifiable() -> None:
    """Nothing but a value means only the range check ran; that is not a clean bill of health."""
    out = model.score_sample("flow_out", 1.0)
    assert out["is_actionable"] is False
    assert "UNVERIFIED_CHECKS" in out["flags"]
    assert out["unverified_checks"] == ["completeness"]


def test_qse_single_sample_with_window_is_still_actionable() -> None:
    out = model.score_sample("wob", 25.0, samples_in_window=60)
    assert out["is_actionable"] is True
    assert out["flags"] == ["OK"]


def test_envelope_refuses_a_parameter_with_no_configured_limit() -> None:
    """A parameter the policy has no ceiling for is not certified, it is refused."""
    out = model.check_envelope({"hydraulic_horsepower": 900.0})
    assert out["passed"] is False
    assert out["unverified_parameters"] == ["hydraulic_horsepower"]


def test_negotiation_refuses_a_winner_that_breaches_the_envelope() -> None:
    proposals = [_p("drilling-optimization-agent", 4, 0.95)]
    proposals[0]["parameters"] = {"weight_on_bit": 300.0}
    with pytest.raises(ValueError, match="breaches the safety envelope"):
        model.negotiate(proposals, [])


# --- regressions from the fourth audit pass (1.1.6) ----------------------


def test_envelope_compares_flow_rate() -> None:
    out = model.check_envelope({"flow_rate": 5000.0})
    assert out["passed"] is False
    assert out["hard_violation"] is True
    assert out["unverified_parameters"] == []
    assert any("flow rate" in v for v in out["violations"])
    assert model.check_envelope({"flow_rate": 800.0})["passed"] is True


def test_losses_escalate_with_size() -> None:
    """Every loss used to sit at Advisory whatever its size."""
    small = model.well_control_assess(pit_gain_bbl=-0.5)
    medium = model.well_control_assess(pit_gain_bbl=-3.0)
    large = model.well_control_assess(pit_gain_bbl=-6.0)
    assert small["alert_level"] < medium["alert_level"] < large["alert_level"]
    assert medium["alert_level"] == 2
    assert large["alert_level"] == 3
    assert large["alert_level"] < 4, "a well losing returns is not shut in"
    for out in (small, medium, large):
        assert out["classification"] == "LOST_CIRCULATION"
        assert out["losses_detected"] is True


def test_negotiation_refuses_an_unknown_agent() -> None:
    with pytest.raises(ValueError, match="unknown agent id"):
        model.negotiate([_p("phantom-safety-agent", 1, 0.99)], [])


def test_negotiation_accepts_a_packaged_agent() -> None:
    out = model.negotiate([_p("well-control-monitoring-agent", 1, 0.8)], [])
    assert out["outcome"] == "CONSENSUS"


def test_flow_only_loss_is_not_monitor() -> None:
    """A 200 gpm deficit with a steady pit used to read Monitor: the ladder only counted pit volume."""
    out = model.well_control_assess(flow_diff_gpm=-200.0)
    assert out["losses_detected"] is True
    assert out["loss_basis"] == "flow_equivalent"
    assert out["alert_level"] >= 2
    assert out["classification"] == "LOST_CIRCULATION"
    assert out["loss_equivalent_bbl"] == pytest.approx(200 / 42.0, abs=0.01)


def test_a_large_flow_only_loss_reaches_well_control_alert() -> None:
    out = model.well_control_assess(flow_diff_gpm=-400.0)
    assert out["alert_level"] == 3
    assert out["alert_level"] < 4, "a well losing returns is not shut in"


def test_loss_basis_reports_both_signals() -> None:
    out = model.well_control_assess(pit_gain_bbl=-6.0, flow_diff_gpm=-100.0)
    assert out["loss_basis"] == "both"
    assert out["loss_equivalent_bbl"] == 6.0


def test_loss_note_names_the_level_actually_set() -> None:
    """The note said 'escalated to the Advisory level' even when the level shown was 3."""
    out = model.well_control_assess(pit_gain_bbl=-6.0)
    note = " ".join(out["notes"])
    assert out["alert_level"] == 3
    assert "Advisory level" not in note
    assert "level 3" in note
    assert "authored ladder" in note


def test_loss_with_influx_is_underground_flow() -> None:
    """A loss that also shows gas or excess flow is the underground-flow signature, not a loss."""
    out = model.well_control_assess(pit_gain_bbl=-5.0, gas_units_pct=2.0)
    assert out["alert_level"] == 4
    assert out["classification"] == "UNDERGROUND_FLOW_SUSPECTED"


def test_pit_gain_override_is_inclusive() -> None:
    """2.00 bbl is a pit total that lands on an exact tenth; it must not be one level below 2.01."""
    assert model.well_control_assess(pit_gain_bbl=2.0)["alert_level"] == 3
    assert model.well_control_assess(pit_gain_bbl=2.01)["alert_level"] == 3


def test_gas_below_background_contributes_nothing() -> None:
    out = model.well_control_assess(gas_units_pct=0.4)
    assert out["mass"]["gas_or_flow"] == 0.0
    assert out["alert_level"] == 0


def test_gas_and_flow_corroborate() -> None:
    """Under max(), 2% gas with +5 gpm scored exactly the same as gas alone."""
    gas_only = model.well_control_assess(gas_units_pct=2.0)["kick_score"]
    with_flow = model.well_control_assess(gas_units_pct=2.0, flow_diff_gpm=5.0)["kick_score"]
    assert with_flow > gas_only


def test_flow_check_outranks_the_score() -> None:
    """Evidence sets the floor: a positive flow check with pumps off is a shut-in proposal."""
    out = model.well_control_assess(flow_check_pumps_off=True)
    assert out["alert_level"] == 4
    assert out["classification"] == "KICK_CONFIRMED"


def test_kick_score_renamed_with_a_deprecated_alias() -> None:
    out = model.well_control_assess(gas_units_pct=2.0)
    assert out["kick_score"] == out["kick_probability"]
    assert "Deterministic" in out["basis"]


def test_loss_classes_follow_rate() -> None:
    assert model.well_control_assess(flow_diff_gpm=-3.0)["loss_class"] == "seepage"
    assert model.well_control_assess(flow_diff_gpm=-20.0)["loss_class"] == "partial"
    assert model.well_control_assess(flow_diff_gpm=-80.0)["loss_class"] == "severe"


def test_envelope_checks_mud_weight_itself() -> None:
    """The window was applied to proposed ECD only, so mud weight 8.8 passed a 9.0 ppg floor."""
    out = model.check_envelope({"mud_weight": 8.8})
    assert out["passed"] is False
    assert out["hard_violation"] is True
    assert any("mud weight" in v for v in out["violations"])


def test_quality_floor_is_inclusive() -> None:
    """57 of 60 samples IS 0.95: the floor must not exclude its own value."""
    out = model.score_sample("wob", 25.0, samples_in_window=57)
    assert out["quality_score"] == pytest.approx(0.95)
    assert out["is_actionable"] is True


def test_defaults_are_reported_not_hidden() -> None:
    """A default standing in for a company-policy value must say so in every answer that uses it."""
    out = model.well_control_assess(pit_gain_bbl=1.0)
    assert "min_data_quality_to_act" in out["defaults_in_use"]
    assert "pit_gain.kick_tolerance_fraction" in out["defaults_in_use"]
    assert "must update" in out["calibration_note"].lower() or "Update them" in out["calibration_note"]
    env = model.check_envelope({"wob": 20.0})
    assert "min_data_quality_to_act" in env["defaults_in_use"]


def test_influx_height_makes_fixed_barrels_interpretable() -> None:
    """5 bbl is 18 ft of influx in 17.5" hole and 109 ft in 8.5": the same volume, different risk."""
    big = model.well_control_assess(pit_gain_bbl=5.0, hole_diameter_in=17.5, pipe_od_in=5.0)
    small = model.well_control_assess(pit_gain_bbl=5.0, hole_diameter_in=8.5, pipe_od_in=5.0)
    assert big["influx_height_ft"] < small["influx_height_ft"]
    assert big["annular_capacity_bbl_ft"] == pytest.approx((17.5**2 - 5.0**2) / 1029.4, abs=1e-3)


def test_volumetric_cap_escalates_to_emergency() -> None:
    """With a kick-tolerance volume supplied, exceeding half of it is an Emergency."""
    under = model.well_control_assess(pit_gain_bbl=4.0, kick_tolerance_volume_bbl=20.0)
    over = model.well_control_assess(pit_gain_bbl=12.0, kick_tolerance_volume_bbl=20.0)
    assert under["volumetric_cap_bbl"] == pytest.approx(10.0)
    assert under["alert_level"] < 4
    assert over["alert_level"] == 4


def test_geometry_is_optional_and_never_invented() -> None:
    out = model.well_control_assess(pit_gain_bbl=3.0)
    assert out["influx_height_ft"] is None
    assert out["volumetric_cap_bbl"] is None


def test_flow_only_loss_discloses_the_equivalent_basis() -> None:
    note = " ".join(model.well_control_assess(flow_diff_gpm=-200.0)["notes"])
    assert "equivalent" in note and "not a measured volume" in note


def test_authored_values_are_declared_as_authored() -> None:
    """A value that was not transcribed must say so, so nobody mistakes it for reviewed."""
    from advisory_core import model as m
    policy = m._load("src/policies/safety-envelope.yaml") or {}
    declared = set(policy.get("authored_limits") or [])
    assert "max_flow_rate_gpm" in declared
    assert "losses.advisory_bbl" in declared and "losses.alert_bbl" in declared
    assert "losses.flow_equivalent_gpm_per_bbl" in declared
