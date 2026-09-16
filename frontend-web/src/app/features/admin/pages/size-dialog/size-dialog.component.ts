import { Component, Inject, inject } from '@angular/core';
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';
import { NonNullableFormBuilder, Validators } from '@angular/forms';
import { ReactiveFormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatDialogModule } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { AdminSize as Size } from '../../models/size-admin.model';

@Component({
  selector: 'app-size-dialog',
  standalone: true,
  imports: [ReactiveFormsModule, MatButtonModule, MatDialogModule, MatFormFieldModule, MatInputModule],
  template: `<h2 mat-dialog-title>{{data?.id_talla ? 'Editar' : 'Crear'} talla</h2><form [formGroup]="form" (ngSubmit)="save()" mat-dialog-content><mat-form-field><mat-label>Nombre</mat-label><input matInput formControlName="nombre"></mat-form-field><div mat-dialog-actions align="end"><button mat-button mat-dialog-close type="button">Cancelar</button><button mat-flat-button color="primary" [disabled]="form.invalid">Guardar</button></div></form>`
})
export class SizeDialogComponent {
  private ref = inject(MatDialogRef<SizeDialogComponent>);
  form = inject(NonNullableFormBuilder).group({ nombre: ['', [Validators.required, Validators.minLength(1)]] });
  constructor(@Inject(MAT_DIALOG_DATA) public data: Size | null) { if (data) this.form.patchValue(data); }
  save(): void { this.ref.close(this.form.getRawValue()); }
}