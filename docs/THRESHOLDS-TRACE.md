# Threshold provenance

> Values marked **authored here** were not transcribed from the reference implementation: it
> defines nothing at that key. They exist so a gap could not silently pass as a decision, they
> carry no pedigree, and they are listed under `authored_limits` in
> `src/policies/safety-envelope.yaml`. They need a rig-specific answer before site use.



Every number in `src/agents/` and `src/policies/` is transcribed from the author's private

reference implementation, which is **not** part of this package. The `Source` column gives the

module and line in that implementation at extraction time.



Why keep the line references at all: they are the difference between a number with an origin

and a number someone typed. They let the implementation and this package be re-audited against

each other after any change. They are not links a reader can follow — the implementation is

private — so treat a row as "this value came from that routine", not as a citation you can

open.



`tools/validate.py` fails if a contract threshold key has no row here.



## `well-control-monitoring-agent`

| Value | Source |
|---|---|
| `kick_probability.monitor` 0.20 | `agents/well_control_agent.py:24` |
| `kick_probability.advisory` 0.40 | `agents/well_control_agent.py:23` |
| `kick_probability.well_control_alert` 0.60 | `agents/well_control_agent.py:24` |
| `kick_probability.emergency` 0.85 | `agents/well_control_agent.py:25` |
| **fusion** PWD `sigma / 3.0 x 0.90` | weight set `agents/well_control_agent.py:237`; per-line reference not individually confirmed |
| **fusion** pit `bbl / 5.0 x 0.95` | same weight set; unconfirmed per line |
| **fusion** gas `(pct - background) / (5 x background) x 0.70` | same weight set; background subtracted as of 1.1.8 |
| **fusion** flow `gpm / 10.0 x 0.80` | same weight set; unconfirmed per line |
| **fusion** gas and flow combine as noisy-OR, not max | behaviour change 1.1.8 |
| **fusion** single-signal caps: PWD -> Alert, gas -> Advisory | authored here: one signal must not reach Emergency alone |
| `pit_gain.advisory_bbl` 2.0 | `agents/well_control_agent.py:27` |
| `pit_gain.emergency_bbl` 5.0 | `agents/well_control_agent.py:28` |
| `pit_baseline_ema_alpha` 0.02 | `agents/well_control_agent.py:31` |
| `background_gas_pct` 0.5 | `agents/well_control_agent.py:29` |
| alert ladder 0-4 names | `agents/well_control_agent.py:33-40` |
| veto trigger `kick_probability > 0.60` | `agents/well_control_agent.py:250` |
| veto trigger `alert_level >= 3` | `agents/well_control_agent.py:249` |
| tier SAFETY (1) | `data/proposals.py:22` |
| confidence weights 0.4/0.2/0.2/0.2 | `agents/well_control_agent.py:237` |

## `stuck-pipe-prevention-agent`

| Value | Source |
|---|---|
| `risk_score.advisory` 25.0 | `agents/stuck_pipe_agent.py:25` |
| `risk_score.active` 40.0 | `agents/stuck_pipe_agent.py:26` |
| `risk_score.immediate` 60.0 | `agents/stuck_pipe_agent.py:27` |
| `risk_score.critical` 80.0 | `agents/stuck_pipe_agent.py:28` |
| `baseline_ema_alpha` 0.05 | `agents/stuck_pipe_agent.py:29` |
| `scales.torque_ft_lbs` 6000.0 | `agents/stuck_pipe_agent.py:30` |
| `scales.overpull_klbf` 60.0 | `agents/stuck_pipe_agent.py:31` |
| `weights.torque` 0.40 | `agents/stuck_pipe_agent.py:135` |
| `weights.overpull` 0.30 | `agents/stuck_pipe_agent.py:136` |
| `weights.overbalance` 0.20 | `agents/stuck_pipe_agent.py:137` |
| `weights.inclination` 0.10 | `agents/stuck_pipe_agent.py:138` |
| `scales.overbalance_floor_ppg` 3.0 | `agents/stuck_pipe_agent.py:129` |
| `scales.overbalance_span_ppg` 2.0 | `agents/stuck_pipe_agent.py:129` |
| `time_to_stuck_min.floor` 5.0 | `agents/stuck_pipe_agent.py:144` |
| `time_to_stuck_min.span` 90.0 | `agents/stuck_pipe_agent.py:144` |
| veto `risk >= 60`, wob increase only | `agents/stuck_pipe_agent.py:233-238` |
| alternative `wob -3.0`, `rpm +10.0` | `agents/stuck_pipe_agent.py:249-252` |
| tier NPT (2) | `data/proposals.py:23` |

## `safety-envelope`

