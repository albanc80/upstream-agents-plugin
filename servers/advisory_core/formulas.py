"""Physics / petroleum-engineering formulas.

Transcribed verbatim from the reference implementation ``safety/physics_models.py`` so the plugin and
the platform return identical numbers for identical inputs. Oilfield units throughout: mud
weight ppg, depth ft (TVD), pressure psi, unless a name says otherwise.

Do not "improve" a formula here. If the reference implementation changes, re-transcribe and re-run
``tests/test_parity_with_roc.py``, which asserts this module against the reference implementation's own hand-calculated
expectations.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

PRESSURE_GRADIENT_CONSTANT = 0.052
STEEL_WEIGHT_PPG = 65.5
CAPACITY_CONSTANT = 1029.4


# --- Pressure & gradient ---------------------------------------------------


def pressure_gradient_psi_per_ft(mud_weight_ppg: float) -> float:
    """psi/ft = MW(ppg) x 0.052."""
    return mud_weight_ppg * PRESSURE_GRADIENT_CONSTANT


def hydrostatic_pressure_psi(mud_weight_ppg: float, tvd_ft: float) -> float:
    """HP = MW(ppg) x 0.052 x TVD(ft).

    A non-positive mud weight is not a fluid: it would return a negative pressure that reads as
    a valid number.
    """
    if mud_weight_ppg <= 0:
        raise ValueError(f"hydrostatic pressure needs a positive mud weight; got {mud_weight_ppg} ppg")
    if tvd_ft < 0:
        raise ValueError(f"hydrostatic pressure needs a non-negative TVD; got {tvd_ft} ft")
    return mud_weight_ppg * PRESSURE_GRADIENT_CONSTANT * tvd_ft


def mud_weight_from_pressure_ppg(pressure_psi: float, tvd_ft: float) -> float:
    """MW(ppg) = P / (0.052 x TVD).

    A non-positive TVD has no answer; returning 0.0 ppg would present it as a mud weight.
    """
    if tvd_ft <= 0:
        raise ValueError(
            f"mud weight from pressure needs a positive true vertical depth; got tvd_ft={tvd_ft}"
        )
    if pressure_psi < 0:
        raise ValueError(f"pressure cannot be negative; got {pressure_psi} psi")
    return pressure_psi / (PRESSURE_GRADIENT_CONSTANT * tvd_ft)


def buoyancy_factor(mud_weight_ppg: float) -> float:
    """BF = 1 - MW / 65.5 (weight of tubulars in fluid)."""
    return 1.0 - mud_weight_ppg / STEEL_WEIGHT_PPG


def equivalent_circulating_density_ppg(
    mud_weight_ppg: float, annular_pressure_loss_psi: float, tvd_ft: float
) -> float:
    """ECD = APL / (TVD x 0.052) + MW.

    A non-positive TVD has no annulus to report on; returning the mud weight would present a
    static value as a circulating density, so this raises instead.
    """
    if tvd_ft <= 0:
        raise ValueError(
            f"equivalent circulating density needs a positive TVD; got tvd_ft={tvd_ft}"
        )
    return annular_pressure_loss_psi / (tvd_ft * PRESSURE_GRADIENT_CONSTANT) + mud_weight_ppg


# --- Well control ----------------------------------------------------------


def maasp_psi(max_mud_weight_ppg: float, current_mud_weight_ppg: float, shoe_tvd_ft: float) -> float:
    """MAASP = 0.052 x (MaxMW - CurrentMW) x ShoeTVD.

    A current mud weight above the maximum gives a negative MAASP, which means the shoe margin is
    already gone — that is a well-control condition, not a pressure to report quietly.
    """
    if current_mud_weight_ppg > max_mud_weight_ppg:
        raise ValueError(
            f"current mud weight {current_mud_weight_ppg} ppg exceeds the maximum "
            f"{max_mud_weight_ppg} ppg: MAASP would be negative, i.e. no remaining shoe margin"
        )
    if shoe_tvd_ft <= 0:
        raise ValueError(f"MAASP needs a positive shoe TVD; got {shoe_tvd_ft} ft")
    return PRESSURE_GRADIENT_CONSTANT * (max_mud_weight_ppg - current_mud_weight_ppg) * shoe_tvd_ft


def kill_mud_weight_ppg(current_mud_weight_ppg: float, sidpp_psi: float, tvd_ft: float) -> float:
    """Required kill mud weight W2 = W1 + SIDPP / (TVD x 0.052).

    A non-positive TVD has no defined answer; returning the current mud weight would read as a
    valid kill weight, so this raises instead.
    """
    if tvd_ft <= 0:
        raise ValueError(
            f"kill mud weight needs a positive true vertical depth; got tvd_ft={tvd_ft}. "
            "Returning the current mud weight would be indistinguishable from a real kill weight."
        )
    return current_mud_weight_ppg + sidpp_psi / (tvd_ft * PRESSURE_GRADIENT_CONSTANT)


def formation_pressure_psi(sidpp_psi: float, mud_weight_ppg: float, tvd_ft: float) -> float:
    """Formation pressure P = SIDPP + 0.052 x MW x TVD."""
    return sidpp_psi + hydrostatic_pressure_psi(mud_weight_ppg, tvd_ft)


def initial_circulating_pressure_psi(sidpp_psi: float, slow_circulating_rate_psi: float) -> float:
    """ICP = SIDPP + SCR."""
    return sidpp_psi + slow_circulating_rate_psi


def final_circulating_pressure_psi(
    slow_circulating_rate_psi: float, kill_mud_weight_ppg: float, current_mud_weight_ppg: float
) -> float:
    """FCP = SCR x (W2 / W1)."""
    if current_mud_weight_ppg <= 0:
        return slow_circulating_rate_psi
    return slow_circulating_rate_psi * (kill_mud_weight_ppg / current_mud_weight_ppg)


def mud_weight_window_ppg(
    pore_pressure_ppg: float, fracture_gradient_ppg: float
) -> tuple[float, float]:
    """Safe operating window: (pore-pressure EMW, fracture-gradient upper bound)."""
    return (pore_pressure_ppg, fracture_gradient_ppg)


def is_within_mud_weight_window(
    emw_ppg: float, pore_pressure_ppg: float, fracture_gradient_ppg: float
) -> bool:
    return pore_pressure_ppg <= emw_ppg <= fracture_gradient_ppg


def kick_tolerance_intensity_ppg(
    fracture_gradient_ppg: float,
    mud_weight_ppg: float,
    shoe_tvd_ft: float,
    well_tvd_ft: float,
) -> float:
    """Mud-weight-equivalent margin the shoe can absorb, scaled by shoe/TD depth ratio."""
    if well_tvd_ft <= 0:
        return 0.0
    margin = max(0.0, fracture_gradient_ppg - mud_weight_ppg)
    return margin * (shoe_tvd_ft / well_tvd_ft)


# --- Hydraulics / hole cleaning -------------------------------------------


def pipe_capacity_bbl_per_ft(diameter_in: float) -> float:
    """Internal capacity: D^2 / 1029.4 (bbl/ft)."""
    return diameter_in**2 / CAPACITY_CONSTANT


def annular_capacity_bbl_per_ft(hole_diameter_in: float, pipe_diameter_in: float) -> float:
    """Annular capacity: (Dhole^2 - Dpipe^2) / 1029.4 (bbl/ft)."""
    return (hole_diameter_in**2 - pipe_diameter_in**2) / CAPACITY_CONSTANT


def annular_velocity_ft_per_min(
    pump_output_bbl_per_min: float, annular_capacity_bbl_per_ft: float
) -> float:
    """AV = pump output / annular capacity (ft/min)."""
    if annular_capacity_bbl_per_ft <= 0:
        return 0.0
    return pump_output_bbl_per_min / annular_capacity_bbl_per_ft


def teale_mse_psi(
    wob_klbf: float, rpm: float, torque_ft_lbf: float, bit_size_in: float, rop_ft_hr: float
) -> float:
    """MSE = WOB / A + (480 x RPM x Torque) / (A x ROP), A = pi/4 x bit_size^2."""
    bit_area_in2 = math.pi / 4.0 * bit_size_in**2
    if bit_area_in2 <= 0 or rop_ft_hr <= 0:
        return 0.0
    return (wob_klbf * 1000.0 / bit_area_in2) + (
        480.0 * rpm * torque_ft_lbf / (bit_area_in2 * rop_ft_hr)
    )


# --- Petrophysics (LWD / Geosteering) -------------------------------------


def vshale_linear(gr_api: float, gr_min: float = 20.0, gr_max: float = 150.0) -> float:
    """Linear shale volume from gamma ray (clamped 0-1)."""
    if gr_max <= gr_min:
        return 0.0
    return max(0.0, min(1.0, (gr_api - gr_min) / (gr_max - gr_min)))


def density_porosity(
    rhob_gcc: float, matrix_density_gcc: float = 2.65, fluid_density_gcc: float = 1.0
) -> float:
    """Porosity from bulk density (clamped 0-1)."""
    denom = matrix_density_gcc - fluid_density_gcc
    if denom <= 0:
        return 0.0
    return max(0.0, min(1.0, (matrix_density_gcc - rhob_gcc) / denom))


def archie_water_saturation(
    rt_ohmm: float,
    porosity: float,
    rw_ohmm: float = 0.05,
    a: float = 1.0,
    m: float = 2.0,
    n: float = 2.0,
) -> float:
    """Archie Sw = ((a*Rw)/(phi^m * Rt))^(1/n), clamped 0-1."""
    if porosity <= 0 or rt_ohmm <= 0:
        return 1.0
    sw = float(((a * rw_ohmm) / (porosity**m * rt_ohmm)) ** (1.0 / n))
    return max(0.0, min(1.0, sw))


def cuttings_transport_ratio(
    annular_velocity_ft_min: float, slip_velocity_ft_min: float, inclination_deg: float
) -> float:
    """CTR (high-angle corrected); adequate hole cleaning at CTR >= 0.55."""
    if slip_velocity_ft_min <= 0:
        return 1.0
    f_inc = 1.0 + 0.3 * math.sin(2.0 * math.radians(inclination_deg))
    va_effective = annular_velocity_ft_min * math.cos(math.radians(inclination_deg))
    return max(0.0, min(1.0, va_effective / (slip_velocity_ft_min * f_inc)))


# --- Trajectory ------------------------------------------------------------


@dataclass(frozen=True)
class MinCurvatureResult:
    delta_north_ft: float
    delta_east_ft: float
    delta_tvd_ft: float
    dogleg_deg: float
    dls_deg_per_100ft: float


def dogleg_angle_deg(inc1_deg: float, az1_deg: float, inc2_deg: float, az2_deg: float) -> float:
    """cos(DL) = cos(I1)cos(I2) + sin(I1)sin(I2)cos(A2 - A1)."""
    i1, a1, i2, a2 = map(math.radians, (inc1_deg, az1_deg, inc2_deg, az2_deg))
    cos_dl = math.cos(i1) * math.cos(i2) + math.sin(i1) * math.sin(i2) * math.cos(a2 - a1)
    cos_dl = max(-1.0, min(1.0, cos_dl))
    return math.degrees(math.acos(cos_dl))


def dogleg_severity_deg_per_100ft(
    inc1_deg: float, az1_deg: float, inc2_deg: float, az2_deg: float, course_length_ft: float
) -> float:
    """DLS = dogleg angle x (100 / course length)."""
    if course_length_ft <= 0:
        return 0.0
    return dogleg_angle_deg(inc1_deg, az1_deg, inc2_deg, az2_deg) * (100.0 / course_length_ft)


def minimum_curvature(
    md1_ft: float, inc1_deg: float, az1_deg: float, md2_ft: float, inc2_deg: float, az2_deg: float
) -> MinCurvatureResult:
    """Minimum-curvature position increment between two survey stations."""
    course_length = md2_ft - md1_ft
    dl_deg = dogleg_angle_deg(inc1_deg, az1_deg, inc2_deg, az2_deg)
    beta = math.radians(dl_deg)
    ratio_factor = 1.0 if beta < 1e-9 else (2.0 / beta) * math.tan(beta / 2.0)

    i1, a1, i2, a2 = map(math.radians, (inc1_deg, az1_deg, inc2_deg, az2_deg))
    half_cl = course_length / 2.0
    delta_north = half_cl * (math.sin(i1) * math.cos(a1) + math.sin(i2) * math.cos(a2)) * ratio_factor
    delta_east = half_cl * (math.sin(i1) * math.sin(a1) + math.sin(i2) * math.sin(a2)) * ratio_factor
    delta_tvd = half_cl * (math.cos(i1) + math.cos(i2)) * ratio_factor
    dls = dl_deg * (100.0 / course_length) if course_length > 0 else 0.0
    return MinCurvatureResult(delta_north, delta_east, delta_tvd, dl_deg, dls)


# --- Production -----------------------------------------------------------


def turner_critical_velocity_ft_per_s(
    surface_tension_dyne_cm: float, liquid_density_lb_ft3: float, gas_density_lb_ft3: float
) -> float:
    """Turner unloading velocity: v = 1.593 sigma^0.25 (rho_l - rho_g)^0.25 / rho_g^0.5."""
    if gas_density_lb_ft3 <= 0:
        return 0.0
    numerator = (
        1.593
        * surface_tension_dyne_cm**0.25
        * max(0.0, liquid_density_lb_ft3 - gas_density_lb_ft3) ** 0.25
    )
    return float(numerator / gas_density_lb_ft3**0.5)


# --- Tubular mechanics (API 5C3) -----------------------------------------


def casing_wall_thickness_in(weight_ppf: float, od_in: float) -> float:
    """t ~ W / (10.68 x OD)."""
    if od_in <= 0:
        return 0.0
    return weight_ppf / (10.68 * od_in)


def barlow_burst_psi(yield_strength_psi: float, wall_in: float, od_in: float) -> float:
    """API Barlow burst with the 0.875 wall-tolerance factor."""
    if od_in <= 0:
        return 0.0
    return 0.875 * 2.0 * yield_strength_psi * wall_in / od_in


def api_collapse_yield_psi(yield_strength_psi: float, od_in: float, wall_in: float) -> float:
    """API 5C3 yield-strength collapse."""
    if wall_in <= 0 or od_in <= 0:
        return 0.0
    dt = od_in / wall_in
    return 2.0 * yield_strength_psi * (dt - 1.0) / (dt * dt)


def pipe_body_yield_lbs(yield_strength_psi: float, od_in: float, id_in: float) -> float:
    """Pipe-body tensile yield: Yp x cross-section area."""
    return yield_strength_psi * math.pi / 4.0 * max(0.0, od_in**2 - id_in**2)


# --- Cement evaluation ----------------------------------------------------


def cbl_bond_index(measured_amp: float, free_pipe_amp: float, cemented_amp: float) -> float:
    """BI = 1 - (measured - cemented)/(free - cemented). 1.0 cemented, 0.0 free pipe."""
    denom = free_pipe_amp - cemented_amp
    if denom <= 0:
        return 0.0
    return max(0.0, min(1.0, 1.0 - (measured_amp - cemented_amp) / denom))


# --- Decline analysis -----------------------------------------------------


def arps_hyperbolic_rate(qi_stb_d: float, di_per_day: float, b: float, t_days: float) -> float:
    """Arps hyperbolic decline q(t) = qi / (1 + b Di t)^(1/b); b->0 is exponential."""
    if t_days <= 0:
        return qi_stb_d
    if b <= 1e-6:
        return qi_stb_d * math.exp(-di_per_day * t_days)
    return float(qi_stb_d / (1.0 + b * di_per_day * t_days) ** (1.0 / b))


# --- Kalman filter --------------------------------------------------------


class KalmanFilter1D:
    """Scalar linear Kalman filter, used to smooth pit volume and fuse signals."""

    def __init__(
        self,
        initial_estimate: float,
        initial_variance: float,
        process_variance: float,
        measurement_variance: float,
    ) -> None:
        self.estimate = initial_estimate
        self.variance = initial_variance
        self.process_variance = process_variance
        self.measurement_variance = measurement_variance

    def predict(self, control: float = 0.0) -> float:
        self.estimate += control
        self.variance += self.process_variance
        return self.estimate

    def update(self, measurement: float) -> float:
        kalman_gain = self.variance / (self.variance + self.measurement_variance)
        self.estimate += kalman_gain * (measurement - self.estimate)
        self.variance *= 1.0 - kalman_gain
        return self.estimate
