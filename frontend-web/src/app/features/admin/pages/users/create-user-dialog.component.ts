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

const BRANCH_ROLES = new Set(['ENCARGADO_SUCURSAL', 'CAJERO']);

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
      @if (rolesLoading) { <p role="status">Cargando roles disponibles…</p> }
      @if (rolesError) { <p role="alert">{{rolesError}} <button mat-button type="button" (click)="loadRoles()">Reintentar</button></p> }
      @if (!rolesLoading && !rolesError) {
        @if (roles.length) {
          <mat-form-field>
            <mat-label>Rol</mat-label>
            <mat-select formControlName="rol" (selectionChange)="roleChanged()">
              @for (role of roles; track role.id_rol) { <mat-option [value]="role.nombre">{{ role.nombre }}</mat-option> }
            </mat-select>
          </mat-form-field>
        } @else { <p role="alert">No hay roles empresariales activos disponibles.</p> }
      }
      @if (isStoreStaff) {
        @if (branchesLoading) { <p role="status">Cargando sucursales de esta empresa…</p> }
        @if (branchesError) { <p role="alert">{{branchesError}} <button mat-button type="button" (click)="loadBranches()">Reintentar</button></p> }
        @if (!branchesLoading && !branchesError) {
          @if (branches.length) {
            <mat-form-field>
              <mat-label>Sucursal obligatoria</mat-label>
              <mat-select formControlName="id_sucursal" required>
                @for (branch of branches; track branch.id_sucursal) { <mat-option [value]="branch.id_sucursal">{{ branch.nombre }}</mat-option> }
              </mat-select>
              @if (form.controls.id_sucursal.hasError('required')) { <mat-error>Selecciona una sucursal activa.</mat-error> }
            </mat-form-field>
          } @else { <p role="alert">Crea una sucursal activa antes de asignar este rol.</p> }
        }
      }
      <div mat-dialog-actions align="end">
        <button mat-button type="button" mat-dialog-close>Cancelar</button>
        <button mat-flat-button color="primary" [disabled]="!canSave">Guardar</button>
      </div>
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
  rolesLoading = false;
  rolesError = '';
  branchesLoading = false;
  branchesError = '';
  private branchesLoaded = false;
  form = this.fb.group({
    nombres: ['', Validators.required], apellidos: ['', Validators.required],
    correo: ['', [Validators.required, Validators.email]], password: ['', [Validators.required, Validators.minLength(8)]],
    telefono: [''], rol: ['', Validators.required], id_sucursal: [null as number | null]
  });

  ngOnInit(): void { this.loadRoles(); }

  get isStoreStaff(): boolean { return BRANCH_ROLES.has(this.form.controls.rol.value); }
  get canSave(): boolean {
    const roleValid = this.roles.some(role => role.nombre === this.form.controls.rol.value && role.estado === 'ACTIVO');
    const branchValid = !this.isStoreStaff || this.branches.some(branch =>
      branch.id_sucursal === this.form.controls.id_sucursal.value && branch.estado === 'ACTIVA');
    return this.form.valid && roleValid && branchValid && !this.rolesLoading && !this.rolesError &&
      (!this.isStoreStaff || (!this.branchesLoading && !this.branchesError));
  }

  loadRoles(): void {
    this.rolesLoading = true;
    this.rolesError = '';
    this.roleService.listAssignable().subscribe({
      next: roles => {
        this.roles = roles.filter(role => role.estado === 'ACTIVO' && role.nombre !== 'ADMINISTRADOR_PLATAFORMA');
        if (!this.roles.some(role => role.nombre === this.form.controls.rol.value)) this.form.controls.rol.setValue('');
        this.rolesLoading = false;
      },
      error: () => { this.roles = []; this.rolesError = 'No se pudieron cargar los roles.'; this.rolesLoading = false; }
    });
  }

  loadBranches(): void {
    this.branchesLoading = true;
    this.branchesError = '';
    this.branchService.list().subscribe({
      next: branches => {
        this.branches = branches.filter(branch => branch.estado === 'ACTIVA');
        this.branchesLoaded = true;
        this.branchesLoading = false;
      },
      error: () => { this.branches = []; this.branchesError = 'No se pudieron cargar las sucursales de esta empresa.'; this.branchesLoading = false; }
    });
  }

  roleChanged(): void {
    if (!this.isStoreStaff) {
      this.form.controls.id_sucursal.setValue(null);
      this.form.controls.id_sucursal.clearValidators();
    } else {
      this.form.controls.id_sucursal.setValidators(Validators.required);
      if (!this.branchesLoaded && !this.branchesLoading) this.loadBranches();
    }
    this.form.controls.id_sucursal.updateValueAndValidity();
  }

  save(): void {
    if (!this.canSave) return;
    this.ref.close(this.form.getRawValue());
  }
}
