import { Component, Inject } from '@angular/core';
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';

@Component({
  selector: 'app-confirm-dialog',
  standalone: true,
  imports: [MatDialogModule, MatButtonModule],
  template: `<h2 mat-dialog-title>{{data.title}}</h2><mat-dialog-content><p>{{data.message}}</p></mat-dialog-content><div mat-dialog-actions align="end"><button mat-button mat-dialog-close type="button">Cancelar</button><button mat-flat-button color="warn" [mat-dialog-close]="true">Confirmar</button></div>`
})
export class ConfirmDialogComponent {
  constructor(@Inject(MAT_DIALOG_DATA) public data: { title: string; message: string }, public dialogRef: MatDialogRef<ConfirmDialogComponent>) {}
}