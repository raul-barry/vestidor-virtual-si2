import { Component, Inject, inject } from '@angular/core';
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';
import { NonNullableFormBuilder, Validators } from '@angular/forms';
import { ReactiveFormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatDialogModule } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { AdminBranch as Branch } from '../../models/branch-admin.model';

@Component({
  selector: 'app-branch-dialog',
  standalone: true,
  imports: [ReactiveFormsModule, MatButtonModule, MatDialogModule, MatFormFieldModule, MatInputModule],
  template: `<h2 mat-dialog-title>{{data?.id_sucursal ? 'Editar' : 'Crear'} sucursal</h2><form [formGroup]="form" (ngSubmit)="save()" mat-dialog-content><mat-form-field><mat-label>Nombre</mat-label><input matInput formControlName="nombre"></mat-form-field><mat-form-field><mat-label>Dirección</mat-label><input matInput formControlName="direccion"></mat-form-field><mat-form-field><mat-label>Ciudad</mat-label><input matInput formControlName="ciudad"></mat-form-field><div mat-dialog-actions align="end"><button mat-button mat-dialog-close type="button">Cancelar</button><button mat-flat-button color="primary" [disabled]="form.invalid">Guardar</button></div></form>`
})
export class BranchDialogComponent {
  private ref = inject(MatDialogRef<BranchDialogComponent>);
  form = inject(NonNullableFormBuilder).group({ nombre: ['', [Validators.required, Validators.minLength(1)]], direccion: ['', [Validators.required, Validators.minLength(1)]], ciudad: ['Santa Cruz', Validators.required] });
  constructor(@Inject(MAT_DIALOG_DATA) public data: Branch | null) { if (data) this.form.patchValue(data); }
  save(): void { this.ref.close(this.form.getRawValue()); }
}