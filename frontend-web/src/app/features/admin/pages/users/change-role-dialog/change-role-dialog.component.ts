import { Component, Inject, OnInit, inject } from '@angular/core';
import { NonNullableFormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';
import { AdminBranch } from '../../../models/branch-admin.model';
import { AdminRole } from '../../../models/role-admin.model';
import { UserAdmin } from '../../../models/user-admin.model';
import { BranchAdminService } from '../../../services/branch-admin.service';
import { RoleAdminService } from '../../../services/role-admin.service';

const BRANCH_ROLES = new Set(['ENCARGADO_SUCURSAL', 'CAJERO']);

@Component({
  selector: 'app-change-role-dialog',
  standalone: true,
  imports: [ReactiveFormsModule, MatButtonModule, MatDialogModule, MatFormFieldModule, MatSelectModule],
  template: `
    <h2 mat-dialog-title>Cambiar rol: {{ data.nombres }}</h2>
    <form [formGroup]="form" (ngSubmit)="save()" mat-dialog-content>
      @if (rolesLoading) { <p role="status">Cargando roles disponibles…</p> }
      @if (rolesError) { <p role="alert">{{rolesError}} <button mat-button type="button" (click)="loadRoles()">Reintentar</button></p> }
      @if (!rolesLoading && !rolesError) {
        <mat-form-field>
          <mat-label>Rol</mat-label>
          <mat-select formControlName="id_rol" (selectionChange)="roleChanged()">
            @for (role of roles; track role.id_rol) { <mat-option [value]="role.id_rol">{{ role.nombre }}</mat-option> }
          </mat-select>
        </mat-form-field>
      }
      @if (isStoreStaff) {
        @if (branchesLoading) { <p role="status">Cargando sucursales de esta empresa…</p> }
        @if (branchesError) { <p role="alert">{{branchesError}} <button mat-button type="button" (click)="loadBranches()">Reintentar</button></p> }
        @if (!branchesLoading && !branchesError) {
          @if (branches.length) {
            <mat-form-field>
              <mat-label>Sucursal obligatoria</mat-label>
              <mat-select formControlName="id_sucursal" required>
                @for (branch of branches; track branch.id_sucursal) { <mat-option [value]="branch.id_sucursal">{{branch.nombre}}</mat-option> }
              </mat-select>
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
export class ChangeRoleDialogComponent implements OnInit {
  private fb = inject(NonNullableFormBuilder);
  private ref = inject(MatDialogRef<ChangeRoleDialogComponent>);
  private roleService = inject(RoleAdminService);
  private branchService = inject(BranchAdminService);
  roles: AdminRole[] = [];
  branches: AdminBranch[] = [];
  rolesLoading = false;
  rolesError = '';
  branchesLoading = false;
  branchesError = '';
  private branchesLoaded = false;
  form = this.fb.group({ id_rol: [0, [Validators.required, Validators.min(1)]], id_sucursal: [null as number | null] });

  constructor(@Inject(MAT_DIALOG_DATA) public data: UserAdmin) {}

  ngOnInit(): void { this.loadRoles(); }

  get selectedRole(): AdminRole | undefined { return this.roles.find(role => role.id_rol === this.form.controls.id_rol.value); }
  get isStoreStaff(): boolean { return !!this.selectedRole && BRANCH_ROLES.has(this.selectedRole.nombre); }
  get canSave(): boolean {
    const roleValid = !!this.selectedRole && this.selectedRole.estado === 'ACTIVO' && this.selectedRole.nombre !== 'ADMINISTRADOR_PLATAFORMA';
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
        const current = this.roles.find(role => role.nombre === this.data.rol);
        if (current) {
          this.form.controls.id_rol.setValue(current.id_rol);
          this.form.controls.id_sucursal.setValue(this.data.id_sucursal ?? null);
        }
        if (this.isStoreStaff) {
          this.form.controls.id_sucursal.setValidators(Validators.required);
          this.form.controls.id_sucursal.updateValueAndValidity();
          this.loadBranches();
        }
        this.rolesLoading = false;
      },
      error: () => { this.roles = []; this.rolesError = 'No se pudieron cargar los roles.'; this.rolesLoading = false; }
    });
  }

  loadBranches(): void {
    this.branchesLoading = true;
    this.branchesError = '';
    this.branchService.list().subscribe({
      next: branches => { this.branches = branches.filter(branch => branch.estado === 'ACTIVA'); this.branchesLoaded = true; this.branchesLoading = false; },
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
