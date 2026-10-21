# Fleet Reliability Findings - 2025 (SYNTHETIC DATA)
*Synthetic dataset generated for portfolio purposes; figures are illustrative, not agency results.*

**Scope.** 160 vehicles in 4 types across 5 divisions; 10.0 M km; 3,342 failures.

**Headline KPIs.** Fleet failure rate **33.3 per 100,000 km** (MDBF 3,005 km). Availability **93.6%** of vehicle-days.

**Findings.**
1. **Bus-Artic is the least reliable type** at 70.7 failures/100k km (MDBF 1,415 km); **Subway-Car is the best** at 13.2 (MDBF 7,603 km).
2. **Seasonality.** Failure rate peaks in 2025-01 (42.6/100k km) and bottoms in 2025-08 (25.5); winter months run well above summer.
3. **Age effect is modest in aggregate.** Vehicles aged 10+ years fail at 35.9/100k km vs 31.9 for 0-4 years (1.12x), but this is confounded by vehicle-type mix; a within-type comparison is the next step.
4. **Top failure system:** Doors (21.9% of failures).
5. **Availability.** Lowest division: North Garage (90.5%); highest: Subway Div (96.9%).

**Mileage audit.** 5 division-months fail reconciliation (>0.5% between summed daily km and the operations report): East Garage 2025-04; East Garage 2025-08; North Garage 2025-05; South Garage 2025-09; Subway Div 2025-03. Recommend investigating before these totals feed ridership/service-km reporting.

**Data quality.** 245 issues logged and resolved or flagged (see `output/error_log.csv`): duplicates, missing/invalid km (56 rows imputed and flagged), inconsistent labels, and 33 traceability breaks (failures without work orders, orphan work orders).

**Caveats.** Imputed km (vehicle median) and standardised labels are flagged in the clean tables; synthetic failure rates were seeded, so the findings demonstrate method rather than real conclusions.
