import sqlite3, pandas as pd, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]
db = ROOT / "output" / "fleet.db"; db.parent.mkdir(exist_ok=True)
if db.exists(): db.unlink()
con = sqlite3.connect(db); con.execute("PRAGMA foreign_keys=ON")
con.executescript((ROOT / "sql/schema.sql").read_text())
for t in ["vehicles", "daily_mileage", "failures", "work_orders", "reported_division_km"]:
    pd.read_csv(ROOT / f"data/clean/{t}.csv").to_sql(t, con, if_exists="append", index=False)
con.commit()
print({t: con.execute(f"select count(*) from {t}").fetchone()[0] for t in ["vehicles","daily_mileage","failures","work_orders"]})
