Attribute VB_Name = "modValidation"
Option Compare Database
Option Explicit
' Central business-rule validation. Each Validate* function returns "" when valid,
' otherwise a message listing every problem (one per line). Forms call these in BeforeUpdate.

Private Const MAX_HOURS_ENTRY As Double = 16
Private Const MAX_HOURS_DAY As Double = 16

Public Function IsBlank(ByVal v As Variant) As Boolean
    IsBlank = IsNull(v) Or Trim$(Nz(v, "") & "") = ""
End Function

Public Function SqlText(ByVal s As String) As String        ' escape single quotes for criteria strings
    SqlText = Replace(s, "'", "''")
End Function

Private Function SqlDate(ByVal d As Date) As String
    SqlDate = "#" & Format$(d, "yyyy-mm-dd") & "#"
End Function

Private Sub AddErr(ByRef msg As String, ByVal text As String)
    msg = msg & IIf(Len(msg) > 0, vbCrLf, "") & "- " & text
End Sub

Public Function StatusId(ByVal statusName As String) As Long
    StatusId = Nz(DLookup("WOStatusID", "tblWOStatus", "WOStatusName='" & SqlText(statusName) & "'"), 0)
End Function

Public Function ValidateWorkOrder(ByVal woId As Variant, ByVal carId As Variant, ByVal woTypeId As Variant, _
        ByVal priorityId As Variant, ByVal statusId_ As Variant, ByVal openedDate As Variant, ByVal dueDate As Variant, _
        ByVal closedDate As Variant, ByVal odometer As Variant, ByVal defect As Variant, ByVal closureNotes As Variant) As String
    Dim m As String, id As Long, crit As String
    id = Nz(woId, 0)
    If IsBlank(carId) Then AddErr m, "Car is required."
    If IsBlank(woTypeId) Then AddErr m, "Work order type is required."
    If IsBlank(priorityId) Then AddErr m, "Priority is required."
    If IsBlank(statusId_) Then AddErr m, "Status is required."
    If IsBlank(openedDate) Then
        AddErr m, "Opened date is required."
    ElseIf Not IsDate(openedDate) Then
        AddErr m, "Opened date is not a valid date."
    Else
        If CDate(openedDate) > Date Then AddErr m, "Opened date cannot be in the future."
        If CDate(openedDate) < #1/1/2000# Then AddErr m, "Opened date is before 2000 - check the year."
    End If
    If IsBlank(defect) Then
        AddErr m, "Defect description is required."
    ElseIf Len(Trim$(defect)) < 10 Then
        AddErr m, "Defect description must be at least 10 characters."
    End If
    If Not IsBlank(dueDate) And IsDate(openedDate) And IsDate(dueDate) Then
        If CDate(dueDate) < CDate(openedDate) Then AddErr m, "Due date cannot be before the opened date."
    End If
    If Not IsBlank(closedDate) And IsDate(openedDate) And IsDate(closedDate) Then
        If CDate(closedDate) < CDate(openedDate) Then AddErr m, "Closed date cannot be before the opened date."
        If CDate(closedDate) > Date Then AddErr m, "Closed date cannot be in the future."
    End If
    ' odometer must not decrease relative to the car's earlier work orders
    If Not IsBlank(odometer) And Not IsBlank(carId) And IsDate(openedDate) Then
        If Not IsNumeric(odometer) Then
            AddErr m, "Odometer must be a number."
        ElseIf CLng(odometer) < 0 Then
            AddErr m, "Odometer cannot be negative."
        Else
            crit = "CarID=" & CLng(carId) & " AND WOID<>" & id & " AND OpenedDate<=" & SqlDate(CDate(openedDate))
            If CLng(odometer) < Nz(DMax("OdometerKm", "tblWorkOrder", crit), 0) Then
                AddErr m, "Odometer is lower than this car's reading on an earlier work order (" & _
                    Format$(DMax("OdometerKm", "tblWorkOrder", crit), "#,##0") & " km)."
            End If
        End If
    End If
    ' duplicate open corrective WO
    If Not IsBlank(carId) And Not IsBlank(woTypeId) And Not IsBlank(defect) Then
        If CLng(woTypeId) = Nz(DLookup("WOTypeID", "tblWOType", "WOTypeName='Corrective'"), -1) And _
           CLng(statusId_) <> StatusId("Closed") Then
            If DCount("WOID", "tblWorkOrder", "CarID=" & CLng(carId) & " AND WOID<>" & id & _
                " AND WOStatusID<>" & StatusId("Closed") & " AND WOTypeID=" & CLng(woTypeId) & _
                " AND DefectDescription='" & SqlText(Trim$(defect)) & "'") > 0 Then
                AddErr m, "An open corrective work order with the same defect already exists for this car."
            End If
        End If
    End If
    ' closing rules
    If Not IsBlank(statusId_) Then
        If CLng(statusId_) = StatusId("Closed") Then
            If IsBlank(closedDate) Then AddErr m, "A closed work order needs a closed date."
            If IsBlank(closureNotes) Then AddErr m, "A closed work order needs closure notes."
            If id = 0 Then
                AddErr m, "Save the work order and add labour before closing it."
            ElseIf DCount("LabourID", "tblLabour", "WOID=" & id) = 0 Then
                AddErr m, "A work order cannot be closed without at least one labour entry."
            End If
        ElseIf Not IsBlank(closedDate) Then
            AddErr m, "Closed date is set but status is not Closed."
        End If
    End If
    ValidateWorkOrder = m
