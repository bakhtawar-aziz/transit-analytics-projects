"""Mileage audit: flags totals that do not reconcile. Output: output/mileage_audit.csv"""
import sqlite3, pandas as pd, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]
TOL_PCT = 0.5                      # division-month tolerance
con = sqlite3.connect(ROOT / "output/fleet.db")
rows = []
# A. Division-month: summed daily km vs operations-reported km
a = pd.read_sql("""SELECT r.division, r.month, r.reported_km, ROUND(SUM(d.km),0) AS daily_sum_km,
        SUM(d.km_flag='imputed') AS imputed_rows
        FROM reported_division_km r JOIN daily_mileage d ON d.division=r.division AND substr(d.record_date,1,7)=r.month
        GROUP BY r.division, r.month""", con)
a["diff_km"] = a.daily_sum_km - a.reported_km; a["diff_pct"] = (100 * a.diff_km / a.reported_km).round(2)
for r in a[a.diff_pct.abs() > TOL_PCT].itertuples():
    rows.append(dict(audit="A-division-month-reconciliation", ref=f"{r.division} {r.month}",
                     detail=f"daily sum {r.daily_sum_km:,.0f} vs reported {r.reported_km:,.0f} ({r.diff_pct:+.2f}%), {r.imputed_rows} imputed rows", severity="High"))
# B. Implied speed out of range (km / hours)
b = pd.read_sql("""SELECT vehicle_id, record_date, km, hours, km/hours AS kmh FROM daily_mileage
        WHERE service_status='IN_SERVICE' AND hours>0 AND (km/hours<8 OR km/hours>70)""", con)
for r in b.itertuples(): rows.append(dict(audit="B-implied-speed", ref=f"{r.vehicle_id} {r.record_date}", detail=f"{r.km} km / {r.hours} h = {r.kmh:.0f} km/h", severity="Medium"))
# C. Km recorded on a day the vehicle was not in service
c = pd.read_sql("SELECT vehicle_id, record_date, km, service_status FROM daily_mileage WHERE service_status<>'IN_SERVICE' AND km>0", con)
for r in c.itertuples(): rows.append(dict(audit="C-km-while-not-in-service", ref=f"{r.vehicle_id} {r.record_date}", detail=f"{r.km} km on {r.service_status}", severity="High"))
# D. Calendar completeness: every vehicle should have 365 rows
d = pd.read_sql("SELECT vehicle_id, COUNT(*) n FROM daily_mileage GROUP BY vehicle_id HAVING n<>365", con)
for r in d.itertuples(): rows.append(dict(audit="D-missing-vehicle-days", ref=r.vehicle_id, detail=f"{r.n} rows, expected 365", severity="High"))
# E. Failure logged on a day with no in-service km
e = pd.read_sql("""SELECT f.failure_id, f.vehicle_id, f.failure_date FROM failures f
        LEFT JOIN daily_mileage d ON d.vehicle_id=f.vehicle_id AND d.record_date=f.failure_date
        WHERE d.record_date IS NULL OR d.service_status<>'IN_SERVICE'""", con)
for r in e.itertuples(): rows.append(dict(audit="E-failure-without-service-day", ref=r.failure_id, detail=f"{r.vehicle_id} on {r.failure_date}", severity="Medium"))
out = pd.DataFrame(rows); out.to_csv(ROOT / "output/mileage_audit.csv", index=False)
a.to_csv(ROOT / "output/division_month_reconciliation.csv", index=False)
print(f"{len(a)} division-months checked, {int((a.diff_pct.abs()>TOL_PCT).sum())} outside +/-{TOL_PCT}%")
print(out.groupby("audit").size().to_string() if len(out) else "no flags")
