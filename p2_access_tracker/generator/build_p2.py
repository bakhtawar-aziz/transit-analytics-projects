"""Single source of truth for the Access tracker schema. Emits: Access DDL, SQLite DDL (for testing),
VBA schema-setup module, data dictionary, ERD (Mermaid) and SYNTHETIC seed CSVs."""
import pathlib, random, csv, datetime as dt
ROOT = pathlib.Path(__file__).resolve().parents[1]; random.seed(7)
# column: (name, access_type, sqlite_type, constraint, description)
PK = "PK"
T = {
 "tblCarType": ("Rail car classes and their preventive-maintenance intervals", [
   ("CarTypeID","AUTOINCREMENT","INTEGER",PK,"Surrogate key"),
   ("TypeName","TEXT(50)","TEXT","NOT NULL UNIQUE","Car class name, e.g. LRV-A"),
   ("Manufacturer","TEXT(50)","TEXT","","Builder of the car class"),
   ("PMIntervalKm","LONG","INTEGER","NOT NULL","Preventive-maintenance interval in km"),
   ("PMIntervalDays","LONG","INTEGER","NOT NULL","Preventive-maintenance interval in calendar days")]),
 "tblCarStatus": ("Lookup: operational status of a car", [
   ("CarStatusID","AUTOINCREMENT","INTEGER",PK,"Surrogate key"),
   ("StatusName","TEXT(30)","TEXT","NOT NULL UNIQUE","Active, In Shop, Stored, Retired")]),
 "tblLocation": ("Yards, shops and storage tracks", [
   ("LocationID","AUTOINCREMENT","INTEGER",PK,"Surrogate key"),
   ("LocationName","TEXT(50)","TEXT","NOT NULL UNIQUE","Location name"),
   ("LocationType","TEXT(20)","TEXT","NOT NULL","Yard, Shop or Storage")]),
 "tblCar": ("One row per rail car", [
   ("CarID","AUTOINCREMENT","INTEGER",PK,"Surrogate key"),
   ("CarNumber","TEXT(10)","TEXT","NOT NULL UNIQUE","Operating car number"),
   ("CarTypeID","LONG","INTEGER","NOT NULL FK tblCarType.CarTypeID","Car class"),
   ("CarStatusID","LONG","INTEGER","NOT NULL FK tblCarStatus.CarStatusID","Current status"),
   ("LocationID","LONG","INTEGER","FK tblLocation.LocationID","Where the car is now"),
   ("InServiceDate","DATETIME","TEXT","NOT NULL","Date entered revenue service"),
   ("CurrentOdometerKm","LONG","INTEGER","NOT NULL CHECK >=0","Latest known odometer (km)")]),
 "tblTechnician": ("Maintenance staff", [
   ("TechID","AUTOINCREMENT","INTEGER",PK,"Surrogate key"),
   ("EmployeeNo","TEXT(10)","TEXT","NOT NULL UNIQUE","Employee number (synthetic)"),
   ("FullName","TEXT(60)","TEXT","NOT NULL","Technician name (synthetic)"),
   ("Trade","TEXT(30)","TEXT","","Electrical, Mechanical, Body..."),
   ("IsActive","YESNO","INTEGER","NOT NULL","Currently employed/assignable")]),
 "tblPriority": ("Lookup: work-order priority", [
   ("PriorityID","AUTOINCREMENT","INTEGER",PK,"Surrogate key"),
   ("PriorityName","TEXT(20)","TEXT","NOT NULL UNIQUE","Critical, High, Normal, Low"),
   ("TargetHours","LONG","INTEGER","NOT NULL","Target hours to complete")]),
 "tblWOType": ("Lookup: work-order type", [
   ("WOTypeID","AUTOINCREMENT","INTEGER",PK,"Surrogate key"),
   ("WOTypeName","TEXT(30)","TEXT","NOT NULL UNIQUE","Corrective, Preventive, Inspection, Campaign")]),
 "tblWOStatus": ("Lookup: work-order status", [
   ("WOStatusID","AUTOINCREMENT","INTEGER",PK,"Surrogate key"),
   ("WOStatusName","TEXT(20)","TEXT","NOT NULL UNIQUE","Open, In Progress, On Hold, Closed")]),
 "tblWorkOrder": ("Maintenance work orders against cars", [
   ("WOID","AUTOINCREMENT","INTEGER",PK,"Work-order number"),
   ("CarID","LONG","INTEGER","NOT NULL FK tblCar.CarID","Car being worked on"),
   ("WOTypeID","LONG","INTEGER","NOT NULL FK tblWOType.WOTypeID","Type"),
   ("PriorityID","LONG","INTEGER","NOT NULL FK tblPriority.PriorityID","Priority"),
   ("WOStatusID","LONG","INTEGER","NOT NULL FK tblWOStatus.WOStatusID","Status"),
   ("AssignedTechID","LONG","INTEGER","FK tblTechnician.TechID","Lead technician"),
   ("OpenedDate","DATETIME","TEXT","NOT NULL","Date opened"),
   ("DueDate","DATETIME","TEXT","","Target completion date (>= OpenedDate)"),
   ("ClosedDate","DATETIME","TEXT","","Date closed (>= OpenedDate); required when status is Closed"),
   ("OdometerKm","LONG","INTEGER","CHECK >=0","Car odometer when opened; must not decrease for the same car"),
   ("DefectDescription","TEXT(255)","TEXT","NOT NULL","Defect or task description (min 10 characters, enforced by VBA)"),
   ("ClosureNotes","TEXT(255)","TEXT","","Required when closing")]),
 "tblLabour": ("Labour hours booked to a work order", [
   ("LabourID","AUTOINCREMENT","INTEGER",PK,"Surrogate key"),
   ("WOID","LONG","INTEGER","NOT NULL FK tblWorkOrder.WOID","Work order"),
   ("TechID","LONG","INTEGER","NOT NULL FK tblTechnician.TechID","Technician"),
   ("WorkDate","DATETIME","TEXT","NOT NULL","Date worked"),
   ("Hours","DOUBLE","REAL","NOT NULL CHECK >0 AND <=16","Hours (max 16 per entry)")]),
 "tblPart": ("Parts catalogue", [
   ("PartID","AUTOINCREMENT","INTEGER",PK,"Surrogate key"),
   ("PartNumber","TEXT(20)","TEXT","NOT NULL UNIQUE","Part number (synthetic)"),
   ("PartName","TEXT(60)","TEXT","NOT NULL","Description"),
   ("UnitCost","CURRENCY","REAL","NOT NULL CHECK >=0","Unit cost")]),
 "tblPartUsed": ("Parts consumed on a work order", [
   ("PartUsedID","AUTOINCREMENT","INTEGER",PK,"Surrogate key"),
   ("WOID","LONG","INTEGER","NOT NULL FK tblWorkOrder.WOID","Work order"),
   ("PartID","LONG","INTEGER","NOT NULL FK tblPart.PartID","Part"),
   ("Quantity","LONG","INTEGER","NOT NULL CHECK >0","Quantity used")]),
}
def parts(c):
    fk = checks = None
    cons = c[3]; nn = "NOT NULL" in cons
    chk = None
    if "CHECK" in cons: chk = cons.split("CHECK ")[1]
    fk = cons.split("FK ")[1].split()[0] if "FK " in cons else None
    return nn, "UNIQUE" in cons, chk, fk
