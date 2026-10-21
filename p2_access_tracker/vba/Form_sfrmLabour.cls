VERSION 1.0 CLASS
BEGIN
  MultiUse = -1
END
Attribute VB_Name = "Form_sfrmLabour"
Option Compare Database
Option Explicit
' Continuous subform bound to tblLabour; LinkMasterFields = txtWOID, LinkChildFields = WOID.
' Controls: txtLabourID, txtWOID, cboTech, txtWorkDate, txtHours.

Private Sub Form_BeforeUpdate(Cancel As Integer)
    Dim msg As String
    msg = ValidateLabour(Me.txtLabourID.Value, Me.Parent!txtWOID.Value, Me.cboTech.Value, Me.txtWorkDate.Value, Me.txtHours.Value)
    If Len(msg) > 0 Then MsgBox msg, vbExclamation, "Labour entry": Cancel = True
End Sub

Private Sub Form_BeforeInsert(Cancel As Integer)
    If IsNull(Me.Parent!txtWOID.Value) Then
        MsgBox "Save the work order first.", vbInformation: Cancel = True
    End If
End Sub
