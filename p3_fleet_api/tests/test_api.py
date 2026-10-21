import unittest, shutil, tempfile, pathlib, sys, csv
ROOT = pathlib.Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from fleet_api import create_app
H = {"X-API-Key": "test-key"}
class Api(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(); db = pathlib.Path(self.tmp) / "t.db"; shutil.copy(ROOT / "data/api.db", db)
        self.c = create_app(str(db), "test-key").test_client()
    def tearDown(self): shutil.rmtree(self.tmp, ignore_errors=True)
    def get(self, url): return self.c.get(url, headers=H)
    def test_health_open(self): self.assertEqual(self.c.get("/health").status_code, 200)
    def test_auth_required(self):
        r = self.c.get("/api/v1/vehicles"); self.assertEqual(r.status_code, 401); self.assertEqual(r.json["error"]["code"], "unauthorized")
        self.assertEqual(self.c.get("/api/v1/vehicles", headers={"X-API-Key": "bad"}).status_code, 401)
    def test_vehicle_list_paging_filter(self):
        r = self.get("/api/v1/vehicles?type=LRV&limit=5"); self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.json["data"]), 5); self.assertEqual(r.json["meta"]["total"], 30)
    def test_bad_paging(self): self.assertEqual(self.get("/api/v1/vehicles?limit=9999").status_code, 400); self.assertEqual(self.get("/api/v1/vehicles?limit=x").status_code, 400)
    def test_vehicle_detail_and_404(self):
        vid = self.get("/api/v1/vehicles?limit=1").json["data"][0]["vehicle_id"]
        self.assertIn("summary", self.get(f"/api/v1/vehicles/{vid}").json["data"]); self.assertEqual(self.get("/api/v1/vehicles/NOPE").status_code, 404)
    def test_failures_filters(self):
        r = self.get("/api/v1/failures?system=Doors&from=2025-03-01&to=2025-03-31&limit=500"); self.assertEqual(r.status_code, 200)
        self.assertTrue(all(f["system"] == "Doors" and "2025-03-01" <= f["failure_date"] <= "2025-03-31" for f in r.json["data"]))
        self.assertEqual(self.get("/api/v1/failures?system=Wheels").status_code, 400); self.assertEqual(self.get("/api/v1/failures?from=03/01/2025").status_code, 400)
    def test_sql_injection_is_inert(self):
        r = self.get("/api/v1/vehicles?type=LRV'%20OR%20'1'='1"); self.assertEqual(r.json["meta"]["total"], 0)
        self.assertEqual(self.get("/api/v1/kpis/reliability?group_by=vehicle_type;DROP%20TABLE%20failures").status_code, 400)
    def test_kpi_matches_project1(self):
        p1 = {r["vehicle_type"]: float(r["failures_per_100k_km"]) for r in csv.DictReader(open(ROOT.parent / "p1_fleet_reliability/output/KPI_ByType.csv", newline=""))}
        api = {r["vehicle_type"]: r["failures_per_100k_km"] for r in self.get("/api/v1/kpis/reliability?group_by=vehicle_type").json["data"]}
        self.assertEqual(p1, api)
    def test_kpi_groupings(self):
        self.assertEqual(len(self.get("/api/v1/kpis/reliability?group_by=month").json["data"]), 12)
        self.assertEqual(len(self.get("/api/v1/kpis/reliability?group_by=division").json["data"]), 5)
        r = self.get("/api/v1/kpis/reliability?group_by=month&from_month=2025-06&to_month=2025-08&vehicle_type=LRV"); self.assertEqual(len(r.json["data"]), 3)
        self.assertEqual(self.get("/api/v1/kpis/reliability?from_month=2025-13").status_code, 400)
    def test_availability(self): self.assertEqual(len(self.get("/api/v1/kpis/availability").json["data"]), 5)
    def test_audit_and_dq(self):
        self.assertEqual(self.get("/api/v1/audit/mileage").json["meta"]["total"], 5)
        self.assertEqual(self.get("/api/v1/data-quality/errors?check=DQ01-duplicate&limit=500").json["meta"]["total"], 38)
    def test_create_failure_ok_then_duplicate(self):
        body = {"vehicle_id": "L1100", "failure_date": "2025-12-30", "system": "Doors", "severity": "Minor"}
        vid = self.get("/api/v1/vehicles?type=LRV&limit=1").json["data"][0]["vehicle_id"]; body["vehicle_id"] = vid
        r = self.c.post("/api/v1/failures", json=body, headers=H); self.assertEqual(r.status_code, 201, r.json)
        self.assertTrue(r.headers["Location"].endswith(r.json["data"]["failure_id"]))
        self.assertEqual(self.c.post("/api/v1/failures", json=body, headers=H).status_code, 409)
        self.assertEqual(self.get(r.headers["Location"]).status_code, 200)
    def test_create_failure_validation(self):
        r = self.c.post("/api/v1/failures", json={"vehicle_id": "ZZZ", "failure_date": "2999-01-01", "system": "x", "severity": "y"}, headers=H)
        self.assertEqual(r.status_code, 422); self.assertEqual(set(r.json["error"]["details"]), {"vehicle_id", "failure_date", "system", "severity"})
        self.assertEqual(self.c.post("/api/v1/failures", data="not json", headers=H).status_code, 400)
        self.assertEqual(self.c.post("/api/v1/failures", json={}, headers={}).status_code, 401)
    def test_work_orders_orphans(self):
        # 5 seeded orphans + 3 WOs whose failure was quarantined (unknown vehicle) = what the error log reports
        orphans = self.get("/api/v1/work-orders?orphan=1").json["meta"]["total"]
        logged = self.get("/api/v1/data-quality/errors?table=work_orders&check=DQ05-traceability&limit=500").json["meta"]["total"]
        self.assertEqual(orphans, logged); self.assertGreater(orphans, 0)
    def test_unknown_route_json(self): r = self.get("/api/v1/nope"); self.assertEqual((r.status_code, r.json["error"]["code"]), (404, "not_found"))
if __name__ == "__main__": unittest.main()
