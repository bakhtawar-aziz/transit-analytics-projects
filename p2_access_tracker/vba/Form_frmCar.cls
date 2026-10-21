VERSION 1.0 CLASS
BEGIN
  MultiUse = -1
END
Attribute VB_Name = "Form_frmCar"
Option Compare Database
Option Explicit
' Bound to tblCar. Controls: txtCarID, txtCarNumber, cboCarType, cboStatus, cboLocation, txtInService, txtOdometer.

Private Sub txtCarNumber_AfterUpdate()
    Me.txtCarNumber.Value = UCase$(Trim$(Nz(Me.txtCarNumber.Value, "")))
End Sub

Private Sub Form_BeforeUpdate(Cancel As Integer)
    Dim msg As String
    msg = ValidateCar(Me.txtCarID.Value, Me.txtCarNumber.Value, Me.cboCarType.Value, Me.txtInService.Value, Me.txtOdometer.Value)
    If Len(msg) > 0 Then MsgBox msg, vbExclamation, "Car": Cancel = True
End Sub