| Value | Source |
|---|---|
| `mud_weight_window` 9.0 / 14.5 ppg | `config.py:104-105` |
| `max_wob_klbs` 40.0 | `config.py:106` |
| `max_rpm` 180 | `config.py:107` |
| `max_standpipe_pressure_psi` 4000.0 | `config.py:108` |
| `max_torque_ft_lbs` 15000.0 | `config.py:109` |
| `max_flow_rate_gpm` 1000.0 | **authored here** — the reference defines none; operator placeholder |
| `losses.advisory_bbl` 2.0 / `alert_bbl` 5.0 | **authored here** — mirrors the pit-gain ladder; reference defines none |
| `losses.flow_equivalent_gpm_per_bbl` 42.0 | **authored here** — sizes a flow-only loss as bbl over one minute |
| `max_dls_per_100ft` 5.0 | `config.py:110` |
| `h2s_alarm_ppm` 10.0 | `config.py:111` |
| `min_confidence_for_action` 0.75 | `config.py:112` |
| `max_kick_probability_for_autonomy` 0.60 | `config.py:113` |
| `min_data_quality_to_act` 0.95 | `config.py:93` |
| evaluation order + hard-violation set | `safety/safety_envelope.py:83-162` |
| channel-to-parameter map | `safety/safety_envelope.py:19-26` |

## `veto-matrix`

| Value | Source |
|---|---|
| four tiers 1-4 | `data/proposals.py:19-26` |
| tie-break by confidence | `orchestration/priority_hierarchy.py:15-24` |
| `window_ms` 2000 | `config.py:98` |
| stage timeouts 500/400/600/500 | `config.py:99-103` |
| four stages, four outcomes | `orchestration/negotiation_protocol.py:1-12` |
| promotion 0.85 / 50 cycles | `config.py:117` |
| demotion 0.70 / 10 cycles | `config.py:118-119` |
| routing thresholds 0.85 / 0.70 | `config.py:122-123` |
| routing logic | `safety/autonomy_manager.py:194-202` |

## Remaining agents (extracted batch 1)

Same provenance rule: each value is a module-level constant in the cited file.

