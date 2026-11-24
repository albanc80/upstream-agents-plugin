# Review brief — thresholds

For a reviewer with drilling/well-control background. **You are not reviewing code, and you are not
re-reviewing what has already been fixed.** Section 1 is what changed since the last review, so you
do not spend time on it. Section 2 is what still needs your judgement: numbers that are
company-policy questions this pack deliberately does not decide.

Status: `site_validated: false`. Nothing here is used on a live well until you sign off the numbers.

---

## 1 - What the code now does (settled - please skip)

The previous review found the pack's *behaviour* contradicting its own documentation. Those are
closed, each with a regression test.

| Was | Now |
|---|---|
| Losses lowered the kick score and read Normal | Masses floored at 0. Losses follow their own ladder (2 bbl Advisory, 5 bbl Alert), classified `LOST_CIRCULATION` |
| A loss with gas or excess flow read as a plain loss | Escalates to **level 4**, classified `UNDERGROUND_FLOW_SUSPECTED` - the underground-flow signature |
| `weight_on_bit` bypassed the envelope; unknown names passed | Fails closed: channel ids and unit suffixes resolve to their limits; anything unresolvable - **or resolvable with no configured limit** - is refused as uncertifiable |
| Mud weight was never checked, only ECD | `mud_weight` is checked against the 9.0-14.5 ppg window in its own right |
| Emergency returned `classification: NORMAL` | An escalation is never labelled Normal; classification comes from the same evidence as the level |
| 2.00 bbl was Monitor but 2.01 bbl was Alert | Volume overrides compare `>=`; the autonomy ceiling is inclusive at 0.60 too |
| 0.4% gas - below the 0.5% background - still added mass | Background is **subtracted**: sub-background gas contributes nothing |
| Gas and flow combined by `max()`, so agreement earned nothing | Combined as noisy-OR: 2% gas with +5 gpm now outranks gas alone |
| One signal alone reached Emergency (PWD 3 sigma, 5 bbl, 10 gpm) | PWD alone is capped at Alert, gas alone at Advisory. Emergency needs corroboration or a volume override |
| A bare QSE sample scored 1.0 and was actionable | `UNVERIFIED_CHECKS`, not actionable, when no observation window is supplied |
| 57/60 samples = 0.95 was flagged OK but not actionable | The floor is inclusive at its own value |
| `kick_probability` read as a calibrated probability | Primary field is **`kick_score`** (`kick_probability` kept as a deprecated alias). A positive flow check with pumps off forces level 4 whatever the score |

If any of these is still misbehaving, that is a defect - say so and it gets fixed, not debated.

## 2 - What still needs your judgement

Where a number is in the pack it is transcribed from a reference implementation, authored here, or
an **industry-average default standing in for your policy**. Defaults are listed in
`src/policies/safety-envelope.yaml` under `calibration`, and every tool answer carries
`defaults_in_use` plus a `calibration_note` naming them, so nothing is silently a guess.

### 2.0 Defaults in force - replace these

| Key | Default | Basis | Replace from |
|---|---|---|---|
| `pit_gain.kick_tolerance_fraction` | 0.5 | half the section's kick-tolerance volume | well-control policy, per section |
| `losses.seepage_max_bbl_hr` / `partial_max_bbl_hr` | 10 / 50 | published agreement on seepage; midpoint of 30/50/100 | operator loss-classification standard |
| `max_flow_rate_gpm` | 500 | conservative operator default, below many rigs' pump rate | the rig's pump schedule — expect to raise |
| `min_data_quality_to_act` | 0.95 | **unverified** - measurement deferred, no live rig data available yet | per-channel distributions from recorded data |
| `mud_weight_window` | 9.0-14.5 ppg | fixed window; wrong basis for water, brine and HPHT | pore pressure + overbalance to frac gradient minus margin, per section |

**Until these are replaced, every answer is an industry-average answer.** That is the honest reading
of `site_validated: false`.

### 2.1 The basis of escalation

| Question | Where it stands |
|---|---|
| Should a shut-in proposal rest on evidence rather than a fused score? | Partly implemented: a positive flow check with pumps off forces level 4 regardless of score. The score still sets levels 0-3. **Should any unexplained pit gain also force a shut-in proposal, independent of score?** |
| Is a fixed 2 / 5 bbl pit gain defensible across hole sizes? | Fixed 2/5 bbl still sets the level, but the tool now reports `influx_height_ft` when hole geometry is supplied (5 bbl is ~18 ft in 17.5-inch hole, ~109 ft in 8.5-inch) and enforces a **volumetric cap** when `kick_tolerance_volume_bbl` is passed: exceeding 0.5 x kick tolerance escalates to Emergency. The 0.5 is a default - confirm your own fraction and pass your section volumes. |
| Is the 0.02 EMA on pit baseline acceptable? | Still present. At 1 Hz that is a ~50 s time constant, so a slow gain is absorbed into the reference. **Recommend freezing the reference at last known-good state instead - confirm.** |

### 2.2 Loss classes

Authored boundaries: seepage < 10 bbl/hr, partial 10-50 bbl/hr, severe >= 50 bbl/hr; losses cap at
level 3 (a losing well is treated, not shut in); loss plus any gain goes to level 4.
**Published classes agree only on "seepage < 10 bbl/hr" and disagree above it (30 / 50 / 100 / 200).
Pick your operator numbers.**