End Function

Public Function ValidateLabour(ByVal labourId As Variant, ByVal woId As Variant, ByVal techId As Variant, _
        ByVal workDate As Variant, ByVal hours As Variant) As String
    Dim m As String, opened As Variant, st As Variant, already As Double
    If IsBlank(woId) Then AddErr m, "Work order is required."
    If IsBlank(techId) Then AddErr m, "Technician is required."
    If IsBlank(workDate) Or Not IsDate(workDate) Then AddErr m, "A valid work date is required."
    If IsBlank(hours) Or Not IsNumeric(hours) Then
        AddErr m, "Hours must be a number."
    ElseIf CDbl(hours) <= 0 Or CDbl(hours) > MAX_HOURS_ENTRY Then
        AddErr m, "Hours must be greater than 0 and at most " & MAX_HOURS_ENTRY & " per entry."
    End If
    If Len(m) = 0 Then
        opened = DLookup("OpenedDate", "tblWorkOrder", "WOID=" & CLng(woId))
        st = DLookup("WOStatusID", "tblWorkOrder", "WOID=" & CLng(woId))
        If CDate(workDate) < CDate(opened) Then AddErr m, "Work date is before the work order was opened."
        If CDate(workDate) > Date Then AddErr m, "Work date cannot be in the future."
        If CLng(st) = StatusId("Closed") Then AddErr m, "Cannot add labour to a closed work order."
        already = Nz(DSum("Hours", "tblLabour", "TechID=" & CLng(techId) & " AND WorkDate=" & SqlDate(CDate(workDate)) & _
                  " AND LabourID<>" & Nz(labourId, 0)), 0)
        If already + CDbl(hours) > MAX_HOURS_DAY Then
            AddErr m, "This technician would exceed " & MAX_HOURS_DAY & " hours on that date (" & already & " already booked)."
        End If
        If Nz(DLookup("IsActive", "tblTechnician", "TechID=" & CLng(techId)), False) = False Then AddErr m, "Technician is not active."
    End If
    ValidateLabour = m
End Function

Public Function ValidatePartUsed(ByVal woId As Variant, ByVal partId As Variant, ByVal qty As Variant) As String
    Dim m As String
    If IsBlank(woId) Then AddErr m, "Work order is required."
    If IsBlank(partId) Then AddErr m, "Part is required."
    If IsBlank(qty) Or Not IsNumeric(qty) Then
        AddErr m, "Quantity must be a number."
    ElseIf CDbl(qty) <> Int(CDbl(qty)) Or CDbl(qty) <= 0 Then
        AddErr m, "Quantity must be a whole number greater than 0."
    End If
    If Not IsBlank(woId) Then
        If Nz(DLookup("WOStatusID", "tblWorkOrder", "WOID=" & CLng(woId)), 0) = StatusId("Closed") Then AddErr m, "Cannot add parts to a closed work order."
    End If
    ValidatePartUsed = m
End Function

Public Function ValidateCar(ByVal carId As Variant, ByVal carNumber As Variant, ByVal carTypeId As Variant, _
        ByVal inServiceDate As Variant, ByVal odometer As Variant) As String
    Dim m As String
    If IsBlank(carNumber) Then
        AddErr m, "Car number is required."
    Else
        If Not (UCase$(Trim$(carNumber)) Like "[A-Z][A-Z]*-#*") Then AddErr m, "Car number must look like LA-4001 (letters, hyphen, digits)."
        If DCount("CarID", "tblCar", "CarNumber='" & SqlText(UCase$(Trim$(carNumber))) & "' AND CarID<>" & Nz(carId, 0)) > 0 Then AddErr m, "Car number already exists."
    End If
    If IsBlank(carTypeId) Then AddErr m, "Car type is required."
    If IsBlank(inServiceDate) Or Not IsDate(inServiceDate) Then
        AddErr m, "A valid in-service date is required."
    ElseIf CDate(inServiceDate) > Date Then
        AddErr m, "In-service date cannot be in the future."
    End If
    If IsBlank(odometer) Or Not IsNumeric(odometer) Then
        AddErr m, "Odometer must be a number."
    ElseIf CLng(odometer) < 0 Then
        AddErr m, "Odometer cannot be negative."
    End If
    ValidateCar = m
End Function
