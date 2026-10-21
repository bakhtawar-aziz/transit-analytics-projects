# Build guide - Rail Car Maintenance Tracker (Access + VBA)
> **Synthetic data only.** Files here were generated and the schema/seed logic tested in SQLite on Linux; the Access/VBA parts must be assembled and tested in Microsoft Access (Windows) - I could not run Access here.

## 1. Create the database (about 10 minutes)
1. New blank desktop database `RailCarTracker.accdb`. Enable macros/trust the folder.
2. Alt+F11 > File > Import File: `vba/modSetupSchema.bas`, `modValidation.bas`, `modReports.bas`, `modSeed.bas`.
3. Immediate Window (Ctrl+G): `CreateSchema` (creates 12 tables, unique indexes, FKs, CHECK constraints via ADO). Then Database Tools > Relationships: add all tables, tick *Enforce Referential Integrity* (already enforced by the FKs).
4. `ImportSeedData "C:\...\seed\"` to load the synthetic rows.
5. Create queries from `sql/queries_access.sql` (SQL view), names as in the comments (`qryWOCost` before `qryCarHistory`).

## 2. Forms (design spec - control names must match the code-behind)
| Form | Record source | Controls |
|---|---|---|
| `frmCar` | tblCar | txtCarID, txtCarNumber, cboCarType (tblCarType), cboStatus (tblCarStatus), cboLocation (tblLocation), txtInService, txtOdometer |
| `frmWorkOrder` | tblWorkOrder | txtWOID, cboCar (CarNumber, bound CarID), cboWOType, cboPriority, cboStatus, cboTech (active techs), txtOpenedDate, txtDueDate, txtClosedDate, txtOdometer, txtDefect, txtClosureNotes, cmdCloseWO, cmdUndo; subforms `sfrmLabour`, `sfrmParts` |
| `sfrmLabour` | tblLabour (continuous) | txtLabourID, cboTech, txtWorkDate, txtHours; Link: txtWOID -> WOID |
| `sfrmParts` | tblPartUsed (continuous) | cboPart (PartNumber+PartName), txtQuantity; Link: txtWOID -> WOID |
| `frmDateRange` | unbound | txtFrom, txtTo, cmdRun (calls `OpenLabourByTech`) |
| `frmMain` | unbound | buttons calling the `modReports` launchers; a car combo for Car History |

Open each form in Design view, then Form Properties > *Has Module* = Yes and paste the matching `vba/Form_*.cls` body (everything after the `Attribute VB_Name` line). Set text-box Format/Input Mask (short date) and combo `Limit To List = Yes`, `Allow Edits = No` on key fields.

## 3. Reports
Create from the queries: `rptOpenWorkOrders` (group by priority), `rptOverdueWorkOrders`, `rptCarHistory`, `rptLabourByTech`, `rptPMDue`. In each report's module add: `Private Sub Report_NoData(Cancel As Integer): ReportNoData Cancel: End Sub`.

## 4. Test checklist
Try each: blank defect (blocked); due before opened; future opened date; odometer lower than an earlier WO; closing with no labour; labour of 17 h; two labour entries totalling >16 h for one tech/day; labour on a closed WO; quantity 0 or 2.5; duplicate car number; duplicate open corrective defect.
Then split the database (Database Tools > Access Database) for multi-user use, and compact/repair.
