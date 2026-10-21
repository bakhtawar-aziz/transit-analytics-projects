Attribute VB_Name = "modSeed"
Option Compare Database
Option Explicit
' Imports the SYNTHETIC seed CSVs. Usage (Immediate Window): ImportSeedData "C:\path\to\seed\"
Public Sub ImportSeedData(ByVal folder As String)
    Dim t As Variant
    If Right$(folder, 1) <> "\" Then folder = folder & "\"
    On Error GoTo EH
    For Each t In Array("tblCarType", "tblCarStatus", "tblLocation", "tblPriority", "tblWOType", "tblWOStatus", _
                        "tblTechnician", "tblCar", "tblPart", "tblWorkOrder", "tblLabour", "tblPartUsed")   ' parents before children
        DoCmd.TransferText acImportDelim, , CStr(t), folder & t & ".csv", True
    Next t
    MsgBox "Seed data imported.", vbInformation
    Exit Sub
EH:
    MsgBox "Import failed on " & t & ": " & Err.Description, vbCritical
End Sub
