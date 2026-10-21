"""Copy Project 1's SYNTHETIC fleet.db to data/api.db and add the error_log / mileage_audit tables."""
import sqlite3, shutil, pathlib, pandas as pd, sys
ROOT = pathlib.Path(__file__).resolve().parents[1]; P1 = ROOT.parent / "p1_fleet_reliability" / "output"
if not (P1 / "fleet.db").exists(): sys.exit("Run Project 1 first: python ../p1_fleet_reliability/run_all.py")
(ROOT / "data").mkdir(exist_ok=True); dst = ROOT / "data" / "api.db"; shutil.copy(P1 / "fleet.db", dst)
con = sqlite3.connect(dst)
pd.read_csv(P1 / "error_log.csv").to_sql("error_log", con, if_exists="replace", index=False)
pd.read_csv(P1 / "mileage_audit.csv").to_sql("mileage_audit", con, if_exists="replace", index=False)
con.execute("CREATE INDEX IF NOT EXISTS ix_fail_vehicle ON failures(vehicle_id)"); con.commit(); con.close(); print("Prepared", dst)
