"""The README's capability section quotes thresholds. Hold it to the contracts.

README claims are the easiest thing in a package to let rot: nobody re-reads prose when a limit
changes. Each row below ties a phrase in the README to the contract value it describes, so a
threshold edit that is not reflected in the README fails the build.
"""

from __future__ import annotations

import inspect
import re
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]


def _readme() -> str:
    # Collapse wrapping so a phrase can be asserted without depending on line breaks.
    return re.sub(r"\s+", " ", (ROOT / "README.md").read_text(encoding="utf-8"))


def _contract(agent_id: str) -> dict:
    return yaml.safe_load((ROOT / "src/agents" / f"{agent_id}.yaml").read_text(encoding="utf-8"))


def _dig(payload: dict, dotted: str):
    node = payload
    for part in dotted.split("."):
        node = node[part]
    return node


# (phrase that must appear in the README, contract file, path, value)
CLAIMS = [
    ("1.10 burst", "casing-agent", "thresholds.min_burst_df", 1.10),
    ("1.00 collapse", "casing-agent", "thresholds.min_collapse_df", 1.00),
    ("1.30 tension", "casing-agent", "thresholds.min_tension_df", 1.30),
    ("below 0.55 is a problem", "hydraulics-optimization-agent", "thresholds.ctr_adequate", 0.55),
    ("below 0.40 a deficit", "hydraulics-optimization-agent", "thresholds.ctr_deficit", 0.40),
    ("caution at 1.5", "directional-steering-agent", "thresholds.wsf_caution", 1.5),
    ("stop at 1.0", "directional-steering-agent", "thresholds.wsf_mandatory_stop", 1.0),
    ("0.70 to pass", "cementing-agent", "thresholds.zia_pass", 0.70),
    ("0.50 to fail", "cementing-agent", "thresholds.zia_fail", 0.50),
    ("MAOP alert at 95%", "stimulation-agent", "thresholds.maop_alert_fraction", 0.95),
    ("1.2 Turner factor", "production-monitoring-agent", "thresholds.turner_loading_factor", 1.2),
    ("500 psi/min rise sustained over 3 readings", "stimulation-agent",
     "thresholds.screenout_rise_psi_per_min", 500.0),
    ("above 2 bbl advisory", "well-control-monitoring-agent", "thresholds.pit_gain.advisory_bbl", 2.0),
    ("above 5 bbl emergency", "well-control-monitoring-agent", "thresholds.pit_gain.emergency_bbl", 5.0),
    ("60 immediate", "stuck-pipe-prevention-agent", "thresholds.risk_score.immediate", 60.0),
    ("80 critical", "stuck-pipe-prevention-agent", "thresholds.risk_score.critical", 80.0),
]


@pytest.mark.parametrize("phrase,agent,path,value", CLAIMS)
def test_readme_claim_matches_contract(phrase: str, agent: str, path: str, value: float) -> None:
    contract_value = _dig(_contract(agent), path)
    assert isinstance(contract_value, (int, float)), f"{agent}:{path} is not numeric"
    assert float(contract_value) == pytest.approx(value), (
        f"{agent}:{path} is {contract_value}, README claims {value}"
    )
    assert phrase in _readme(), f"README no longer states {phrase!r}"


def test_envelope_limits_quoted_are_real() -> None:
    envelope = yaml.safe_load((ROOT / "src/policies/safety-envelope.yaml").read_text(encoding="utf-8"))
    limits = envelope["limits"]
    assert limits["wellbore"]["max_dls_per_100ft"] == pytest.approx(5.0)
    assert "5.0 deg/100 ft limit" in _readme()
    assert limits["probabilistic"]["min_data_quality_to_act"] == pytest.approx(0.95)
    assert "Below 0.95 the sample is not actionable" in _readme()


def test_the_counts_quoted_are_real() -> None:
    sys.path.insert(0, str(ROOT / "servers"))
    from advisory_core import formulas as fm

    # Same filter the server uses to build its tool list, so the count is the real one.
    computable = [
        name for name, obj in vars(fm).items()
        if inspect.isfunction(obj) and not name.startswith("_") and obj.__module__ == fm.__name__
    ]
    assert len(computable) == 31, f"{len(computable)} formulas, README says 31"
    assert "31 formulas" in _readme()

    contracts = list((ROOT / "src/agents").glob("*.yaml"))
    assert len(contracts) == 17
    assert "17 agent contracts" in _readme()

    skills = list((ROOT / "skills").glob("*/SKILL.md"))
    assert len(skills) == 10
    assert "10 Agent Skills" in (ROOT / "README.md").read_text(encoding="utf-8")
