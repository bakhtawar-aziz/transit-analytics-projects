# User Guide - Rail Car Maintenance Tracker
*Demonstration system with synthetic data.*

## Open the tracker
Open `RailCarTracker.accdb` and click **Enable Content**. The main menu (`frmMain`) has buttons for Cars, Work Orders and Reports.

## Add or edit a car
Main menu > **Cars**. Car numbers look like `LA-4001`, must be unique, and are upper-cased automatically. Enter type, status, location, in-service date and current odometer, then move to a new record to save.

## Create a work order
1. Main menu > **Work Orders** > new record (`*`).
2. Pick the **Car**; the odometer fills in from the car's latest reading - correct it if needed (it cannot be lower than that car's earlier work orders).
3. Choose Type and Priority, enter the Defect description (at least 10 characters), optionally Due date and Assigned technician.
4. Save by moving to another record or pressing Shift+Enter. A message lists every rule that failed; fix them and save again.

## Record labour and parts
After the work order is saved, use the **Labour** grid (technician, date, hours) and the **Parts** grid (part, quantity). Limits: 0-16 h per entry, 16 h per technician per day, nothing before the opened date, nothing on closed work orders.

## Close a work order
Make sure labour is recorded, type the **Closure notes**, then click **Close Work Order**. The closed date is set to today and the form locks. If a rule blocks it, the message says what is missing.

## Reports
| Report | Use |
|---|---|
| Open Work Orders | Everything not closed, by priority; optional car-type filter |
| Overdue Work Orders | Open items past their due date |
| Car History | All work orders, labour hours and parts cost for one car |
| Labour by Technician | Enter From/To dates first |
| PM Due | Cars past their preventive-maintenance interval (days or km) |

## Common messages
| Message | Meaning / fix |
|---|---|
| Odometer is lower than... | Check the digits, or the earlier work order is wrong |
| Cannot be closed without labour | Add a labour line first |
| Cannot add labour to a closed work order | Reopen by changing status (supervisor) or log on a new WO |
| Record is referenced by other records | Child rows (labour/parts) exist; delete those first or leave the record |

## Data rules and backups
Rules are listed in `DATA_DICTIONARY.md`. Keep the database on a shared folder as a split front end/back end; back up the back end nightly. Report problems with the work-order number and the exact message text.