acc, sq, fks, uq, chks = [], [], [], [], []
for t, (desc, cols) in T.items():
    a, s = [], []
    for c in cols:
        nn, u, chk, fk = parts(c)
        if c[3] == PK: a.append(f"{c[0]} {c[1]} PRIMARY KEY"); s.append(f"{c[0]} INTEGER PRIMARY KEY AUTOINCREMENT"); continue
        a.append(f"{c[0]} {c[1]}" + (" NOT NULL" if nn else "")); s.append(f"{c[0]} {c[2]}" + (" NOT NULL" if nn else "") + (" UNIQUE" if u else ""))
        if u: uq.append(f"CREATE UNIQUE INDEX ux_{t}_{c[0]} ON {t} ({c[0]})")
        if chk: chks.append((t, c[0], chk))
        if fk: fks.append((t, c[0], fk.split(".")[0], fk.split(".")[1]))
    acc.append(f"CREATE TABLE {t} ({', '.join(a)})"); sq.append(f"CREATE TABLE {t} ({', '.join(s)});")
fk_sql = [f"ALTER TABLE {t} ADD CONSTRAINT fk_{t}_{c} FOREIGN KEY ({c}) REFERENCES {rt}({rc})" for t, c, rt, rc in fks]
def chk_sql(t, c, e):
    e = e.replace(">=0", f"{c} >= 0").replace(">0 AND <=16", f"{c} > 0 AND {c} <= 16").replace(">0", f"{c} > 0") if ">" in e and c not in e else e
    return f"ALTER TABLE {t} ADD CONSTRAINT ck_{t}_{c} CHECK ({e})"
