import { Component, Inject, inject } from '@angular/core';
import { NonNullableFormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';

@Component({
  selector: 'app-create-user-dialog',
  standalone: true,
  imports: [ReactiveFormsModule, MatButtonModule, MatDialogModule, MatFormFieldModule, MatInputModule, MatSelectModule],
  template: `<h2 mat-dialog-title>Crear usuario</h2>
    <form [formGroup]="form" (ngSubmit)="save()" mat-dialog-content>
      <mat-form-field><mat-label>Nombres</mat-label><input matInput formControlName="nombres"></mat-form-field>
      <mat-form-field><mat-label>Apellidos</mat-label><input matInput formControlName="apellidos"></mat-form-field>
      <mat-form-field><mat-label>Correo</mat-label><input matInput type="email" formControlName="correo"></mat-form-field>
      <mat-form-field><mat-label>Contraseña</mat-label><input matInput type="password" formControlName="password"></mat-form-field>
      <mat-form-field><mat-label>Teléfono</mat-label><input matInput formControlName="telefono"></mat-form-field>
      <mat-form-field><mat-label>Rol</mat-label><mat-select formControlName="rol">
        <mat-option value="CLIENTE">CLIENTE</mat-option><mat-option value="ENCARGADO_SUCURSAL">ENCARGADO</mat-option>
        <mat-option value="CAJERO">CAJERO</mat-option><mat-option value="ADMINISTRADOR">ADMINISTRADOR</mat-option>
      </mat-select></mat-form-field>
      <mat-form-field><mat-label>ID sucursal (personal de tienda)</mat-label><input matInput type="number" formControlName="id_sucursal"></mat-form-field>
      <div mat-dialog-actions align="end"><button mat-button type="button" mat-dialog-close>Cancelar</button><button mat-flat-button color="primary" [disabled]="form.invalid">Guardar</button></div>
    </form>`
})
export class CreateUserDialogComponent {
  private readonly fb = inject(NonNullableFormBuilder);
  private readonly ref = inject(MatDialogRef<CreateUserDialogComponent>);
  readonly form = this.fb.group({
    nombres: ['', Validators.required], apellidos: ['', Validators.required],
    correo: ['', [Validators.required, Validators.email]], password: ['', [Validators.required, Validators.minLength(8)]],
    telefono: [''], rol: ['CLIENTE', Validators.required], id_sucursal: [null as number | null]
  });
  constructor(@Inject(MAT_DIALOG_DATA) public readonly data: unknown) {}
  save(): void { if (this.form.valid) this.ref.close(this.form.getRawValue()); }
}
