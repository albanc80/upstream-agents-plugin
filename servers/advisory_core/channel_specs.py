"""Channel metadata, generated from the reference implementation ``data/models.py`` CHANNEL_SPECS.

Regenerate from the reference implementation rather than editing by hand: the quality scorer's physics bounds and
the outlier fallback both depend on these ranges, and a hand-edited copy silently diverges.
"""

from __future__ import annotations

from typing import NamedTuple


class ChannelSpec(NamedTuple):
    unit: str
    source: str          # "surface" | "downhole"
    hard_min: float      # physical-plausibility bounds -> PHYSICALLY_INVALID
    hard_max: float
    typical_min: float   # normal operating range
    typical_max: float

    @property
    def typical_range(self) -> float:
        return self.typical_max - self.typical_min


CHANNEL_SPECS: dict[str, ChannelSpec] = {
    "azimuth": ChannelSpec("deg", "downhole", 0.0, 360.0, 0.0, 360.0),
    "bit_depth": ChannelSpec("ft", "surface", 0.0, 40000.0, 0.0, 15000.0),
    "bulk_density": ChannelSpec("g/cc", "downhole", 1.0, 3.5, 2.0, 2.8),
    "casing_pressure": ChannelSpec("psi", "surface", 0.0, 10000.0, 50.0, 1500.0),
    "cbl_amplitude": ChannelSpec("mV", "downhole", 0.0, 100.0, 2.0, 60.0),
    "depth": ChannelSpec("ft", "surface", 0.0, 40000.0, 0.0, 15000.0),
    "ecd": ChannelSpec("ppg", "downhole", 0.0, 25.0, 9.0, 14.5),
    "flow_out": ChannelSpec("gpm", "surface", 0.0, 1500.0, 200.0, 800.0),
    "flow_rate": ChannelSpec("gpm", "surface", 0.0, 1500.0, 200.0, 800.0),
    "gamma_ray": ChannelSpec("gAPI", "downhole", 0.0, 400.0, 20.0, 150.0),
    "gas": ChannelSpec("%", "surface", 0.0, 100.0, 0.0, 2.0),
    "hook_load": ChannelSpec("klbs", "surface", 0.0, 600.0, 50.0, 300.0),
    "inclination": ChannelSpec("deg", "downhole", 0.0, 180.0, 0.0, 90.0),
    "mwd_annular_pressure": ChannelSpec("psi", "downhole", 0.0, 20000.0, 3000.0, 8000.0),
    "mwd_temperature": ChannelSpec("degF", "downhole", 0.0, 500.0, 80.0, 250.0),
    "neutron_porosity": ChannelSpec("frac", "downhole", -0.1, 1.0, 0.05, 0.45),
    "pit_volume": ChannelSpec("bbl", "surface", 0.0, 5000.0, 200.0, 1200.0),
    "production_rate": ChannelSpec("stb/d", "surface", 0.0, 50000.0, 200.0, 2500.0),
    "proppant_concentration": ChannelSpec("ppa", "surface", 0.0, 25.0, 0.0, 6.0),
    "resistivity": ChannelSpec("ohm.m", "downhole", 0.1, 5000.0, 1.0, 200.0),
    "return_density": ChannelSpec("ppg", "surface", 0.0, 25.0, 8.0, 16.0),
    "rop": ChannelSpec("ft/hr", "surface", 0.0, 500.0, 10.0, 200.0),
    "rpm": ChannelSpec("rpm", "surface", 0.0, 300.0, 40.0, 180.0),
    "slurry_rate": ChannelSpec("bpm", "surface", 0.0, 150.0, 30.0, 100.0),
    "standpipe_pressure": ChannelSpec("psi", "surface", 0.0, 10000.0, 1000.0, 4000.0),
    "torque": ChannelSpec("ft-lbs", "surface", 0.0, 50000.0, 1000.0, 15000.0),
    "treating_pressure": ChannelSpec("psi", "surface", 0.0, 15000.0, 4000.0, 9500.0),
    "tubing_pressure": ChannelSpec("psi", "surface", 0.0, 10000.0, 500.0, 3000.0),
    "weight_on_bit": ChannelSpec("klbs", "surface", 0.0, 100.0, 5.0, 40.0),
}
