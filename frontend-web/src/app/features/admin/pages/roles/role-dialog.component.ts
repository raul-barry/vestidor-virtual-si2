import { Component, Inject, inject } from '@angular/core';
import { FormControl, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { AdminPermission, AdminRole } from '../../models/role-admin.model';

@Component({
  selector: 'app-role-dialog',
  standalone: true,
  imports: [ReactiveFormsModule, MatButtonModule, MatCheckboxModule, MatDialogModule, MatFormFieldModule, MatInputModule],
  template: `
    <h2 mat-dialog-title>{{ data.role ? 'Editar rol' : 'Nuevo rol' }}</h2>
    <form [formGroup]="form" (ngSubmit)="save()" mat-dialog-content>
      <mat-form-field>
        <mat-label>Nombre</mat-label>
        <input matInput formControlName="nombre" [readonly]="data.role?.protegido">
        @if (data.role?.protegido) { <mat-hint>El nombre del rol base está protegido.</mat-hint> }
      </mat-form-field>
      <mat-form-field><mat-label>Descripción</mat-label><textarea matInput formControlName="descripcion"></textarea></mat-form-field>
      <fieldset>
        <legend>Permisos</legend>
        @for (permission of data.permissions; track permission.id_permiso) {
          <mat-checkbox [checked]="selected.has(permission.id_permiso)" (change)="toggle(permission.id_permiso, $event.checked)">{{ permission.codigo }} — {{ permission.descripcion }}</mat-checkbox>
        }
      </fieldset>
      <div mat-dialog-actions align="end"><button mat-button type="button" mat-dialog-close>Cancelar</button><button mat-flat-button color="primary" [disabled]="form.invalid">Guardar</button></div>
    </form>
  `,
  styles: ['form{display:grid;gap:12px}fieldset{display:grid;border:1px solid var(--border);border-radius:8px;padding:12px}']
})
export class RoleDialogComponent {
  private ref = inject(MatDialogRef<RoleDialogComponent>);
  selected = new Set<number>(this.data.role?.permisos.map(permission => permission.id_permiso) ?? []);
  form = new FormGroup({
    nombre: new FormControl(this.data.role?.nombre ?? '', { nonNullable: true, validators: [Validators.required, Validators.minLength(2)] }),
    descripcion: new FormControl<string | null>(this.data.role?.descripcion ?? null)
  });

  constructor(@Inject(MAT_DIALOG_DATA) public data: { role: AdminRole | null; permissions: AdminPermission[] }) {}
  toggle(id: number, checked: boolean): void { checked ? this.selected.add(id) : this.selected.delete(id); }
  save(): void { if (this.form.valid) this.ref.close({ ...this.form.getRawValue(), permisos: [...this.selected] }); }
}
