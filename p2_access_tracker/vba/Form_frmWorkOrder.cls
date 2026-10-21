VERSION 1.0 CLASS
BEGIN
  MultiUse = -1
END
Attribute VB_Name = "Form_frmWorkOrder"
Option Compare Database
Option Explicit
' Bound to tblWorkOrder (or qryWorkOrderForm). Controls: txtWOID, cboCar, cboWOType, cboPriority, cboStatus,
' cboTech, txtOpenedDate, txtDueDate, txtClosedDate, txtOdometer, txtDefect, txtClosureNotes, cmdCloseWO,
' cmdSave, cmdUndo. Subforms: sfrmLabour, sfrmParts.

Private Sub Form_Current()
    Dim isClosed As Boolean
    isClosed = (Nz(Me.cboStatus.Value, 0) = StatusId("Closed"))
    Me.cmdCloseWO.Enabled = Not Me.NewRecord And Not isClosed
    LockWhenClosed isClosed
    If Me.NewRecord Then
        Me.txtOpenedDate.DefaultValue = "Date()"
    End If
End Sub

Private Sub LockWhenClosed(ByVal isClosed As Boolean)
    Dim c As Control
    For Each c In Me.Controls
        Select Case c.Name
            Case "txtDefect", "txtOdometer", "txtOpenedDate", "cboCar", "cboWOType", "cboPriority"
                c.Locked = isClosed
        End Select
    Next c
    Me.sfrmLabour.Locked = isClosed: Me.sfrmParts.Locked = isClosed
End Sub

Private Sub cboCar_AfterUpdate()
    ' default the odometer to the car's latest known reading
    If IsBlank(Me.txtOdometer.Value) And Not IsBlank(Me.cboCar.Value) Then
        Me.txtOdometer.Value = DLookup("CurrentOdometerKm", "tblCar", "CarID=" & Me.cboCar.Value)
    End If
End Sub

Private Sub Form_BeforeUpdate(Cancel As Integer)
    Dim msg As String
    msg = ValidateWorkOrder(Me.txtWOID.Value, Me.cboCar.Value, Me.cboWOType.Value, Me.cboPriority.Value, _
          Me.cboStatus.Value, Me.txtOpenedDate.Value, Me.txtDueDate.Value, Me.txtClosedDate.Value, _
          Me.txtOdometer.Value, Me.txtDefect.Value, Me.txtClosureNotes.Value)
    If Len(msg) > 0 Then
        MsgBox "Please fix the following before saving:" & vbCrLf & vbCrLf & msg, vbExclamation, "Work Order"
        Cancel = True
    End If
End Sub

Private Sub Form_AfterUpdate()
    ' keep the car's current odometer in step with the highest work-order reading
    On Error GoTo EH
    If Not IsBlank(Me.txtOdometer.Value) Then
        CurrentDb.Execute "UPDATE tblCar SET CurrentOdometerKm=" & CLng(Me.txtOdometer.Value) & _
            " WHERE CarID=" & Me.cboCar.Value & " AND CurrentOdometerKm<" & CLng(Me.txtOdometer.Value), dbFailOnError
    End If
    Exit Sub
EH:
    MsgBox "Saved, but the car odometer could not be updated: " & Err.Description, vbExclamation
End Sub

Private Sub cmdCloseWO_Click()
    If Me.Dirty Then Me.Dirty = False                       ' save current edits (runs validation)
    Me.cboStatus.Value = StatusId("Closed")
    If IsBlank(Me.txtClosedDate.Value) Then Me.txtClosedDate.Value = Date
    If IsBlank(Me.txtClosureNotes.Value) Then
        Me.txtClosureNotes.SetFocus
        MsgBox "Enter closure notes, then click Close Work Order again.", vbInformation: Me.cboStatus.Undo: Me.txtClosedDate.Undo: Exit Sub
    End If
    On Error Resume Next
    Me.Dirty = False                                        ' BeforeUpdate blocks the save if rules fail
    If Err.Number <> 0 Then Err.Clear: Me.Undo
    On Error GoTo 0
    Form_Current
End Sub

Private Sub cmdUndo_Click()
    If Me.Dirty Then Me.Undo
End Sub

Private Sub Form_Error(DataErr As Integer, Response As Integer)
    Select Case DataErr
        Case 3200: MsgBox "This record is referenced by other records and cannot be deleted.", vbExclamation: Response = acDataErrContinue
        Case 3022: MsgBox "A record with that value already exists.", vbExclamation: Response = acDataErrContinue
        Case Else: Response = acDataErrDisplay
    End Select
End Sub

Private Sub Form_Delete(Cancel As Integer)
    If MsgBox("Delete this work order and its labour/parts?", vbQuestion + vbYesNo + vbDefaultButton2) = vbNo Then Cancel = True
End Sub
