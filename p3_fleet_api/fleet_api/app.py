"""Fleet Reliability REST API (Flask + SQLite). SYNTHETIC data. All SQL is parameterised; dynamic parts are whitelisted."""
import os, re, sqlite3, datetime as dt
from flask import Flask, g, jsonify, request

SYSTEMS = {"Brakes", "Doors", "HVAC", "Propulsion", "Suspension", "Electrical", "Body", "Unknown"}
SEVERITIES = {"Minor", "Major", "Service-Interrupting"}
MONTH = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")

class ApiError(Exception):
    def __init__(self, status, code, message, details=None):
        self.status, self.code, self.message, self.details = status, code, message, details

def create_app(db_path=None, api_key=None):
    app = Flask(__name__)
    app.config["DB_PATH"] = db_path or os.environ.get("DB_PATH", os.path.join(os.path.dirname(__file__), "..", "data", "api.db"))
    app.config["API_KEY"] = api_key or os.environ.get("API_KEY", "dev-key")

    def db():
        if "db" not in g:
            g.db = sqlite3.connect(app.config["DB_PATH"]); g.db.row_factory = sqlite3.Row; g.db.execute("PRAGMA foreign_keys=ON")
        return g.db
    @app.teardown_appcontext
    def close(_):
        d = g.pop("db", None)
        if d is not None: d.close()

    def rows(sql, args=()): return [dict(r) for r in db().execute(sql, args).fetchall()]
    def one(sql, args=()):
        r = db().execute(sql, args).fetchone(); return dict(r) if r else None

    @app.before_request
    def auth():
        if request.path == "/health" or request.path.startswith("/docs"): return
        if request.headers.get("X-API-Key") != app.config["API_KEY"]:
            raise ApiError(401, "unauthorized", "Missing or invalid X-API-Key header.")

    @app.errorhandler(ApiError)
    def api_err(e): return jsonify(error=dict(code=e.code, message=e.message, details=e.details)), e.status
    @app.errorhandler(404)
    def nf(_): return jsonify(error=dict(code="not_found", message="Resource not found.")), 404
    @app.errorhandler(405)
    def na(_): return jsonify(error=dict(code="method_not_allowed", message="Method not allowed.")), 405
    @app.errorhandler(Exception)
    def boom(e):
        app.logger.exception(e); return jsonify(error=dict(code="server_error", message="Unexpected server error.")), 500

    def paging():
        try: limit, offset = int(request.args.get("limit", 50)), int(request.args.get("offset", 0))
        except ValueError: raise ApiError(400, "bad_request", "limit and offset must be integers.")
        if not 1 <= limit <= 500 or offset < 0: raise ApiError(400, "bad_request", "limit must be 1-500 and offset >= 0.")
        return limit, offset
    def page(sql_from, where, args, select, order):
        limit, offset = paging(); w = (" WHERE " + " AND ".join(where)) if where else ""
        total = one(f"SELECT COUNT(*) n FROM {sql_from}{w}", args)["n"]
        data = rows(f"SELECT {select} FROM {sql_from}{w} ORDER BY {order} LIMIT ? OFFSET ?", (*args, limit, offset))
        return jsonify(data=data, meta=dict(limit=limit, offset=offset, total=total))
    def date_arg(name):
        v = request.args.get(name)
        if v is None: return None
        try: dt.date.fromisoformat(v)
        except ValueError: raise ApiError(400, "bad_request", f"{name} must be YYYY-MM-DD.")
        return v
    def month_arg(name):
        v = request.args.get(name)
        if v is not None and not MONTH.match(v): raise ApiError(400, "bad_request", f"{name} must be YYYY-MM.")
        return v
    def enum_arg(name, allowed):
        v = request.args.get(name)
        if v is not None and v not in allowed: raise ApiError(400, "bad_request", f"{name} must be one of {sorted(allowed)}.")
        return v

    @app.get("/health")
    def health():
        db().execute("SELECT 1"); return jsonify(status="ok", data="synthetic")

    @app.get("/api/v1/vehicles")
    def vehicles():
        where, args = [], []
        for p, col in (("type", "vehicle_type"), ("division", "division")):
            if request.args.get(p): where.append(f"{col} = ?"); args.append(request.args[p])
        return page("vehicles", where, args, "*", "vehicle_id")

    @app.get("/api/v1/vehicles/<vid>")
    def vehicle(vid):
        v = one("SELECT * FROM vehicles WHERE vehicle_id=?", (vid,))
        if not v: raise ApiError(404, "not_found", f"Vehicle {vid} not found.")
        v["summary"] = one("""SELECT (SELECT COUNT(*) FROM failures WHERE vehicle_id=:v) AS failures,
            (SELECT ROUND(SUM(km),0) FROM daily_mileage WHERE vehicle_id=:v) AS km""", {"v": vid})
        return jsonify(data=v)

    @app.get("/api/v1/vehicles/<vid>/failures")
    def vehicle_failures(vid):
        if not one("SELECT 1 x FROM vehicles WHERE vehicle_id=?", (vid,)): raise ApiError(404, "not_found", f"Vehicle {vid} not found.")
        return page("failures", ["vehicle_id = ?"], [vid], "*", "failure_date DESC, failure_id")

    @app.get("/api/v1/failures")
    def failures():
        where, args = [], []
        frm, to = date_arg("from"), date_arg("to")
        if frm: where.append("f.failure_date >= ?"); args.append(frm)
        if to: where.append("f.failure_date <= ?"); args.append(to)
        s, sev = enum_arg("system", SYSTEMS), enum_arg("severity", SEVERITIES)
        if s: where.append("f.system = ?"); args.append(s)
        if sev: where.append("f.severity = ?"); args.append(sev)
        for p, col in (("vehicle_type", "v.vehicle_type"), ("division", "v.division"), ("vehicle_id", "f.vehicle_id")):
            if request.args.get(p): where.append(f"{col} = ?"); args.append(request.args[p])
        return page("failures f JOIN vehicles v USING(vehicle_id)", where, args,
                    "f.failure_id, f.vehicle_id, v.vehicle_type, v.division, f.failure_date, f.system, f.severity", "f.failure_date DESC, f.failure_id")

    @app.get("/api/v1/failures/<fid>")
    def failure(fid):
        f = one("SELECT * FROM failures WHERE failure_id=?", (fid,))
        if not f: raise ApiError(404, "not_found", f"Failure {fid} not found.")
        f["work_orders"] = rows("SELECT * FROM work_orders WHERE failure_id=?", (fid,)); return jsonify(data=f)

    @app.post("/api/v1/failures")
    def create_failure():
        b = request.get_json(silent=True)
        if not isinstance(b, dict): raise ApiError(400, "bad_request", "Body must be a JSON object.")
        errs = {}
        veh = one("SELECT * FROM vehicles WHERE vehicle_id=?", (b.get("vehicle_id"),)) if isinstance(b.get("vehicle_id"), str) else None
        if not veh: errs["vehicle_id"] = "Unknown vehicle_id."
        try:
            d = dt.date.fromisoformat(str(b.get("failure_date")))
            if d > dt.date.today(): errs["failure_date"] = "Cannot be in the future."
            elif veh and str(d) < veh["in_service_date"]: errs["failure_date"] = "Before the vehicle's in-service date."
        except ValueError: errs["failure_date"] = "Must be YYYY-MM-DD."
        if b.get("system") not in SYSTEMS: errs["system"] = f"Must be one of {sorted(SYSTEMS)}."
        if b.get("severity") not in SEVERITIES: errs["severity"] = f"Must be one of {sorted(SEVERITIES)}."
        if errs: raise ApiError(422, "validation_failed", "Request body failed validation.", errs)
        if one("SELECT 1 x FROM failures WHERE vehicle_id=? AND failure_date=? AND system=?", (b["vehicle_id"], b["failure_date"], b["system"])):
            raise ApiError(409, "duplicate", "A failure for this vehicle, date and system already exists.")
        n = one("SELECT COALESCE(MAX(CAST(substr(failure_id,5) AS INTEGER)),0)+1 n FROM failures WHERE failure_id LIKE 'FAPI%'")["n"]
        fid = f"FAPI{n:06d}"
        db().execute("INSERT INTO failures (failure_id, vehicle_id, failure_date, system, severity) VALUES (?,?,?,?,?)",
                     (fid, b["vehicle_id"], b["failure_date"], b["system"], b["severity"])); db().commit()
        r = jsonify(data=one("SELECT * FROM failures WHERE failure_id=?", (fid,))); r.status_code = 201
        r.headers["Location"] = f"/api/v1/failures/{fid}"; return r

    @app.get("/api/v1/work-orders")
    def work_orders():
        where, args = [], []
        if request.args.get("vehicle_id"): where.append("vehicle_id = ?"); args.append(request.args["vehicle_id"])
        if request.args.get("status"): where.append("status = ?"); args.append(request.args["status"])
        if request.args.get("orphan") in ("0", "1"): where.append("orphan_flag = ?"); args.append(int(request.args["orphan"]))
        return page("work_orders", where, args, "*", "opened_date DESC, wo_id")

    @app.get("/api/v1/kpis/reliability")
    def kpi_reliability():
        gb = request.args.get("group_by", "vehicle_type")
        if gb not in ("vehicle_type", "division", "month"): raise ApiError(400, "bad_request", "group_by must be vehicle_type, division or month.")
        frm, to, mt = month_arg("from_month"), month_arg("to_month"), request.args.get("vehicle_type")
        def part(datecol):
            d = f"substr({datecol},1,7)" if gb == "month" else f"v.{gb}"
            w, a = [], []
            if frm: w.append(f"substr({datecol},1,7) >= ?"); a.append(frm)
            if to: w.append(f"substr({datecol},1,7) <= ?"); a.append(to)
            if mt: w.append("v.vehicle_type = ?"); a.append(mt)
            return d, ((" WHERE " + " AND ".join(w)) if w else ""), a
        d1, w1, a1 = part("m.record_date"); d2, w2, a2 = part("f.failure_date")
        sql = f"""SELECT k.grp AS {gb}, ROUND(k.km,0) AS km, COALESCE(x.failures,0) AS failures, COALESCE(x.road_calls,0) AS road_calls,
              ROUND(COALESCE(x.failures,0)*100000.0/k.km,2) AS failures_per_100k_km,
              CASE WHEN COALESCE(x.failures,0)=0 THEN NULL ELSE ROUND(k.km/x.failures,0) END AS mdbf_km
            FROM (SELECT {d1} AS grp, SUM(m.km) AS km FROM daily_mileage m JOIN vehicles v USING(vehicle_id){w1} GROUP BY 1) k
            LEFT JOIN (SELECT {d2} AS grp, COUNT(*) AS failures, SUM(f.severity='Service-Interrupting') AS road_calls
                       FROM failures f JOIN vehicles v USING(vehicle_id){w2} GROUP BY 1) x ON x.grp=k.grp ORDER BY k.grp"""
        return jsonify(data=rows(sql, (*a1, *a2)), meta=dict(group_by=gb, definition="failures_per_100k_km = failures/km*100000; mdbf_km = km/failures"))

    @app.get("/api/v1/kpis/availability")
    def kpi_availability():
        gb = request.args.get("group_by", "division")
        if gb not in ("division", "month"): raise ApiError(400, "bad_request", "group_by must be division or month.")
        col = "division" if gb == "division" else "substr(record_date,1,7)"
        return jsonify(data=rows(f"""SELECT {col} AS {gb}, COUNT(*) AS vehicle_days, SUM(service_status<>'OUT_OF_SERVICE') AS available_days,
            ROUND(100.0*SUM(service_status<>'OUT_OF_SERVICE')/COUNT(*),2) AS availability_pct FROM daily_mileage GROUP BY 1 ORDER BY 1"""))

    @app.get("/api/v1/audit/mileage")
    def audit():
        where, args = [], []
        if request.args.get("audit"): where.append("audit = ?"); args.append(request.args["audit"])
        if request.args.get("severity"): where.append("severity = ?"); args.append(request.args["severity"])
        return page("mileage_audit", where, args, "*", "audit, ref")

    @app.get("/api/v1/data-quality/errors")
    def dq_errors():
        where, args = [], []
        for p in ("check", "severity", "table"):
            if request.args.get(p): where.append(f'"{p}" = ?'); args.append(request.args[p])
        return page("error_log", where, args, "*", "error_id")

    @app.get("/docs/openapi.yaml")
    def spec():
        with open(os.path.join(os.path.dirname(__file__), "..", "docs", "openapi.yaml")) as fh: return fh.read(), 200, {"Content-Type": "application/yaml"}
    return app

if __name__ == "__main__":
    create_app().run(port=int(os.environ.get("PORT", 5000)))
