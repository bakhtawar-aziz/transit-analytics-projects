"""Data-quality checks + cleaning for the SYNTHETIC fleet dataset.
Every issue found is written to output/error_log.csv with the action taken."""
import pandas as pd, numpy as np, json, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW, CLEAN, OUT = ROOT / "data/raw", ROOT / "data/clean", ROOT / "output"
for p in (CLEAN, OUT): p.mkdir(exist_ok=True, parents=True)

log = []
def L(check, table, ref, field, issue, value, action, severity):
    log.append(dict(check=check, table=table, record_ref=ref, field=field, issue=issue,
                    raw_value=value, action=action, severity=severity))

veh = pd.read_csv(RAW / "vehicles.csv")
dd = pd.read_csv(RAW / "daily_mileage.csv")
ff = pd.read_csv(RAW / "failures.csv")
ww = pd.read_csv(RAW / "work_orders.csv")
valid_veh = set(veh.vehicle_id)
div_master = veh.set_index("vehicle_id").division.to_dict()
quarantine = []

# ---------------- DAILY MILEAGE ----------------
dd["_ref"] = dd.vehicle_id + "|" + dd.record_date
dup = dd.duplicated(["vehicle_id", "record_date"], keep="first")
for r in dd[dup].itertuples(): L("DQ01-duplicate", "daily_mileage", r._7, "vehicle_id+record_date", "Duplicate vehicle-day", r._7, "Dropped (kept first)", "Medium")
dd = dd[~dup].copy()

status_map = {"in service": "IN_SERVICE"}
for r in dd[dd.service_status.isin(status_map)].itertuples(): L("DQ02-inconsistent", "daily_mileage", r._7, "service_status", "Non-standard label", r.service_status, "Standardised", "Low")
dd["service_status"] = dd.service_status.replace(status_map)

dd["division_raw"] = dd.division
dd["division"] = dd.vehicle_id.map(div_master)          # vehicles master is authoritative
for r in dd[dd.division_raw != dd.division].itertuples(): L("DQ02-inconsistent", "daily_mileage", r._7, "division", "Division spelling differs from vehicle master", r.division_raw, "Replaced from vehicles master", "Low")
for r in dd[~dd.vehicle_id.isin(valid_veh)].itertuples(): L("DQ05-traceability", "daily_mileage", r._7, "vehicle_id", "Vehicle not in master", r.vehicle_id, "Quarantined", "High")
dd = dd[dd.vehicle_id.isin(valid_veh)]

ins = dd.service_status == "IN_SERVICE"
dd["km_flag"] = ""
conds = [("DQ03-missing", dd.km.isna() & ins, "Missing km"),
         ("DQ04-range", (dd.km < 0), "Negative km"),
         ("DQ04-range", (dd.km > 800), "Implausible km (>800/day)")]
for chk, mask, msg in conds:
    for r in dd[mask].itertuples(): L(chk, "daily_mileage", r._7, "km", msg, r.km, "Set to NULL then imputed (vehicle median in-service km); flagged", "High")
    dd.loc[mask, "km_flag"] = "imputed"
dd.loc[dd.km_flag == "imputed", "km"] = np.nan
med = dd[ins & dd.km.notna()].groupby("vehicle_id").km.median()
need = dd.km_flag == "imputed"
dd.loc[need, "km"] = dd.loc[need, "vehicle_id"].map(med).round(1)
hmask = dd.hours > 24
for r in dd[hmask].itertuples(): L("DQ04-range", "daily_mileage", r._7, "hours", "Hours > 24 in a day", r.hours, "Re-derived as km / 22 km/h; flagged", "Medium")
dd.loc[hmask, "hours"] = (dd.loc[hmask, "km"] / 22).round(2)
dd["hours_flag"] = np.where(hmask, "rederived", "")
dd = dd.drop(columns=["_ref", "division_raw"])

