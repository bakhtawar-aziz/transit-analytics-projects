VERSION 1.0 CLASS
BEGIN
  MultiUse = -1
END
Attribute VB_Name = "Form_sfrmParts"
Option Compare Database
Option Explicit
' Continuous subform bound to tblPartUsed; link on WOID. Controls: cboPart, txtQuantity.

Private Sub Form_BeforeUpdate(Cancel As Integer)
    Dim msg As String
    msg = ValidatePartUsed(Me.Parent!txtWOID.Value, Me.cboPart.Value, Me.txtQuantity.Value)
    If Len(msg) > 0 Then MsgBox msg, vbExclamation, "Parts used": Cancel = True
End Sub