| Value | Source |
|---|---|
| `min_burst_df` 1.1 | `agents/casing_agent.py:29` |
| `min_collapse_df` 1.0 | `agents/casing_agent.py:30` |
| `min_tension_df` 1.3 | `agents/casing_agent.py:31` |
| `advisory_burst_df` 1.2 | `agents/casing_agent.py:32` |
| `advisory_collapse_df` 1.1 | `agents/casing_agent.py:33` |
| `drag_deviation_alert` 0.15 | `agents/casing_agent.py:34` |
| `baseline_alpha` 0.05 | `agents/casing_agent.py:35` |
| `default_mw_ppg` 12.5 | `agents/casing_agent.py:37` |
| `channeling_density_delta_ppg` 0.5 | `agents/cementing_agent.py:26` |
| `channeling_pressure_delta_frac` 0.1 | `agents/cementing_agent.py:27` |
| `pressure_alert_above_design_psi` 200.0 | `agents/cementing_agent.py:28` |
| `zia_pass` 0.7 | `agents/cementing_agent.py:29` |
| `zia_fail` 0.5 | `agents/cementing_agent.py:30` |
| `hole_diameter_in` 12.25 | `agents/cementing_agent.py:33` |
| `casing_od_in` 9.625 | `agents/cementing_agent.py:34` |
| `gpm_per_bbl_min` 42.0 | `agents/cementing_agent.py:35` |
| `zia_gate` 0.7 | `agents/completions_agent.py:25` |
| `max_clusters_per_stage` 5 | `agents/completions_agent.py:26` |
| `min_cluster_spacing_ft` 40.0 | `agents/completions_agent.py:27` |
| `rod_pump_max_stb_d` 400.0 | `agents/completions_agent.py:28` |
| `esp_min_stb_d` 1000.0 | `agents/completions_agent.py:29` |
| `wsf_caution` 1.5 | `agents/directional_steering_agent.py:25` |
| `wsf_mandatory_stop` 1.0 | `agents/directional_steering_agent.py:26` |
| `collision_boundary_ft` 25.0 | `agents/directional_steering_agent.py:27` |
| `lateral_offset_limit_ft` 50.0 | `agents/directional_steering_agent.py:28` |
| `min_survey_spacing_ft` 5.0 | `agents/directional_steering_agent.py:33` |
| `wob_auto_delta_klbf` 3.0 | `agents/drilling_optimization_agent.py:24` |
| `rpm_auto_delta` 5.0 | `agents/drilling_optimization_agent.py:25` |
| `vibration_threshold` 0.7 | `agents/drilling_optimization_agent.py:26` |
| `min_improvement_pct` 2.0 | `agents/drilling_optimization_agent.py:27` |
| `bit_size_in` 8.5 | `agents/drilling_optimization_agent.py:28` |
| `default_api_filtrate_ml` 3.5 | `agents/fluids_agent.py:21` |
| `default_kcl_g_per_l` 35.0 | `agents/fluids_agent.py:22` |
| `default_phpa_lb_bbl` 1.0 | `agents/fluids_agent.py:23` |
| `default_water_activity` 0.95 | `agents/fluids_agent.py:24` |
| `default_pv_cp` 20.0 | `agents/fluids_agent.py:25` |
| `default_yp_lb_100ft2` 15.0 | `agents/fluids_agent.py:26` |
| `mw_pp_min_overbalance` 0.2 | `agents/fluids_agent.py:28` |
| `ecd_fg_min_margin` 0.3 | `agents/fluids_agent.py:29` |
| `fg_margin_above_emw_max` 0.3 | `agents/fluids_agent.py:30` |
| `max_filter_cake_mm` 3.0 | `agents/fluids_agent.py:31` |
| `min_shale_inhibition` 0.6 | `agents/fluids_agent.py:32` |
| `approaching_margin_ppg` 0.3 | `agents/fluids_agent.py:33` |
| `default_target_top_tvd` 9000.0 | `agents/geosteering_agent.py:28` |
| `default_target_base_tvd` 9400.0 | `agents/geosteering_agent.py:29` |
| `auto_tvd_correction_ft` 1.0 | `agents/geosteering_agent.py:30` |
| `exit_warning_ft` 50.0 | `agents/geosteering_agent.py:31` |
| `flow_auto_delta_gpm` 50.0 | `agents/hydraulics_agent.py:19` |
| `ctr_adequate` 0.55 | `agents/hydraulics_agent.py:20` |
| `ctr_deficit` 0.4 | `agents/hydraulics_agent.py:21` |
| `ecd_warn_fraction_of_fg` 0.9 | `agents/hydraulics_agent.py:22` |
| `fg_margin_above_emw_max` 0.3 | `agents/hydraulics_agent.py:23` |
| `hole_diameter_in` 8.5 | `agents/hydraulics_agent.py:25` |
| `pipe_diameter_in` 5.0 | `agents/hydraulics_agent.py:26` |
| `slip_velocity_ft_min` 45.0 | `agents/hydraulics_agent.py:27` |
| `gpm_per_bbl_min` 42.0 | `agents/hydraulics_agent.py:28` |
| `sw_net_pay_max` 0.65 | `agents/lwd_agent.py:23` |
| `porosity_net_pay_min` 0.08 | `agents/lwd_agent.py:24` |
| `show_rt_min_ohmm` 20.0 | `agents/lwd_agent.py:25` |
| `show_sw_max` 0.5 | `agents/lwd_agent.py:26` |
| `min_actionable_quality` 0.95 | `agents/mwd_agent.py:21` |
| `uncertainty_fraction_of_md` 0.005 | `agents/mwd_agent.py:23` |
| `uncertainty_floor_ft` 5.0 | `agents/mwd_agent.py:24` |
| `turner_loading_factor` 1.2 | `agents/production_agent.py:29` |
| `eur_reforecast_variance` 0.2 | `agents/production_agent.py:30` |
| `scp_rise_alert_psi` 30.0 | `agents/production_agent.py:31` |
| `scp_bsee_flag_psi` 100.0 | `agents/production_agent.py:32` |
| `velocity_per_stb_d` 0.01 | `agents/production_agent.py:35` |
| `surface_tension_dyne_cm` 60.0 | `agents/production_agent.py:36` |
| `liquid_density_lb_ft3` 67.0 | `agents/production_agent.py:37` |
| `gas_density_lb_ft3` 2.7 | `agents/production_agent.py:38` |
| `ema_alpha` 0.05 | `agents/production_agent.py:39` |
| `ecd_warning_fraction_of_fg` 0.9 | `agents/pwd_agent.py:23` |
| `ecd_critical_fraction_of_fg` 0.95 | `agents/pwd_agent.py:24` |
| `kick_sigma_threshold` 3.0 | `agents/pwd_agent.py:25` |
| `fg_margin_above_emw_max` 0.3 | `agents/pwd_agent.py:26` |
| `mw_pp_min_overbalance` 0.2 | `agents/pwd_agent.py:27` |
| `ecd_fg_min_margin` 0.3 | `agents/pwd_agent.py:28` |
| `screenout_rise_psi_per_min` 500.0 | `agents/stimulation_agent.py:24` |
| `screenout_sustained_readings` 3 | `agents/stimulation_agent.py:25` |
| `maop_alert_fraction` 0.95 | `agents/stimulation_agent.py:27` |
| `min_ecd_to_fg_margin` 0.3 | `agents/well_planning_agent.py:26` |
| `min_mw_to_pp_margin` 0.2 | `agents/well_planning_agent.py:27` |
| `target_top_tvd` 9000.0 | `agents/well_planning_agent.py:28` |
| `target_base_tvd` 9400.0 | `agents/well_planning_agent.py:29` |
| `free_pipe_amp_mv` 60.0 | `agents/wireline_agent.py:24` |
| `cemented_amp_mv` 5.0 | `agents/wireline_agent.py:25` |
| `bond_good` 0.8 | `agents/wireline_agent.py:26` |
| `bond_pass` 0.6 | `agents/wireline_agent.py:27` |