# ---------------- FAILURES ----------------
ff["_ref"] = ff.failure_id
dup = ff.duplicated("failure_id", keep="first")
for r in ff[dup].itertuples(): L("DQ01-duplicate", "failures", r.failure_id, "failure_id", "Duplicate failure record", r.failure_id, "Dropped (kept first)", "Medium")
ff = ff[~dup].copy()
bad = ~ff.vehicle_id.isin(valid_veh)
for r in ff[bad].itertuples(): L("DQ05-traceability", "failures", r.failure_id, "vehicle_id", "Failure references unknown vehicle", r.vehicle_id, "Quarantined (excluded from KPIs)", "High")
quarantine.append(ff[bad].assign(source="failures", reason="unknown vehicle"))
ff = ff[~bad].copy()
for r in ff[ff.system.isna()].itertuples(): L("DQ03-missing", "failures", r.failure_id, "system", "Missing system", "", "Set to 'Unknown'", "Medium")
canon = {"brake": "Brakes", "brakes": "Brakes", "door": "Doors", "doors": "Doors", "hvac": "HVAC"}
raw_sys = ff.system.copy()
ff["system"] = ff.system.fillna("Unknown").str.strip().map(lambda s: canon.get(s.lower(), s))
for r in ff[(raw_sys != ff.system) & raw_sys.notna()].itertuples(): L("DQ02-inconsistent", "failures", r.failure_id, "system", "Non-standard system label", raw_sys[r.Index], f"Standardised to {r.system}", "Low")
vmap = veh.set_index("vehicle_id")
inserv = ff.vehicle_id.map(vmap.in_service_date)
for r in ff[ff.failure_date < inserv].itertuples(): L("DQ04-range", "failures", r.failure_id, "failure_date", "Failure before in-service date", r.failure_date, "Flagged only", "Low")
ff = ff.drop(columns="_ref")

# ---------------- WORK ORDERS ----------------
dup = ww.duplicated("wo_id", keep="first")
for r in ww[dup].itertuples(): L("DQ01-duplicate", "work_orders", r.wo_id, "wo_id", "Duplicate WO", r.wo_id, "Dropped", "Medium")
ww = ww[~dup].copy()
ww["orphan_flag"] = ~ww.failure_id.isin(set(ff.failure_id))
for r in ww[ww.orphan_flag].itertuples(): L("DQ05-traceability", "work_orders", r.wo_id, "failure_id", "WO references failure that does not exist", r.failure_id, "Kept; flagged orphan; excluded from failure-linked metrics", "High")
ww["orphan_flag"] = ww.orphan_flag.astype(int)
reversed_ = pd.to_datetime(ww.closed_date) < pd.to_datetime(ww.opened_date)
for r in ww[reversed_].itertuples(): L("DQ04-range", "work_orders", r.wo_id, "closed_date", "Closed before opened", f"{r.opened_date}>{r.closed_date}", "Dates swapped; flagged", "Medium")
ww.loc[reversed_, ["opened_date", "closed_date"]] = ww.loc[reversed_, ["closed_date", "opened_date"]].values
ww["date_flag"] = np.where(reversed_, "swapped", "")
for r in ww[ww.labour_hours.isna()].itertuples(): L("DQ03-missing", "work_orders", r.wo_id, "labour_hours", "Missing labour hours", "", "Left NULL (excluded from labour averages)", "Low")
no_wo = set(ff.failure_id) - set(ww.failure_id)
for f in sorted(no_wo): L("DQ05-traceability", "failures", f, "failure_id", "Failure has no work order", f, "Flagged; reported in traceability view", "Medium")

veh.to_csv(CLEAN / "vehicles.csv", index=False); dd.to_csv(CLEAN / "daily_mileage.csv", index=False)
ff.to_csv(CLEAN / "failures.csv", index=False); ww.to_csv(CLEAN / "work_orders.csv", index=False)
pd.read_csv(RAW / "reported_division_km.csv").to_csv(CLEAN / "reported_division_km.csv", index=False)
el = pd.DataFrame(log); el.insert(0, "error_id", range(1, len(el) + 1))
el.to_csv(OUT / "error_log.csv", index=False)
if quarantine: pd.concat(quarantine).to_csv(OUT / "quarantine.csv", index=False)
summ = el.groupby(["check", "severity"]).size().reset_index(name="count")
summ.to_csv(OUT / "dq_summary.csv", index=False)
print(f"{len(el)} issues logged -> output/error_log.csv\n{summ.to_string(index=False)}")
