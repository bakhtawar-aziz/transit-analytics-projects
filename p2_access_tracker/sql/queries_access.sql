-- Access SQL for the saved queries behind the reports/forms.
-- qryOpenWorkOrders (rptOpenWorkOrders)
SELECT w.WOID, c.CarNumber, ct.TypeName, ct.CarTypeID, t.WOTypeName, p.PriorityName, s.WOStatusName, w.OpenedDate, w.DueDate,
       DateDiff("d", w.OpenedDate, Date()) AS DaysOpen, w.DefectDescription
FROM (((((tblWorkOrder AS w INNER JOIN tblCar AS c ON w.CarID=c.CarID) INNER JOIN tblCarType AS ct ON c.CarTypeID=ct.CarTypeID)
  INNER JOIN tblWOType AS t ON w.WOTypeID=t.WOTypeID) INNER JOIN tblPriority AS p ON w.PriorityID=p.PriorityID)
  INNER JOIN tblWOStatus AS s ON w.WOStatusID=s.WOStatusID)
WHERE s.WOStatusName<>"Closed" ORDER BY p.PriorityID, w.OpenedDate;

-- qryOverdueWorkOrders (rptOverdueWorkOrders)
SELECT w.WOID, c.CarNumber, w.DueDate, DateDiff("d", w.DueDate, Date()) AS DaysOverdue, w.DefectDescription
FROM (tblWorkOrder AS w INNER JOIN tblCar AS c ON w.CarID=c.CarID) INNER JOIN tblWOStatus AS s ON w.WOStatusID=s.WOStatusID
WHERE s.WOStatusName<>"Closed" AND w.DueDate<Date() ORDER BY w.DueDate;

-- qryWOCost (labour hours and parts cost per WO; labour rate is a parameter on the report)
SELECT w.WOID, Nz(l.Hrs,0) AS LabourHours, Nz(pc.PartsCost,0) AS PartsCost
FROM (tblWorkOrder AS w LEFT JOIN (SELECT WOID, SUM(Hours) AS Hrs FROM tblLabour GROUP BY WOID) AS l ON w.WOID=l.WOID)
LEFT JOIN (SELECT pu.WOID, SUM(pu.Quantity*p.UnitCost) AS PartsCost FROM tblPartUsed AS pu INNER JOIN tblPart AS p ON pu.PartID=p.PartID GROUP BY pu.WOID) AS pc ON w.WOID=pc.WOID;

-- qryCarHistory (rptCarHistory; filter CarID)
SELECT c.CarID, c.CarNumber, w.WOID, w.OpenedDate, w.ClosedDate, t.WOTypeName, w.OdometerKm, w.DefectDescription, q.LabourHours, q.PartsCost
FROM ((tblWorkOrder AS w INNER JOIN tblCar AS c ON w.CarID=c.CarID) INNER JOIN tblWOType AS t ON w.WOTypeID=t.WOTypeID)
INNER JOIN qryWOCost AS q ON w.WOID=q.WOID ORDER BY w.OpenedDate DESC;

-- qryLabourByTech (rptLabourByTech; dates read from open form frmDateRange)
SELECT t.FullName, t.Trade, SUM(l.Hours) AS TotalHours, COUNT(DISTINCT l.WOID) AS WorkOrders
FROM tblLabour AS l INNER JOIN tblTechnician AS t ON l.TechID=t.TechID
WHERE l.WorkDate BETWEEN [Forms]![frmDateRange]![txtFrom] AND [Forms]![frmDateRange]![txtTo]
GROUP BY t.FullName, t.Trade ORDER BY SUM(l.Hours) DESC;

-- qryPMDue (rptPMDue): cars whose last closed Preventive WO is older than the type's interval, by days or by km
SELECT c.CarNumber, ct.TypeName, lp.LastPMDate, lp.LastPMKm, DateDiff("d", lp.LastPMDate, Date()) AS DaysSincePM, c.CurrentOdometerKm - lp.LastPMKm AS KmSincePM
FROM (tblCar AS c INNER JOIN tblCarType AS ct ON c.CarTypeID=ct.CarTypeID)
LEFT JOIN (SELECT w.CarID, MAX(w.ClosedDate) AS LastPMDate, MAX(w.OdometerKm) AS LastPMKm FROM tblWorkOrder AS w
  INNER JOIN tblWOType AS t ON w.WOTypeID=t.WOTypeID WHERE t.WOTypeName="Preventive" AND w.ClosedDate IS NOT NULL GROUP BY w.CarID) AS lp ON c.CarID=lp.CarID
WHERE lp.LastPMDate IS NULL OR DateDiff("d", lp.LastPMDate, Date())>ct.PMIntervalDays OR c.CurrentOdometerKm-lp.LastPMKm>ct.PMIntervalKm;
