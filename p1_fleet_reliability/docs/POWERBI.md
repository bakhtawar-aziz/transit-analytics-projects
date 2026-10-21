# Power BI setup (SYNTHETIC data)
1. Get Data > Folder > `output/` and load `KPI_Monthly.csv`, `KPI_ByType.csv`, `Availability_Monthly.csv`, `FailuresBySystem.csv`, `MileageAudit.csv`, `ErrorLog.csv` (or use `fleet_reliability_kpis.xlsx`).
2. Suggested DAX measures (on a table with `failures` and `km` columns, e.g. KPI_Monthly):
```
Failures per 100k km = DIVIDE ( SUM ( KPI_Monthly[failures] ) * 100000, SUM ( KPI_Monthly[km] ) )
MDBF km = DIVIDE ( SUM ( KPI_Monthly[km] ), SUM ( KPI_Monthly[failures] ) )
Availability % = DIVIDE ( SUM ( Availability_Monthly[available_days] ), SUM ( Availability_Monthly[vehicle_days] ) )
```
3. Pages: Overview (cards + trend line by vehicle_type), Availability (bar by division), Failures (system bar), Data Quality (ErrorLog by check, MileageAudit table).
The .pbix is not included (built on Linux); `output/dashboard.html` is the ready-made dashboard.
