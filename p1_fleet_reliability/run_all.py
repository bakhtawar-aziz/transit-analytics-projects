import subprocess, sys, pathlib
here = pathlib.Path(__file__).parent
for s in ["generate_data", "data_quality", "build_db", "mileage_audit", "kpis", "dashboard"]:
    print(f"\n=== {s} ==="); subprocess.run([sys.executable, str(here / "src" / f"{s}.py")], check=True, stdout=None if s in ("data_quality","mileage_audit") else subprocess.DEVNULL)
print("\nDone. Open output/dashboard.html, output/fleet_reliability_kpis.xlsx, docs/FINDINGS.md")