ck_sql = [chk_sql(*x) for x in chks]
extra = ["ALTER TABLE tblWorkOrder ADD CONSTRAINT ck_tblWorkOrder_dates CHECK (DueDate IS NULL OR DueDate >= OpenedDate)",
         "ALTER TABLE tblWorkOrder ADD CONSTRAINT ck_tblWorkOrder_closed CHECK (ClosedDate IS NULL OR ClosedDate >= OpenedDate)"]
all_access = acc + uq + fk_sql + ck_sql + extra
(ROOT / "sql/schema_access.sql").write_text("-- Access (ACE/Jet ANSI-92) DDL. Run via ADO (CurrentProject.Connection.Execute), one statement at a time.\n" + ";\n".join(all_access) + ";\n")
(ROOT / "sql/schema_sqlite_test.sql").write_text("PRAGMA foreign_keys=ON;\n" + "\n".join(sq))
# VBA setup module
v = ['Attribute VB_Name = "modSetupSchema"', "Option Compare Database", "Option Explicit", "",
     "' GENERATED by generator/build_p2.py - do not edit by hand.", "' Run CreateSchema once in a new empty .accdb (Immediate Window: CreateSchema).", "",
     "Public Sub CreateSchema()", "    Dim s As Collection: Set s = New Collection", "    Dim v As Variant, cn As Object: Set cn = CurrentProject.Connection"]
for st in all_access: v.append(f'    s.Add "{st}"')
v += ["    On Error GoTo EH", "    For Each v In s", "        cn.Execute CStr(v)", "    Next v",
      '    MsgBox "Schema created: " & s.Count & " statements.", vbInformation, "Setup"', "    Exit Sub",
      "EH:", '    MsgBox "Failed on: " & Left$(CStr(v), 80) & vbCrLf & Err.Description, vbCritical, "Setup"', "End Sub"]
(ROOT / "vba/modSetupSchema.bas").write_text("\r\n".join(v) + "\r\n")
# data dictionary
d = ["# Data Dictionary - Rail Car Maintenance Tracker", "*All seed data is SYNTHETIC.*", "",
     "Normalisation: 3NF. Lookups (status, priority, type) are separate tables; labour and parts are child tables of the work order, so no repeating groups or derived totals are stored.", ""]
for t, (desc, cols) in T.items():
    d += [f"## {t}", desc, "", "| Column | Access type | Key / constraint | Description |", "|---|---|---|---|"]
    for c in cols: d.append(f"| {c[0]} | {c[1]} | {'PK' if c[3]==PK else (c[3] or '-')} | {c[4]} |")
    d.append("")
d += ["## Business rules enforced in VBA (modValidation)", "- Defect description at least 10 characters; opened date not in future.",
      "- DueDate/ClosedDate not before OpenedDate; closed date not in future.", "- Odometer cannot be lower than the car's previous work-order odometer.",
      "- A work order cannot be set to Closed without a closed date, closure notes and at least one labour entry.",
      "- No second open Corrective work order with the same defect text on the same car.",
      "- Labour: > 0 and <= 16 h per entry, <= 16 h per technician per day, not before WO opened date, not on closed WOs.",
      "- Parts: quantity whole number > 0; not on closed work orders.", "- Car number format `AAA-nnnn` style (letters, hyphen, digits) and unique."]
(ROOT / "docs/DATA_DICTIONARY.md").write_text("\n".join(d))
m = ["erDiagram"] + [f"  {rt} ||--o{{ {t} : \"{c}\"" for t, c, rt, rc in fks]
(ROOT / "docs/ERD.mmd").write_text("\n".join(m))
# seed
def w(name, rows, hdr):
    with open(ROOT / f"seed/{name}.csv", "w", newline="") as f: cw = csv.writer(f); cw.writerow(hdr); cw.writerows(rows)
