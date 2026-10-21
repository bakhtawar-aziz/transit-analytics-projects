# Data Dictionary - Rail Car Maintenance Tracker
*All seed data is SYNTHETIC.*

Normalisation: 3NF. Lookups (status, priority, type) are separate tables; labour and parts are child tables of the work order, so no repeating groups or derived totals are stored.

## tblCarType
Rail car classes and their preventive-maintenance intervals

| Column | Access type | Key / constraint | Description |
|---|---|---|---|
| CarTypeID | AUTOINCREMENT | PK | Surrogate key |
| TypeName | TEXT(50) | NOT NULL UNIQUE | Car class name, e.g. LRV-A |
| Manufacturer | TEXT(50) | - | Builder of the car class |
| PMIntervalKm | LONG | NOT NULL | Preventive-maintenance interval in km |
| PMIntervalDays | LONG | NOT NULL | Preventive-maintenance interval in calendar days |

## tblCarStatus
Lookup: operational status of a car

| Column | Access type | Key / constraint | Description |
|---|---|---|---|
| CarStatusID | AUTOINCREMENT | PK | Surrogate key |
| StatusName | TEXT(30) | NOT NULL UNIQUE | Active, In Shop, Stored, Retired |

## tblLocation
Yards, shops and storage tracks

| Column | Access type | Key / constraint | Description |
|---|---|---|---|
| LocationID | AUTOINCREMENT | PK | Surrogate key |
| LocationName | TEXT(50) | NOT NULL UNIQUE | Location name |
| LocationType | TEXT(20) | NOT NULL | Yard, Shop or Storage |

## tblCar
One row per rail car

| Column | Access type | Key / constraint | Description |
|---|---|---|---|
| CarID | AUTOINCREMENT | PK | Surrogate key |
| CarNumber | TEXT(10) | NOT NULL UNIQUE | Operating car number |
| CarTypeID | LONG | NOT NULL FK tblCarType.CarTypeID | Car class |
| CarStatusID | LONG | NOT NULL FK tblCarStatus.CarStatusID | Current status |
| LocationID | LONG | FK tblLocation.LocationID | Where the car is now |
| InServiceDate | DATETIME | NOT NULL | Date entered revenue service |
| CurrentOdometerKm | LONG | NOT NULL CHECK >=0 | Latest known odometer (km) |

## tblTechnician
Maintenance staff

| Column | Access type | Key / constraint | Description |
|---|---|---|---|
| TechID | AUTOINCREMENT | PK | Surrogate key |
| EmployeeNo | TEXT(10) | NOT NULL UNIQUE | Employee number (synthetic) |
| FullName | TEXT(60) | NOT NULL | Technician name (synthetic) |
| Trade | TEXT(30) | - | Electrical, Mechanical, Body... |
| IsActive | YESNO | NOT NULL | Currently employed/assignable |

## tblPriority
Lookup: work-order priority

| Column | Access type | Key / constraint | Description |
|---|---|---|---|
| PriorityID | AUTOINCREMENT | PK | Surrogate key |
| PriorityName | TEXT(20) | NOT NULL UNIQUE | Critical, High, Normal, Low |
| TargetHours | LONG | NOT NULL | Target hours to complete |

## tblWOType
Lookup: work-order type

| Column | Access type | Key / constraint | Description |
|---|---|---|---|
| WOTypeID | AUTOINCREMENT | PK | Surrogate key |
| WOTypeName | TEXT(30) | NOT NULL UNIQUE | Corrective, Preventive, Inspection, Campaign |

## tblWOStatus
Lookup: work-order status

| Column | Access type | Key / constraint | Description |
|---|---|---|---|
| WOStatusID | AUTOINCREMENT | PK | Surrogate key |
| WOStatusName | TEXT(20) | NOT NULL UNIQUE | Open, In Progress, On Hold, Closed |

## tblWorkOrder
Maintenance work orders against cars

| Column | Access type | Key / constraint | Description |
|---|---|---|---|
| WOID | AUTOINCREMENT | PK | Work-order number |
| CarID | LONG | NOT NULL FK tblCar.CarID | Car being worked on |
| WOTypeID | LONG | NOT NULL FK tblWOType.WOTypeID | Type |
| PriorityID | LONG | NOT NULL FK tblPriority.PriorityID | Priority |
| WOStatusID | LONG | NOT NULL FK tblWOStatus.WOStatusID | Status |
| AssignedTechID | LONG | FK tblTechnician.TechID | Lead technician |
| OpenedDate | DATETIME | NOT NULL | Date opened |
| DueDate | DATETIME | - | Target completion date (>= OpenedDate) |
| ClosedDate | DATETIME | - | Date closed (>= OpenedDate); required when status is Closed |
| OdometerKm | LONG | CHECK >=0 | Car odometer when opened; must not decrease for the same car |
| DefectDescription | TEXT(255) | NOT NULL | Defect or task description (min 10 characters, enforced by VBA) |
| ClosureNotes | TEXT(255) | - | Required when closing |

## tblLabour
Labour hours booked to a work order

| Column | Access type | Key / constraint | Description |
|---|---|---|---|
| LabourID | AUTOINCREMENT | PK | Surrogate key |
| WOID | LONG | NOT NULL FK tblWorkOrder.WOID | Work order |
| TechID | LONG | NOT NULL FK tblTechnician.TechID | Technician |
| WorkDate | DATETIME | NOT NULL | Date worked |
| Hours | DOUBLE | NOT NULL CHECK >0 AND <=16 | Hours (max 16 per entry) |

## tblPart
Parts catalogue

| Column | Access type | Key / constraint | Description |
|---|---|---|---|
| PartID | AUTOINCREMENT | PK | Surrogate key |
| PartNumber | TEXT(20) | NOT NULL UNIQUE | Part number (synthetic) |
| PartName | TEXT(60) | NOT NULL | Description |
| UnitCost | CURRENCY | NOT NULL CHECK >=0 | Unit cost |

## tblPartUsed
Parts consumed on a work order

| Column | Access type | Key / constraint | Description |
|---|---|---|---|
| PartUsedID | AUTOINCREMENT | PK | Surrogate key |
| WOID | LONG | NOT NULL FK tblWorkOrder.WOID | Work order |
| PartID | LONG | NOT NULL FK tblPart.PartID | Part |
| Quantity | LONG | NOT NULL CHECK >0 | Quantity used |

## Business rules enforced in VBA (modValidation)
- Defect description at least 10 characters; opened date not in future.
- DueDate/ClosedDate not before OpenedDate; closed date not in future.
- Odometer cannot be lower than the car's previous work-order odometer.
- A work order cannot be set to Closed without a closed date, closure notes and at least one labour entry.
- No second open Corrective work order with the same defect text on the same car.
- Labour: > 0 and <= 16 h per entry, <= 16 h per technician per day, not before WO opened date, not on closed WOs.
- Parts: quantity whole number > 0; not on closed work orders.
- Car number format `AAA-nnnn` style (letters, hyphen, digits) and unique.