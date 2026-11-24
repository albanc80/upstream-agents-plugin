---
name: data-quality-and-standards
description: Gate every drilling answer behind data quality and byte-level correctness — the six-check quality score, the 0.95 act floor, units and mnemonics, WITSML and ETP channel identity, timestamp and sequence handling. Use before any numeric interpretation of real-time data, whenever a channel looks flat, drifted, stale, out of sequence or in unexpected units, when two sources disagree, or when mapping a vendor curve to a standard name.
---

# Data Quality and Standards

Every other skill inherits this one. An answer built on bad data is worse than no answer,
because it looks authoritative.

## The gate

A sample is actionable only above a quality score of **0.95**. Below that, the correct
output is a description of the defect, not an interpretation of the value.

Six checks produce that score:

| Check | Fails when | Flag |
|---|---|---|
| Physics bounds | value outside the channel's hard limits | PHYSICALLY_INVALID (score 0) |
| Sequence | packet older than the last one seen | OUT_OF_SEQUENCE (x0.4) |
| Drift | redundant sensors spread beyond tolerance | DRIFT_DETECTED (x0.5) |
| Outlier | value beyond a modified z-score of 3.5 | OUTLIER (x0.5, replaced by median) |
| Completeness | less than 90 % of expected samples in the last 60 s | INCOMPLETE (proportional) |
| Voting | redundant sensors disagree | single ground-truth value chosen |

## Procedure

1. Score first. Call `qse_score_sample` per channel; never assume timestamps are fine.
2. Interpret the defect before the value. Flat line, step change, mirrored pair, or cadence
   gap each mean something different.
3. Check units and mnemonics before comparing anything. `TG` is total gas in %; `TPV` is
   active pit volume in bbl; a vendor's `GAS` may be a fraction.
4. Reconcile sources explicitly. WITSML 1.4.1.1 and ETP 1.2 are separate paths and can
   disagree; name which one the number came from.
5. State the gate result in the answer, taken from the tool: "quality 0.99, actionable" or
   "quality 0.62, not actionable — here is what is wrong".

## Refusal sentences

- "Quality is 0.62, below the 0.95 floor. I can describe the defect, not interpret the value."
- "These two series are not the same quantity — one is a fraction, one is a percentage."
- "This channel stopped updating 4 minutes ago; anything derived from it is stale."
- "I can't map this mnemonic with confidence. Confirm the vendor curve before I use it."

## Degraded mode

Without the advisory server, apply the checks qualitatively and label the result an inspection,
not a score. First try the shell fallback in `upstream-ops`: `--call qse_score_sample` returns the
same JSON the tool would. Never emit a number between 0 and 1 that you did not receive from the tool.

## Calibration check — do this before quoting any number

Every threshold in this pack is either transcribed from a reference implementation, authored here,
or an **industry default standing in for this well's or this operator's value**. Call
`list_calibration` and include the defaults in force in your answer, in plain words: *"these are
industry averages, not your well's numbers."*

Never present a default as a site value, a company SOP, or a regulatory limit. If the user needs a
number that is theirs — kick tolerance, loss classes, flow or pressure ceilings, mud weight window,
stuck-pipe weighting, design factors — say what the default is, that it is a default, and what to
replace it from.
