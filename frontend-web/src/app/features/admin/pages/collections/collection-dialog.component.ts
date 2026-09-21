import { Component, Inject, inject } from '@angular/core';
import { NonNullableFormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { Collection, CollectionRequest, LogicalState } from '../../models/commercial-master.model';

@Component({
  standalone: true,
  imports: [ReactiveFormsModule, MatDialogModule, MatButtonModule, MatFormFieldModule, MatInputModule, MatSelectModule],
  template: `
    <h2 mat-dialog-title>{{ data ? 'Editar colección' : 'Nueva colección' }}</h2>
    <mat-dialog-content>
      <form id="collection-form" [formGroup]="form" (ngSubmit)="submit()" class="grid">
        <mat-form-field class="wide"><mat-label>Nombre</mat-label><input matInput formControlName="nombre"><mat-error>Campo requerido</mat-error></mat-form-field>
        <mat-form-field class="wide"><mat-label>Descripción</mat-label><textarea matInput formControlName="descripcion"></textarea></mat-form-field>
        <mat-form-field><mat-label>Temporada</mat-label><input matInput formControlName="temporada" placeholder="Ej. Primavera / Verano"></mat-form-field>
        <mat-form-field><mat-label>Año</mat-label><input matInput type="number" min="1900" max="2200" formControlName="anio"></mat-form-field>
        <mat-form-field><mat-label>Fecha de inicio</mat-label><input matInput type="date" formControlName="fecha_inicio"></mat-form-field>
        <mat-form-field><mat-label>Fecha de fin</mat-label><input matInput type="date" formControlName="fecha_fin"></mat-form-field>
        <mat-form-field><mat-label>Estado</mat-label><mat-select formControlName="estado"><mat-option value="ACTIVO">Activo</mat-option><mat-option value="INACTIVO">Inactivo</mat-option></mat-select></mat-form-field>
      </form>
    </mat-dialog-content>
    <mat-dialog-actions align="end"><button mat-button mat-dialog-close>Cancelar</button><button mat-flat-button color="primary" form="collection-form" [disabled]="form.invalid">Guardar</button></mat-dialog-actions>
  `,
  styles: ['.grid{display:grid;grid-template-columns:1fr 1fr;gap:.5rem;min-width:min(42rem,75vw)}.wide{grid-column:1/-1}@media(max-width:650px){.grid{grid-template-columns:1fr;min-width:0}.wide{grid-column:auto}}']
})
export class CollectionDialogComponent {
  private fb = inject(NonNullableFormBuilder);
  form = this.fb.group({
    nombre: [this.data?.nombre ?? '', [Validators.required, Validators.maxLength(150)]],
    descripcion: [this.data?.descripcion ?? '', Validators.maxLength(255)],
    temporada: [this.data?.temporada ?? '', Validators.maxLength(80)],
    anio: [this.data?.anio ?? null as number | null, [Validators.min(1900), Validators.max(2200)]],
    fecha_inicio: [this.data?.fecha_inicio ?? ''],
    fecha_fin: [this.data?.fecha_fin ?? ''],
    estado: this.fb.control<LogicalState>(this.data?.estado ?? 'ACTIVO')
  });

  constructor(@Inject(MAT_DIALOG_DATA) public data: Collection | null, private ref: MatDialogRef<CollectionDialogComponent>) {}

  submit(): void {
    if (this.form.invalid) { this.form.markAllAsTouched(); return; }
    const value = this.form.getRawValue();
    if (value.fecha_inicio && value.fecha_fin && value.fecha_fin < value.fecha_inicio) {
      this.form.controls.fecha_fin.setErrors({ range: true });
      return;
    }
    this.ref.close({ ...value, anio: value.anio || null, fecha_inicio: value.fecha_inicio || null, fecha_fin: value.fecha_fin || null } as CollectionRequest);
  }
}
