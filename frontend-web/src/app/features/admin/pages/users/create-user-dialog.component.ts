import { Component, OnInit, inject } from '@angular/core';
import { NonNullableFormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { AdminBranch } from '../../models/branch-admin.model';
import { AdminRole } from '../../models/role-admin.model';
import { BranchAdminService } from '../../services/branch-admin.service';
import { RoleAdminService } from '../../services/role-admin.service';

@Component({
  selector: 'app-create-user-dialog',
  standalone: true,
  imports: [ReactiveFormsModule, MatButtonModule, MatDialogModule, MatFormFieldModule, MatInputModule, MatSelectModule],
  template: `
    <h2 mat-dialog-title>Crear usuario</h2>
    <form [formGroup]="form" (ngSubmit)="save()" mat-dialog-content>
      <mat-form-field><mat-label>Nombres</mat-label><input matInput formControlName="nombres"></mat-form-field>
      <mat-form-field><mat-label>Apellidos</mat-label><input matInput formControlName="apellidos"></mat-form-field>
      <mat-form-field><mat-label>Correo</mat-label><input matInput type="email" formControlName="correo"></mat-form-field>
      <mat-form-field><mat-label>Contraseña</mat-label><input matInput type="password" formControlName="password"></mat-form-field>
      <mat-form-field><mat-label>Teléfono</mat-label><input matInput formControlName="telefono"></mat-form-field>
      <mat-form-field><mat-label>Rol</mat-label><mat-select formControlName="rol" (selectionChange)="roleChanged()">@for (role of roles; track role.id_rol) { <mat-option [value]="role.nombre">{{ role.nombre }}</mat-option> }</mat-select></mat-form-field>
      @if (isStoreStaff) {
        <mat-form-field><mat-label>Sucursal</mat-label><mat-select formControlName="id_sucursal"><mat-option [value]="null">Sin asignar</mat-option>@for (branch of branches; track branch.id_sucursal) { <mat-option [value]="branch.id_sucursal">{{ branch.nombre }}</mat-option> }</mat-select></mat-form-field>
      }
      <div mat-dialog-actions align="end"><button mat-button type="button" mat-dialog-close>Cancelar</button><button mat-flat-button color="primary" [disabled]="form.invalid">Guardar</button></div>
    </form>
  `
})
export class CreateUserDialogComponent implements OnInit {
  private fb = inject(NonNullableFormBuilder);
  private ref = inject(MatDialogRef<CreateUserDialogComponent>);
  private branchService = inject(BranchAdminService);
  private roleService = inject(RoleAdminService);
  roles: AdminRole[] = [];
  branches: AdminBranch[] = [];
  form = this.fb.group({
    nombres: ['', Validators.required], apellidos: ['', Validators.required],
    correo: ['', [Validators.required, Validators.email]], password: ['', [Validators.required, Validators.minLength(8)]],
    telefono: [''], rol: ['CLIENTE', Validators.required], id_sucursal: [null as number | null]
  });

  ngOnInit(): void {
    this.roleService.list().subscribe(roles => this.roles = roles.filter(role => role.estado === 'ACTIVO'));
    this.branchService.list().subscribe(branches => this.branches = branches.filter(branch => branch.estado === 'ACTIVA'));
  }
  get isStoreStaff(): boolean { return ['CAJERO', 'ENCARGADO_SUCURSAL'].includes(this.form.controls.rol.value); }
  roleChanged(): void { if (!this.isStoreStaff) this.form.controls.id_sucursal.setValue(null); }
  save(): void { if (this.form.valid) this.ref.close(this.form.getRawValue()); }
}
