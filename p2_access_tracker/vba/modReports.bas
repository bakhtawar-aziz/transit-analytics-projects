Attribute VB_Name = "modReports"
Option Compare Database
Option Explicit
' Report launchers with parameters and error handling. Called from the switchboard form (frmMain).

Public Sub OpenOpenWorkOrders(Optional ByVal carTypeId As Variant)
    Dim f As String
    If Not IsMissing(carTypeId) Then If Not IsNull(carTypeId) Then f = "CarTypeID=" & CLng(carTypeId)
    SafeOpenReport "rptOpenWorkOrders", f
End Sub

Public Sub OpenCarHistory(ByVal carId As Variant)
    If IsBlank(carId) Then MsgBox "Select a car first.", vbInformation: Exit Sub
    SafeOpenReport "rptCarHistory", "CarID=" & CLng(carId)
End Sub

Public Sub OpenOverdueWorkOrders()
    SafeOpenReport "rptOverdueWorkOrders"
End Sub

Public Sub OpenLabourByTech(ByVal fromDate As Date, ByVal toDate As Date)
    If toDate < fromDate Then MsgBox "'To' date is before 'From' date.", vbExclamation: Exit Sub
    ' qryLabourByTech reads the dates from the open frmDateRange form (see USER_GUIDE)
    SafeOpenReport "rptLabourByTech"
End Sub

Public Sub OpenPMDue()
    SafeOpenReport "rptPMDue"
End Sub

Private Sub SafeOpenReport(ByVal name As String, Optional ByVal where_ As String = "")
    On Error GoTo EH
    DoCmd.OpenReport name, acViewPreview, , where_
    Exit Sub
EH:
    If Err.Number = 2501 Then Exit Sub                       ' cancelled by the report's NoData handler
    MsgBox "Could not open " & name & ": " & Err.Description, vbExclamation
End Sub

' Paste into each report's code module:   Private Sub Report_NoData(Cancel As Integer): ReportNoData Cancel: End Sub
Public Sub ReportNoData(ByRef Cancel As Integer)
    MsgBox "No records match the selected criteria.", vbInformation, "Report"
    Cancel = True
End Sub
