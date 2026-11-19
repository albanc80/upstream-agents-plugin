---
name: drilling-optimization
description: Raise rate of penetration without buying a dysfunction — founder point, mechanical specific energy, torque and drag signatures, stick-slip and whirl diagnosis, WOB and RPM trade-offs. Use when asked to improve ROP, explain a slow section, interpret MSE or a founder test, choose WOB and RPM, or judge whether an optimisation will trigger vibration, balling or stick-slip.
---

# Drilling Optimisation

The objective is the lowest cost per foot, not the highest instantaneous ROP. Optimisation
that trades a dysfunction for a rate is a loss.

## Procedure

1. **Check the data.** Torque, WOB, RPM, flow and ROP at usable quality, over a steady
   interval. A founder test on unsteady data measures noise.
2. **Compute MSE, not intuition.** Call `compute teale_mse_psi`. Rising MSE at flat ROP is the
   founder point — additional WOB is buying heat, not hole.
3. **Identify the dysfunction before changing anything.** Stick-slip (torque oscillation,
   RPM fluctuation), whirl (lateral vibration, erratic torque), bit balling (torque up,
   ROP down, pump pressure up), or a clean founder.
4. **Trade along the known direction.** For stick-slip, RPM up and WOB down. For balling,
   flow and hydraulics first. For a true founder, back off WOB and hold RPM.
5. **Check who else is exposed.** Any WOB or RPM increase is a `parameter_change`: run
   `check_safety_envelope`, and expect the stuck-pipe movement veto above a risk score of 60.
   Say so before recommending it.
6. **State the expected delta and how you would know it failed.** A recommendation without a
   falsifier is a slogan.

## Refusal sentences

- "I won't raise WOB on these indicators — stuck-pipe risk is above the veto threshold."
- "MSE isn't available, so I can't locate the founder point. Here is what would tell us."
- "That parameter change crosses the envelope; it isn't a matter of preference."
- "Optimising through a vibration flag trades bit life for a rate I can't verify."

## Degraded mode

Without the advisory server, discuss the physics and the decision logic, and say plainly that
MSE and the founder point were not computed. Never quote an MSE value you did not receive.