w("tblCarType", [(1,"LRV-A","SynthBuild",12000,90),(2,"LRV-B","SynthBuild",15000,120),(3,"Subway-T","MockRail",20000,180)], ["CarTypeID","TypeName","Manufacturer","PMIntervalKm","PMIntervalDays"])
w("tblCarStatus", [(1,"Active"),(2,"In Shop"),(3,"Stored"),(4,"Retired")], ["CarStatusID","StatusName"])
w("tblLocation", [(1,"North Yard","Yard"),(2,"Main Shop","Shop"),(3,"South Yard","Yard"),(4,"Storage Track 1","Storage")], ["LocationID","LocationName","LocationType"])
w("tblPriority", [(1,"Critical",24),(2,"High",72),(3,"Normal",168),(4,"Low",336)], ["PriorityID","PriorityName","TargetHours"])
w("tblWOType", [(1,"Corrective"),(2,"Preventive"),(3,"Inspection"),(4,"Campaign")], ["WOTypeID","WOTypeName"])
w("tblWOStatus", [(1,"Open"),(2,"In Progress"),(3,"On Hold"),(4,"Closed")], ["WOStatusID","WOStatusName"])
first = "Alex Sam Jordan Casey Riley Morgan Taylor Jamie Drew Quinn Avery Rowan".split(); trades = ["Electrical","Mechanical","Body","Electrical"]
techs = [(i+1, f"E{1001+i}", f"{first[i]} Example", trades[i%4], -1) for i in range(12)]
w("tblTechnician", techs, ["TechID","EmployeeNo","FullName","Trade","IsActive"])
cars = []
for i in range(40):
    ct = 1 + i % 3; cars.append((i+1, f"{'LA' if ct==1 else 'LB' if ct==2 else 'ST'}-{4000+i}", ct, 1 if i % 9 else 2, random.choice([1,2,3,4]), f"{random.randint(2012,2022)}-0{random.randint(1,9)}-15", 0))
parts_ = [(i+1, f"P-{2000+i}", n, round(c,2)) for i,(n,c) in enumerate([("Door motor",845.5),("Brake pad set",212.0),("HVAC compressor",1290.0),("Traction contactor",640.25),("Pantograph carbon strip",96.8),("Wheel bearing",388.0),("Coupler seal kit",54.1),("LED light panel",72.3)])]
w("tblPart", parts_, ["PartID","PartNumber","PartName","UnitCost"])
defects = ["Door fails to close fully on side B","Brake pad wear beyond limit","HVAC not cooling in car interior","Intermittent traction fault code","Pantograph carbon strip worn","Wheel bearing noise during acceleration","Coupler air leak detected","Interior lighting panel flickering"]
wo, lab, pu = [], [], []
odo = {c[0]: random.randint(40000, 900000) for c in cars}; base = dt.date(2025, 1, 6)
for n in range(1, 61):
    car = random.choice(cars)[0]; op = base + dt.timedelta(days=random.randint(0, 300)); odo[car] += random.randint(500, 9000)
    closed = n % 4 != 0; typ = random.choice([1,1,1,2,3]); st = 4 if closed else random.choice([1,2,3])
    cl = (op + dt.timedelta(days=random.randint(1, 12))).isoformat() if closed else ""
    wo.append((n, car, typ, random.choice([1,2,3,3,4]), st, random.randint(1,12), op.isoformat(), (op+dt.timedelta(days=14)).isoformat(), cl, odo[car], random.choice(defects) + f" (WO {n})", "Repaired and tested OK" if closed else ""))
    for _ in range(random.randint(1, 3 if closed else 2)):
        lab.append((len(lab)+1, n, random.randint(1,12), (op+dt.timedelta(days=random.randint(0,3))).isoformat(), random.choice([1.5,2,3.5,4,6,8])))
    for _ in range(random.randint(0, 2)): pu.append((len(pu)+1, n, random.randint(1,8), random.randint(1,4)))
# make odometers monotonic by opened date per car (matches the VBA business rule)
by = {}
for i, r in enumerate(wo): by.setdefault(r[1], []).append(i)
for car, idxs in by.items():
    idxs.sort(key=lambda i: (wo[i][6], wo[i][0])); cur = random.randint(40000, 900000)
    for i in idxs:
        cur += random.randint(500, 9000); r = list(wo[i]); r[9] = cur; wo[i] = tuple(r)
    odo[car] = cur
cars = [(c[0],c[1],c[2],c[3],c[4],c[5],odo[c[0]]) for c in cars]
w("tblCar", cars, ["CarID","CarNumber","CarTypeID","CarStatusID","LocationID","InServiceDate","CurrentOdometerKm"])
w("tblWorkOrder", wo, ["WOID","CarID","WOTypeID","PriorityID","WOStatusID","AssignedTechID","OpenedDate","DueDate","ClosedDate","OdometerKm","DefectDescription","ClosureNotes"])
w("tblLabour", lab, ["LabourID","WOID","TechID","WorkDate","Hours"]); w("tblPartUsed", pu, ["PartUsedID","WOID","PartID","Quantity"])
print(f"Generated {len(all_access)} DDL statements, {len(T)} tables, {len(wo)} synthetic work orders")
