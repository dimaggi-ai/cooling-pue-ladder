# References

Every constant and claim in the model traces to one of these. Company
figures are quoted as published facts; US-government-funded (DOE
national lab) reports are publicly released, and only facts and figures
are quoted from them; survey headline numbers are cited as facts.
Where a value is a planning assumption with no single anchor, the code
labels it as such and it appears in "What a skeptic should attack."

- **[1] PUE definition.** The Green Grid, "PUE: A Comprehensive Examination
  of the Metric" (WP#49), standardized as ISO/IEC 30134-2. PUE = total
  facility energy / IT equipment energy; ≥ 1.0 by construction.
- **[2] Industry survey averages.** Uptime Institute Global Data Center
  Survey series: average PUE ~1.7 (2014 era) falling to ~1.55-1.6 and
  plateauing there since ~2020 (2023: ~1.58; 2024: ~1.56). Survey averages
  are per-respondent (site-count-weighted), not energy-weighted — the
  distinction the two-fleets simulation is about.
- **[3] Google fleet PUE/WUE.** Google publishes a trailing-twelve-month
  fleet-wide PUE of ~1.09-1.10 (2023: 1.10; 2024: 1.09; best campuses
  ~1.04-1.06) and a fleet WUE on the order of ~1 L/kWh.
  Company-published figures, quoted as facts.
- **[4] Meta fleet PUE.** Meta reports fleet average PUE ~1.08-1.09 in its
  sustainability reporting. Company-published figure, quoted as fact.
- **[5] NREL ESIF.** NREL's Energy Systems Integration Facility HPC data
  center reports an annualized PUE ≤ 1.036 with warm-water liquid cooling
  and campus heat reuse. US-government facility, public figures.
- **[6] Legacy stock efficiency.** LBNL, "United States Data Center Energy
  Usage Report" (LBNL-1005775, 2016, public domain): PUE ~1.8-2.0 typical
  of small/legacy server rooms; hyperscale far lower. Basis for the
  legacy-air rung's ~1.9.
- **[7] US data center energy trajectory.** LBNL, "2024 United States Data
  Center Energy Usage Report": ~176 TWh in 2023 (~4.4% of US electricity),
  projected 6.7-12% of US electricity by 2028. The grid-stress context.
- **[8] Withdrawn timing comparison.** LBNL's [Queued Up 2024](https://eta.lbl.gov/publications/queued-2024-edition-characteristics)
  concerns generation and storage interconnection, not data-center load
  connections. Its five-year statistic is not a parameter in this model.
- **[9] Thermal envelopes.** ASHRAE TC 9.9 datacom thermal guidelines:
  recommended inlet 18-27°C, allowable classes A1-A4. Bounds what "free
  cooling" can serve.
- **[10] NVL72-class rack density.** NVIDIA GB200 NVL72: a single liquid-
  cooled rack at ~120 kW nominal, with shipping configurations quoted up
  to ~132 kW. Vendor-published spec, quoted as fact; the model's
  direct-to-chip ceiling uses the 132 kW figure.
- **[11] DGX H100 node power.** NVIDIA DGX H100: 8 GPUs, ~10.2 kW maximum
  system power. Vendor-published spec; used to express freed megawatts in
  GPU-node equivalents.
- **[12] Heat-capture fractions.** OCP cold-plate/coolant guidelines and
  vendor engineering documentation: single-phase direct-to-chip captures
  roughly 70-80% of IT heat to liquid (rest to room air); rear-door heat
  exchangers are marketed as neutralizing most-to-all rack exhaust heat
  into the water loop within their capacity (modeled at 0.85); immersion
  approaches ~95%+. Engineering ranges, not a single measurement.
- **[13] Immersion PUE claims.** Immersion vendors market PUE ~1.02-1.05
  and tank densities to ~200 kW. Vendor claims, labeled as such.
- **[14] New-build cost anchor.** Commonly cited all-in build cost for
  conventional hyperscale capacity is on the order of ~$10-12M per MW of
  IT load (excluding IT hardware); AI-optimized builds are commonly
  quoted higher ($15-20M+/MW ex-IT). The model's ~$10M anchor is
  deliberately conservative — it makes the retrofit comparison harder to
  win, not easier. Industry planning anchor, not a quote; the retrofit
  comparison only needs the order of magnitude.
