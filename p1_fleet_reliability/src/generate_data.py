"""Generate a SYNTHETIC transit fleet dataset (raw, deliberately dirty).
Nothing here is real agency data. Seeded for reproducibility."""
import numpy as np, pandas as pd, pathlib, random
RAW = pathlib.Path(__file__).resolve().parents[1] / "data" / "raw"
RAW.mkdir(parents=True, exist_ok=True)
rng = np.random.default_rng(42); random.seed(42)
START, END = pd.Timestamp("2025-01-01"), pd.Timestamp("2025-12-31")
DAYS = pd.date_range(START, END)

# type: (count, failures/100k km, mean daily km, avg km/h, divisions)
TYPES = {
    "Bus-40ft":   (60, 38.0, 190, 20, ["North Garage", "South Garage", "East Garage"]),
    "Bus-Artic":  (25, 55.0, 175, 18, ["North Garage", "South Garage"]),
    "LRV":        (30, 18.0, 210, 28, ["Light Rail Div"]),
    "Subway-Car": (45,  9.0, 260, 34, ["Subway Div"]),
}
PREFIX = {"Bus-40ft": "B", "Bus-Artic": "A", "LRV": "L", "Subway-Car": "S"}
SYSTEMS = ["Brakes", "Doors", "HVAC", "Propulsion", "Suspension", "Electrical", "Body"]
SYS_P = [.18, .22, .14, .16, .10, .14, .06]
SEV = ["Minor", "Major", "Service-Interrupting"]

vehicles, n = [], 1000
for vt, (cnt, _r, _k, _s, divs) in TYPES.items():
    for i in range(cnt):
        n += 1
        my = int(rng.integers(2008, 2023))
        vehicles.append(dict(vehicle_id=f"{PREFIX[vt]}{n}", vehicle_type=vt, division=divs[i % len(divs)],
                             model_year=my, in_service_date=f"{my + int(rng.integers(0, 2))}-06-01"))
veh = pd.DataFrame(vehicles)

daily, fails, wos = [], [], []
fid = 0
for v in veh.itertuples():
    _c, rate, mkm, spd, _d = TYPES[v.vehicle_type]
    rate_v = rate * (1 + 0.035 * (2025 - v.model_year))      # older = less reliable
    oos_until = START - pd.Timedelta(days=1)
    for d in DAYS:
        season = 1 + 0.25 * np.cos((d.dayofyear - 20) / 365 * 2 * np.pi)   # winter bump
        if d <= oos_until:
            daily.append((d, v.vehicle_id, v.division, 0.0, 0.0, "OUT_OF_SERVICE")); continue
        if rng.random() < 0.13:
            daily.append((d, v.vehicle_id, v.division, 0.0, 0.0, "SPARE")); continue
        km = max(20, rng.normal(mkm, mkm * .12)); hrs = km / spd * rng.normal(1, .04)
        daily.append((d, v.vehicle_id, v.division, round(km, 1), round(hrs, 2), "IN_SERVICE"))
        if rng.poisson(rate_v * season * km / 1e5) > 0:
            fid += 1
            sev = rng.choice(SEV, p=[.55, .30, .15])
            rep_h = float(rng.lognormal({"Minor": 1.5, "Major": 3.0, "Service-Interrupting": 3.6}[sev], .5))
            down = 0 if sev == "Minor" and rep_h < 8 else int(np.ceil(rep_h / 16))
            oos_until = d + pd.Timedelta(days=down)
            fails.append((f"F{fid:06d}", v.vehicle_id, d.date().isoformat(), rng.choice(SYSTEMS, p=SYS_P), sev))
            closed = d + pd.Timedelta(days=down + int(rng.integers(0, 2)))
            wos.append((f"WO{fid:06d}", f"F{fid:06d}", v.vehicle_id, d.date().isoformat(), closed.date().isoformat(),
                        round(rep_h, 1), round(float(rng.lognormal(5, .9)), 2), "Closed"))
dd = pd.DataFrame(daily, columns=["record_date", "vehicle_id", "division", "km", "hours", "service_status"])
ff = pd.DataFrame(fails, columns=["failure_id", "vehicle_id", "failure_date", "system", "severity"])
ww = pd.DataFrame(wos, columns=["wo_id", "failure_id", "vehicle_id", "opened_date", "closed_date", "labour_hours", "parts_cost", "status"])

# "Operations report" division-month totals from the TRUE data, before dirtying
dd["month"] = pd.to_datetime(dd.record_date).dt.strftime("%Y-%m")
rep = dd.groupby(["division", "month"], as_index=False).km.sum().rename(columns={"km": "reported_km"})
rep["reported_km"] = rep.reported_km.round(0)
for idx in rng.choice(len(rep), 5, replace=False):            # injected reconciliation breaks
    rep.loc[idx, "reported_km"] = round(rep.loc[idx, "reported_km"] * rng.choice([0.93, 1.06, 1.12]))
dd = dd.drop(columns="month")

# ---------- inject data-quality problems ----------
ins = dd.index[dd.service_status == "IN_SERVICE"]
dd.loc[rng.choice(ins, 40, replace=False), "km"] = np.nan
dd.loc[rng.choice(ins, 10, replace=False), "km"] = -rng.uniform(5, 200, 10).round(1)
dd.loc[rng.choice(ins, 6, replace=False), "km"] = rng.uniform(900, 2500, 6).round(1)
dd.loc[rng.choice(ins, 5, replace=False), "hours"] = 30.0
dd.loc[rng.choice(ins, 4, replace=False), "service_status"] = "in service"
messy = {"North Garage": ["north garage", "NORTH GARAGE", "N. Garage"], "Subway Div": ["Subway Division", "subway div "]}
for k, alts in messy.items():
    rows = dd.index[dd.division == k]
    dd.loc[rng.choice(rows, 25, replace=False), "division"] = [random.choice(alts) for _ in range(25)]
dd = pd.concat([dd, dd.sample(30, random_state=1)], ignore_index=True)       # duplicates

miss = rng.choice(len(ff), 12, replace=False)
for i in rng.choice([j for j in range(len(ff)) if j not in set(miss)], 30, replace=False):
    ff.loc[i, "system"] = random.choice(["Brake", "brakes", "HVAC ", "door", "Doors "])
ff.loc[miss, "system"] = None
ff.loc[rng.choice(len(ff), 3, replace=False), "vehicle_id"] = ["B9999", "X0001", "L8888"]
ff = pd.concat([ff, ff.sample(8, random_state=2)], ignore_index=True)

no_wo = set(rng.choice(ff.failure_id.unique(), 20, replace=False))
ww = ww[~ww.failure_id.isin(no_wo)].reset_index(drop=True)
bad = rng.choice(len(ww), 6, replace=False)
ww.loc[bad, ["opened_date", "closed_date"]] = ww.loc[bad, ["closed_date", "opened_date"]].values
ww.loc[rng.choice(len(ww), 5, replace=False), "failure_id"] = [f"F9{i}999" for i in range(5)]
ww.loc[rng.choice(len(ww), 8, replace=False), "labour_hours"] = np.nan

veh.to_csv(RAW / "vehicles.csv", index=False); dd.to_csv(RAW / "daily_mileage.csv", index=False)
ff.to_csv(RAW / "failures.csv", index=False); ww.to_csv(RAW / "work_orders.csv", index=False)
rep.to_csv(RAW / "reported_division_km.csv", index=False)
print(f"SYNTHETIC data written: {len(veh)} vehicles, {len(dd)} daily rows, {len(ff)} failures, {len(ww)} work orders")
