# Project 2 - Access + VBA Rail Car Maintenance Tracker
> Synthetic data. Access/VBA code was written but **not executed in Access** (built on Linux). Schema, seed integrity and business-rule data checks were tested in SQLite: `python generator/test_schema.py` (8 tests).

- `generator/build_p2.py` - single source of truth -> `sql/schema_access.sql`, `vba/modSetupSchema.bas`, `docs/DATA_DICTIONARY.md`, `docs/ERD.mmd`, `seed/*.csv`
- `vba/` - `modValidation`, form code-behind (`frmWorkOrder`, `sfrmLabour`, `sfrmParts`, `frmCar`), `modReports`, `modSeed`
- `sql/queries_access.sql` - saved queries for reports
- `docs/` - BUILD_GUIDE (start here), USER_GUIDE, DATA_DICTIONARY, ERD
