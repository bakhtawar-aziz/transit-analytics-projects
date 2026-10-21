"""Build a single-file HTML dashboard (charts embedded as images) and FINDINGS.md from the KPI CSVs."""
import pandas as pd, pathlib, io, base64, matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
ROOT = pathlib.Path(__file__).resolve().parents[1]; OUT = ROOT / "output"
r = lambda n: pd.read_csv(OUT / f"{n}.csv")
bt, mo, av, am, sy, ag = r("KPI_ByType"), r("KPI_Monthly"), r("KPI_Availability"), r("Availability_Monthly"), r("FailuresBySystem"), r("AgeBands")
audit, el, tr = r("MileageAudit"), r("ErrorLog"), r("Traceability")
def img(fig):
    b = io.BytesIO(); fig.savefig(b, format="png", dpi=110, bbox_inches="tight"); plt.close(fig)
    return "data:image/png;base64," + base64.b64encode(b.getvalue()).decode()
C = ["#1f6feb", "#d1495b", "#2a9d8f", "#e9a23b"]
f1, a = plt.subplots(figsize=(6, 3.2)); a.bar(bt.vehicle_type, bt.failures_per_100k_km, color=C); a.set_title("Failures per 100,000 km"); a.set_ylabel("failures / 100k km")
f2, a = plt.subplots(figsize=(6, 3.2))
for i, (t, g) in enumerate(mo.groupby("vehicle_type")): a.plot(g.month.str[5:], g.failures_per_100k_km, label=t, color=C[i], marker="o", ms=3)
a.set_title("Monthly trend by vehicle type"); a.legend(fontsize=7); a.set_xlabel("month (2025)")
f3, a = plt.subplots(figsize=(6, 3.2)); a.barh(av.division, av.availability_pct, color="#2a9d8f"); a.set_xlim(min(av.availability_pct) - 3, 100); a.set_title("Availability % by division")
f4, a = plt.subplots(figsize=(6, 3.2)); a.barh(sy.system[::-1], sy.failures[::-1], color="#7a5195"); a.set_title("Failures by system")
f5, a = plt.subplots(figsize=(6, 3.2)); a.bar(ag.age_band, ag.failures_per_100k_km, color="#e9a23b"); a.set_title("Failures per 100k km by fleet age")
tot_fail, tot_km = int(bt.failures.sum()), bt.km.sum()
tiles = [("Fleet failures / 100k km", f"{tot_fail*1e5/tot_km:.1f}"), ("Fleet MDBF (km)", f"{tot_km/tot_fail:,.0f}"),
         ("Availability", f"{av.available_days.sum()/av.vehicle_days.sum()*100:.1f}%"),
         ("Data issues logged", f"{len(el)}"), ("Audit flags", f"{len(audit)}")]
tile_html = "".join(f"<div class=t><b>{v}</b><span>{k}</span></div>" for k, v in tiles)
aud = audit.head(10).to_html(index=False, border=0) if len(audit) else "<p>No flags</p>"
dq = el.groupby("check").size().reset_index(name="issues").to_html(index=False, border=0)
html = f"""<!doctype html><meta charset=utf-8><title>Fleet Reliability Dashboard (SYNTHETIC)</title>
<style>body{{font:14px system-ui;margin:24px;max-width:1100px}}.g{{display:grid;grid-template-columns:repeat(auto-fit,minmax(340px,1fr));gap:14px}}
.t{{background:#f2f5f9;border-radius:8px;padding:12px;display:inline-block;margin:0 8px 8px 0;min-width:150px}}.t b{{display:block;font-size:24px}}.t span{{font-size:12px;color:#555}}
img{{width:100%}}table{{border-collapse:collapse;font-size:12px}}td,th{{padding:3px 8px;border-bottom:1px solid #ddd;text-align:left}}.w{{background:#fff3cd;padding:8px;border-radius:6px}}</style>
<h1>Fleet Reliability &amp; Mileage Dashboard</h1><p class=w><b>SYNTHETIC DATA</b> &ndash; generated for portfolio use. Calendar year 2025.</p>{tile_html}
<div class=g>{"".join(f"<img src='{img(f)}'>" for f in (f1,f2,f3,f4,f5))}</div>
<h3>Mileage audit flags (first 10 of {len(audit)})</h3>{aud}<h3>Data-quality issues by check</h3>{dq}"""
(OUT / "dashboard.html").write_text(html)

w = bt.sort_values("failures_per_100k_km"); worst, best = w.iloc[-1], w.iloc[0]
wm = mo.groupby("month").apply(lambda g: g.failures.sum() * 1e5 / g.km.sum()); lo = av.sort_values("availability_pct")
top = sy.iloc[0]; old = ag[ag.age_band == "10+ yrs"].failures_per_100k_km.iloc[0]; new = ag[ag.age_band == "0-4 yrs"].failures_per_100k_km.iloc[0]
imp = int((el.issue.str.contains("Missing km|Negative|Implausible", regex=True)).sum())
ac = audit[audit.audit.str.startswith("A")]
md = f"""# Fleet Reliability Findings - 2025 (SYNTHETIC DATA)
*Synthetic dataset generated for portfolio purposes; figures are illustrative, not agency results.*

**Scope.** {len(pd.read_csv(ROOT/'data/clean/vehicles.csv'))} vehicles in 4 types across 5 divisions; {tot_km/1e6:.1f} M km; {tot_fail:,} failures.

**Headline KPIs.** Fleet failure rate **{tot_fail*1e5/tot_km:.1f} per 100,000 km** (MDBF {tot_km/tot_fail:,.0f} km). Availability **{av.available_days.sum()/av.vehicle_days.sum()*100:.1f}%** of vehicle-days.

**Findings.**
1. **{worst.vehicle_type} is the least reliable type** at {worst.failures_per_100k_km:.1f} failures/100k km (MDBF {worst.mdbf_km:,.0f} km); **{best.vehicle_type} is the best** at {best.failures_per_100k_km:.1f} (MDBF {best.mdbf_km:,.0f} km).
2. **Seasonality.** Failure rate peaks in {wm.idxmax()} ({wm.max():.1f}/100k km) and bottoms in {wm.idxmin()} ({wm.min():.1f}); winter months run well above summer.
3. **Age effect is modest in aggregate.** Vehicles aged 10+ years fail at {old:.1f}/100k km vs {new:.1f} for 0-4 years ({old/new:.2f}x), but this is confounded by vehicle-type mix; a within-type comparison is the next step.
4. **Top failure system:** {top.system} ({top.pct}% of failures).
5. **Availability.** Lowest division: {lo.iloc[0].division} ({lo.iloc[0].availability_pct:.1f}%); highest: {lo.iloc[-1].division} ({lo.iloc[-1].availability_pct:.1f}%).

**Mileage audit.** {len(ac)} division-months fail reconciliation (>0.5% between summed daily km and the operations report): {'; '.join(ac.ref)}. Recommend investigating before these totals feed ridership/service-km reporting.

**Data quality.** {len(el)} issues logged and resolved or flagged (see `output/error_log.csv`): duplicates, missing/invalid km ({imp} rows imputed and flagged), inconsistent labels, and {int((tr[tr.status!='OK'].n).sum())} traceability breaks (failures without work orders, orphan work orders).

**Caveats.** Imputed km (vehicle median) and standardised labels are flagged in the clean tables; synthetic failure rates were seeded, so the findings demonstrate method rather than real conclusions.
"""
(ROOT / "docs/FINDINGS.md").write_text(md); print(md)
