-- Fleet Reliability schema (SQLite). SYNTHETIC data only.
DROP VIEW IF EXISTS v_monthly_reliability; DROP VIEW IF EXISTS v_availability; DROP VIEW IF EXISTS v_traceability;
DROP TABLE IF EXISTS work_orders; DROP TABLE IF EXISTS failures; DROP TABLE IF EXISTS daily_mileage;
DROP TABLE IF EXISTS reported_division_km; DROP TABLE IF EXISTS vehicles;
CREATE TABLE vehicles (
  vehicle_id TEXT PRIMARY KEY, vehicle_type TEXT NOT NULL, division TEXT NOT NULL,
  model_year INTEGER NOT NULL, in_service_date TEXT NOT NULL);
CREATE TABLE daily_mileage (
  record_date TEXT NOT NULL, vehicle_id TEXT NOT NULL REFERENCES vehicles(vehicle_id),
  division TEXT NOT NULL, km REAL NOT NULL CHECK (km >= 0), hours REAL NOT NULL CHECK (hours BETWEEN 0 AND 24),
  service_status TEXT NOT NULL CHECK (service_status IN ('IN_SERVICE','SPARE','OUT_OF_SERVICE')),
  km_flag TEXT, hours_flag TEXT, PRIMARY KEY (vehicle_id, record_date));
CREATE TABLE failures (
  failure_id TEXT PRIMARY KEY, vehicle_id TEXT NOT NULL REFERENCES vehicles(vehicle_id),
  failure_date TEXT NOT NULL, system TEXT NOT NULL,
  severity TEXT NOT NULL CHECK (severity IN ('Minor','Major','Service-Interrupting')));
CREATE TABLE work_orders (
  wo_id TEXT PRIMARY KEY, failure_id TEXT, vehicle_id TEXT NOT NULL, opened_date TEXT NOT NULL, closed_date TEXT,
  labour_hours REAL, parts_cost REAL, status TEXT, orphan_flag INTEGER DEFAULT 0, date_flag TEXT);
CREATE TABLE reported_division_km (division TEXT, month TEXT, reported_km REAL, PRIMARY KEY (division, month));
CREATE INDEX ix_fail_date ON failures(failure_date); CREATE INDEX ix_daily_div ON daily_mileage(division, record_date);

CREATE VIEW v_monthly_reliability AS
SELECT v.vehicle_type, m.month, m.km, COALESCE(f.failures,0) AS failures,
       COALESCE(f.road_calls,0) AS road_calls,
       ROUND(COALESCE(f.failures,0)*100000.0/m.km, 2) AS failures_per_100k_km,
       CASE WHEN COALESCE(f.failures,0)=0 THEN NULL ELSE ROUND(m.km*1.0/f.failures,0) END AS mdbf_km
FROM (SELECT vehicle_type FROM vehicles GROUP BY vehicle_type) v
JOIN (SELECT ve.vehicle_type, substr(d.record_date,1,7) AS month, SUM(d.km) AS km
      FROM daily_mileage d JOIN vehicles ve USING(vehicle_id) GROUP BY 1,2) m ON m.vehicle_type=v.vehicle_type
LEFT JOIN (SELECT ve.vehicle_type, substr(f.failure_date,1,7) AS month, COUNT(*) AS failures,
           SUM(f.severity='Service-Interrupting') AS road_calls
           FROM failures f JOIN vehicles ve USING(vehicle_id) GROUP BY 1,2) f
       ON f.vehicle_type=m.vehicle_type AND f.month=m.month;

CREATE VIEW v_availability AS
SELECT division, substr(record_date,1,7) AS month, COUNT(*) AS vehicle_days,
       SUM(service_status<>'OUT_OF_SERVICE') AS available_days,
       ROUND(100.0*SUM(service_status<>'OUT_OF_SERVICE')/COUNT(*),2) AS availability_pct
FROM daily_mileage GROUP BY division, month;

CREATE VIEW v_traceability AS
SELECT f.failure_id, f.vehicle_id, f.failure_date, w.wo_id,
       CASE WHEN w.wo_id IS NULL THEN 'FAILURE_WITHOUT_WO' ELSE 'OK' END AS status
FROM failures f LEFT JOIN work_orders w ON w.failure_id=f.failure_id
UNION ALL
SELECT NULL, w.vehicle_id, w.opened_date, w.wo_id, 'ORPHAN_WO' FROM work_orders w WHERE w.orphan_flag=1;
