# Review brief — thresholds

For a reviewer with drilling/well-control background. **You are not reviewing code.** You are
reviewing whether each number is right for the context it is applied in, and whether its
consequence is proportionate. Every value below is transcribed verbatim from a private reference
implementation (`docs/THRESHOLDS-TRACE.md` carries the `module:line` for each), so transcription is
not in question — judgement is.

Three categories, in priority order. Please answer per item: **OK / ADJUST to ___ / WRONG because ___**.

---

## 1. The numbers that decide "shut in or keep drilling"

These are the highest consequence: if one is wrong in the permissive direction, a real influx reads
as normal.

| Value | Where | Question for you |
|---|---|---|
| `kick_probability` 0.20 / 0.40 / 0.60 / 0.85 | alert ladder monitor → advisory → alert → emergency | Is a *probability* the right basis for the escalation at all, or should any pit gain with pumps off force the alert regardless of the score? |
| `pit_gain.advisory_bbl` 2.0, `emergency_bbl` 5.0 | hard overrides to levels 3 and 4 | Are 2 and 5 bbl the right trip/pump-off pit gain triggers **for a 12¼" hole**? Should these scale with hole size or be a fraction of annular volume instead of a fixed barrel count? |
| `background_gas_pct` 0.5 | gas mass baseline | With connection gas routinely 1–2% on some wells, does 0.5% make every connection an alert? What baseline do you actually use? |
| `max_kick_probability_for_autonomy` 0.60 | blocks any parameter change above this | Is 0.60 the right point to freeze optimisation, or should *any* positive pit gain already freeze it? |
| `min_data_quality_to_act` 0.95 | gate: below this, no answer is actionable | **Is 0.95 achievable with real rig sensors, or does this block everything in practice?** This is the one most likely to make the pack unusable. |
| *no loss threshold exists* | losses currently escalate to Advisory and are labelled `LOST_CIRCULATION`, with a note that the contract defines none | What loss rate or cumulative pit loss should escalate, and to which level? We deliberately did not invent a number. |

### Fusion scaling (the same category, needs your physics)

Each signal is mapped to a 0–1 mass and combined. The divisors set how fast a signal saturates:

- PWD residual `sigma / 3.0 × 0.90` — is 3σ the right full-scale?
- pit gain `bbl / 5.0 × 0.95` — 5 bbl gives near-full mass; too sensitive for a large hole?
- gas `pct / (5 × 0.5) × 0.70` and flow `gpm / 10.0 × 0.80` — are 10 gpm and 2.5% sensible half-scales?

---

## 2. Limits applied as hard blocks on every proposed change

A limit set too low blocks legitimate work (operational failure); too high fails to protect the
string. All are currently global, i.e. not per-hole-size or per-section.

| Value | Question |
|---|---|
| `max_wob_klbs` 40 · `max_rpm` 180 · `max_standpipe_pressure_psi` 4000 · `max_torque_ft_lbs` 15000 | Are these rig/tool limits or rules of thumb? Which of them are safe as a global ceiling, and which must be per-section? |
| `mud_weight_window` 9.0–14.5 ppg | Is a fixed window meaningful, or should it be pore–frac derived per well? |
| `max_dls_per_100ft` 5.0 | OK as a ceiling for a motor/BHA? |
| `h2s_alarm_ppm` 10.0 | Matches your alarm philosophy? |
| `min_confidence_for_action` 0.75 | Any objection to an agent acting at 0.75 on a parameter change? |

---

## 3. Agent-specific constants worth a sanity check

| Area | Values | Question |
|---|---|---|
| Stuck pipe | weights torque 0.40 / overpull 0.30 / overbalance 0.20 / inclination 0.10; scales 6,000 ft·lbf, 60 klbf; **veto at risk ≥ 60**; standard alternative **WOB −3 klbf, RPM +10** | Is torque-dominant weighting right for your wells? Is 60 the right veto point? Is "less WOB, more RPM" a sound generic response, or does it depend on the mechanism (differential sticking wants overbalance reduced, not WOB)? |
| Directional | WSF 1.5 caution / 1.0 mandatory stop; collision boundary 25 ft; min survey spacing 5 ft | Are these your company's separation rules or generic? |
| Hydraulics/fluids | ECD warn at 0.9 × frac; overbalance min 0.2 ppg; ECD–FG min margin 0.3 ppg; CTR adequate 0.55 / deficit 0.40 | Do those margins match practice on your fields? |
| Casing | design factors burst 1.1 / collapse 1.0 / tension 1.3; advisory 1.2 / 1.1 | Standard DF basis? |
| Cementing | channeling density Δ 0.5 ppg, pressure Δ 10%, ZIA pass 0.7 / fail 0.5 | Are the ZIA cut-offs meaningful or arbitrary? |
| Geosteering | target window 9,000–9,400 ft TVD, exit warning 50 ft, auto TVD correction 1 ft | Placeholders from one well — obviously not universal |
| Optimisation | WOB auto delta 3 klbf, RPM +5, vibration 0.7, min improvement 2%, bit size 8.5" | Is a 2% ROP improvement worth a change? |

---

## What to ignore

Code, packaging, agent prompt wording, the MCP transport. Not your scope, already reviewed four
times.

## What I would ask you to answer first, if you only have an hour

1. Is the **pit-gain** basis (fixed 2 and 5 bbl) defensible across hole sizes, or must it be
   volumetric?
2. Is **data quality 0.95** realistic against real sensor behaviour?
3. What **loss** threshold should exist, given the contract has none?
4. Is a **probability score** an acceptable basis for a shut-in recommendation at all, or should the
   ladder be evidence-driven (pit gain, flow with pumps off, gas) rather than score-driven?

Nothing in this package is used on a live well until `site_validated` stops being `false`. This
review is the step that would start that.
