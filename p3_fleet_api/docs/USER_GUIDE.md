# User Guide - Fleet Reliability API
*Synthetic data. Base URL `http://localhost:5000`; all examples use API key `demo`.*

## 1. Install and run
```
cd p1_fleet_reliability && python run_all.py        # builds fleet.db (once)
cd ../p3_fleet_api && pip install -r requirements.txt
python scripts/prepare_db.py                         # creates data/api.db
API_KEY=demo python -m fleet_api.app                 # Windows PowerShell: $env:API_KEY="demo"; python -m fleet_api.app
```
Check: `curl localhost:5000/health` -> `{"status":"ok"}`. Spec: `/docs/openapi.yaml` (paste into editor.swagger.io).

## 2. Authentication
Send `X-API-Key: <key>` on every request except `/health`. Missing/wrong key -> `401`.

## 3. Conventions
Lists return `{"data":[...],"meta":{"limit","offset","total"}}`. Use `limit` (1-500, default 50) and `offset`. Dates are `YYYY-MM-DD`, months `YYYY-MM`. Errors: `{"error":{"code","message","details"}}`.

## 4. Examples
```
# LRVs in the fleet
curl -H "X-API-Key: demo" "localhost:5000/api/v1/vehicles?type=LRV&limit=5"
# Door failures in March 2025
curl -H "X-API-Key: demo" "localhost:5000/api/v1/failures?system=Doors&from=2025-03-01&to=2025-03-31"
# Reliability KPIs by vehicle type / monthly trend for LRVs
curl -H "X-API-Key: demo" "localhost:5000/api/v1/kpis/reliability?group_by=vehicle_type"
curl -H "X-API-Key: demo" "localhost:5000/api/v1/kpis/reliability?group_by=month&vehicle_type=LRV"
# Availability by division, mileage audit flags, duplicate-record log
curl -H "X-API-Key: demo" "localhost:5000/api/v1/kpis/availability"
curl -H "X-API-Key: demo" "localhost:5000/api/v1/audit/mileage"
curl -H "X-API-Key: demo" "localhost:5000/api/v1/data-quality/errors?check=DQ01-duplicate"
# Record a failure
curl -X POST -H "X-API-Key: demo" -H "Content-Type: application/json" localhost:5000/api/v1/failures \
  -d '{"vehicle_id":"L1091","failure_date":"2025-12-30","system":"Doors","severity":"Minor"}'
```
Use a `vehicle_id` returned by `/api/v1/vehicles`.

## 5. Endpoint summary
| Method | Path | Purpose |
|---|---|---|
| GET | /health | Liveness |
| GET | /api/v1/vehicles, /vehicles/{id}, /vehicles/{id}/failures | Fleet lookups |
| GET | /api/v1/failures, /failures/{id} | Failure search / detail with work orders |
| POST | /api/v1/failures | Create failure (201 + Location) |
| GET | /api/v1/work-orders | Filter by vehicle_id, status, orphan=0/1 |
| GET | /api/v1/kpis/reliability | group_by = vehicle_type, division, month; from_month, to_month, vehicle_type |
| GET | /api/v1/kpis/availability | group_by = division, month |
| GET | /api/v1/audit/mileage | audit, severity |
| GET | /api/v1/data-quality/errors | check, severity, table |

## 6. Status codes
200 OK, 201 Created, 400 bad parameter, 401 bad/missing key, 404 not found, 405 wrong method, 409 duplicate failure, 422 body failed validation (`details` lists each field), 500 unexpected.

## 7. Power BI / Excel / Python
Power BI: Get Data > Web > Advanced, add header `X-API-Key`. Python: `requests.get(url, headers={"X-API-Key":"demo"}).json()["data"]` into `pandas.DataFrame`.

## 8. Troubleshooting
`401` - check the header name and `API_KEY` variable the server was started with. `no such table: error_log` - run `scripts/prepare_db.py`. `database is locked` - another process is writing; retry. Run tests: `python -m unittest discover -s tests`.
