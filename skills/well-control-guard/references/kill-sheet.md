# Kill-sheet quantities

Definitions the tool computes (engine module `safety/physics_models.py`). Listed so you know
what to ask for and what each one requires — not so you can reproduce it by hand.

| Quantity | Needs | Note |
|---|---|---|
| Pressure gradient | mud weight (ppg) | `gradient = MW x 0.052` psi/ft |
| Hydrostatic pressure | MW, TVD | `MW x 0.052 x TVD` |
| Formation pressure | SIDPP, MW, TVD | `SIDPP + hydrostatic` |
| Kill mud weight | current MW, SIDPP, TVD | `MW + SIDPP / (0.052 x TVD)` |
| MAASP | envelope MW max, current MW, casing-shoe TVD | `(MW_max - MW) x 0.052 x shoe TVD` |
| Initial circulating pressure | SIDPP, slow circulating rate pressure | `ICP = SIDPP + SCR` |

## Rules

- Every input above is a **measured** value. An assumed SIDPP produces a useless kill weight.
- TVD, not MD. If only MD is available, say the answer is approximate and name the error.
- MAASP uses the **shoe** TVD of the open-hole section, and must be recomputed when the mud
  weight changes.
- Gas in the annulus makes ECD and MAASP read optimistic: there is no mud/gas model, so
  never call an ECD margin conservative during a gas event.

## Alert ladder

| Level | Name | Meaning |
|---|---|---|
| 0 | Normal | No anomaly |
| 1 | Monitor | Weak signal, watch |
| 2 | Advisory | Probable anomaly, inform |
| 3 | Well Control Alert | Confirmed event, escalate and notify |
| 4 | Emergency Shut-In Proposal | Severe, human decides shut-in |

Fusion weights: PWD residual (primary), pit gain (secondary), gas or flow differential
(tertiary). Background gas is 0.5 %; the advisory floor is a 2 bbl pit gain.
