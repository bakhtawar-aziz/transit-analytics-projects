"""Sanity-test the normalised schema + SYNTHETIC seed in SQLite (FKs on). Access/VBA itself must be tested inside Access."""
import sqlite3, csv, pathlib, unittest
R = pathlib.Path(__file__).resolve().parents[1]
class T(unittest.TestCase):
    @classmethod
    def setUpClass(c):
        c.db = sqlite3.connect(":memory:"); c.db.executescript((R/"sql/schema_sqlite_test.sql").read_text())
        order = ["tblCarType","tblCarStatus","tblLocation","tblPriority","tblWOType","tblWOStatus","tblTechnician","tblCar","tblPart","tblWorkOrder","tblLabour","tblPartUsed"]
        for t in order:
            rows = list(csv.reader(open(R/f"seed/{t}.csv"))); h = rows[0]
            c.db.executemany(f"INSERT INTO {t} ({','.join(h)}) VALUES ({','.join('?'*len(h))})", [[v if v != "" else None for v in r] for r in rows[1:]])
    def q(s, *a): pass
    def test_fk_integrity(self): self.assertEqual(self.db.execute("PRAGMA foreign_key_check").fetchall(), [])
    def test_closed_have_dates_and_notes(self):
        n = self.db.execute("SELECT COUNT(*) FROM tblWorkOrder WHERE WOStatusID=4 AND (ClosedDate IS NULL OR ClosureNotes IS NULL)").fetchone()[0]; self.assertEqual(n, 0)
    def test_closed_after_opened(self):
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM tblWorkOrder WHERE ClosedDate<OpenedDate OR DueDate<OpenedDate").fetchone()[0], 0)
    def test_odometer_monotonic(self):
        bad = self.db.execute("""SELECT COUNT(*) FROM tblWorkOrder a JOIN tblWorkOrder b ON a.CarID=b.CarID AND a.OpenedDate<b.OpenedDate AND a.OdometerKm>b.OdometerKm""").fetchone()[0]; self.assertEqual(bad, 0)
    def test_closed_wo_have_labour(self):
        n = self.db.execute("SELECT COUNT(*) FROM tblWorkOrder w WHERE WOStatusID=4 AND NOT EXISTS (SELECT 1 FROM tblLabour l WHERE l.WOID=w.WOID)").fetchone()[0]; self.assertEqual(n, 0)
    def test_labour_limits(self):
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM tblLabour WHERE Hours<=0 OR Hours>16").fetchone()[0], 0)
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM (SELECT TechID,WorkDate,SUM(Hours) h FROM tblLabour GROUP BY 1,2 HAVING h>16)").fetchone()[0], 0)
    def test_labour_not_before_open(self):
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM tblLabour l JOIN tblWorkOrder w USING(WOID) WHERE l.WorkDate<w.OpenedDate").fetchone()[0], 0)
    def test_car_odometer_covers_wo(self):
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM tblCar c WHERE CurrentOdometerKm < (SELECT MAX(OdometerKm) FROM tblWorkOrder w WHERE w.CarID=c.CarID)").fetchone()[0], 0)
if __name__ == "__main__": unittest.main(verbosity=1)