### 2.3 Per-section equipment limits

Currently global rules of thumb, which is wrong for at least half of them:

| Value | Why it needs you |
|---|---|
| `max_wob_klbs` 40 | Large-hole PDC often needs more; 6.125-inch needs far less |
| `max_rpm` 180 | Surface or bit RPM? Limit is motor/BHA/pipe plus the vibration envelope |
| `max_standpipe_pressure_psi` 4000 | Many rigs run 5000 psi; deep 8.5-inch sections exceed 4000 |
| `max_torque_ft_lbs` 15000 | Likely below make-up torque for 5-inch+ connections - would block normal work |
| `mud_weight_window` 9.0-14.5 ppg | Blocks water/brine and HPHT alike. Should be pore pressure + overbalance to frac gradient minus margin, per depth |
| `max_dls_per_100ft` 5.0 | Unconventional curves are planned above this; casing/ESP intervals need less |
| `max_flow_rate_gpm` 500 | **Authored here** - the reference defines none. Deliberately conservative: it will refuse high-rate proposals until replaced |
| `min_data_quality_to_act` 0.95 | A feed dropping 3 samples/min fails it. Measure from recorded rig data, per channel, with hysteresis; for well control, low quality should escalate rather than block |
| `min_confidence_for_action` 0.75 | Meaningless without a reliability curve on held-out cases. Until then, require human confirmation for every parameter change |
| `h2s_alarm_ppm` 10 | Common first alarm; BSEE 30 CFR 250.490 builds required actions around 20 ppm. Confirm the jurisdiction before calling 10 "regulatory" |

### 2.4 Agent constants

| Area | Question |
|---|---|
| Stuck pipe weighting 0.40 torque / 0.30 overpull / 0.20 overbalance / 0.10 inclination | Torque-led weighting understates differential sticking. Weight by mechanism instead? |
| Overbalance floor 3.0 ppg | If this is a floor, the term is zero on most wells and differential sticking is invisible. Confirm the intended semantics |
| Veto at risk >= 60 | Should it also block reduced flow under pack-off risk, stopped rotation, extended stationary time? |
| Alternative "WOB -3 klbf, RPM +10" | Wrong as a generic: pack-off wants flow and rotation, differential sticking wants overbalance reduced, geometry wants reaming. Replace with "do not add WOB; keep circulating and moving pipe; call the driller"? |
| ECD warn at 0.9 x FG | Gives 1.6 ppg of margin at 16 ppg FG but 1.1 ppg at 11 ppg. Use absolute ppg margins like `ecd_fg_min_margin` 0.3? |
| CTR 0.55 / 0.40 | Vertical-well concept; above ~30 deg inclination cuttings beds govern. Deviated-hole model? |
| Casing DF 1.1 burst / 1.0 collapse / 1.3 tension | Tension 1.3 is low if applied to API joint strength (many use ~1.6). Confirm the basis, add triaxial/VME? |
| Cementing density delta 0.5 ppg, pressure delta 10%, ZIA 0.7 / 0.5 | 0.5 ppg is loose against normal slurry density control; ZIA cut-offs are arbitrary until calibrated against bond logs |
| Geosteering 9,000-9,400 ft, 50 ft, 1 ft | One well's placeholders - refuse to run without a target from the well plan? |
| Optimisation WOB 3 klbf / RPM 5 / vibration 0.7 / 2% | 2% ROP is inside formation noise. Require persistence over footage, net of MSE and vibration cost? |
| Directional WSF 1.5 / 1.0, 25 ft, 5 ft | Matches common ISCWSA practice, but for high-consequence offsets 1.5 is often the stop. Confirm |

## 3 - What was checked and holds

Transcription is consistent: every value quoted here matches `docs/THRESHOLDS-TRACE.md` and the live
`thresholds_used` block. Ladders are monotonic, weight sets sum to 1.0, advisory design factors sit
above their minimums, and the negotiation stage timeouts (500 + 400 + 600 + 500 ms) sum to the
2,000 ms window.

**Deferred by decision:** the 0.95 data-quality floor stays a default because calibrating it needs
per-channel distributions from recorded rig data, and there is no access to live rig systems yet. It
is labelled unverified in the calibration block rather than presented as measured.

Known gaps, stated rather than hidden: fusion constants now have trace rows but their per-line
references are not individually confirmed; several values are duplicated across the reference
implementation's modules (this pack keeps one policy file, so copies cannot drift); geometry defaults
conflict between agents (12.25-inch cementing vs 8.5-inch hydraulics) and are placeholders; the lift
gap between rod pump 400 stb/d and ESP 1,000 stb/d is not covered.

## 4 - The four answers worth giving first

1. **Kick-tolerance fraction** for the pit-gain volumetric cap. Without it, 2/5 bbl stays fixed.
2. **Loss classification boundaries** - your operator's seepage / partial / severe split in bbl/hr.
3. **Per-section equipment limits** - WOB, RPM (surface or bit), SPP, torque, DLS, mud window basis.
4. **Whether any unexplained pit gain forces a shut-in proposal** regardless of score.

## Out of scope

Code, packaging, agent prompt wording, the MCP transport. Reviewed five times; not your time.
