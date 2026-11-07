import { Component, Inject, OnInit, inject } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { AdminBranch } from '../../models/branch-admin.model';
import { UserAdmin } from '../../models/user-admin.model';
import { BranchAdminService } from '../../services/branch-admin.service';

const BRANCH_ROLES = new Set(['CAJERO', 'ENCARGADO_SUCURSAL']);

@Component({
  selector: 'app-edit-user-dialog', standalone: true,
  imports: [ReactiveFormsModule, MatButtonModule, MatDialogModule, MatFormFieldModule, MatInputModule, MatSelectModule],
  template: `
    <h2 mat-dialog-title>Editar usuario</h2>
    <form [formGroup]="form" (ngSubmit)="save()" mat-dialog-content>
      <mat-form-field><mat-label>Nombres</mat-label><input matInput formControlName="nombres"></mat-form-field>
      <mat-form-field><mat-label>Apellidos</mat-label><input matInput formControlName="apellidos"></mat-form-field>
      <mat-form-field><mat-label>Correo</mat-label><input matInput formControlName="correo"></mat-form-field>
      <mat-form-field><mat-label>Teléfono</mat-label><input matInput formControlName="telefono"></mat-form-field>
      @if (isStoreStaff) {
        @if (branchesLoading) { <p role="status">Cargando sucursales de esta empresa…</p> }
        @if (branchesError) { <p role="alert">{{branchesError}} <button mat-button type="button" (click)="loadBranches()">Reintentar</button></p> }
        @if (!branchesLoading && !branchesError) {
          @if (branches.length) {
            <mat-form-field><mat-label>Sucursal obligatoria</mat-label>
              <mat-select formControlName="id_sucursal" required>
                @for (branch of branches; track branch.id_sucursal) { <mat-option [value]="branch.id_sucursal">{{branch.nombre}}</mat-option> }
              </mat-select>
            </mat-form-field>
          } @else { <p role="alert">Crea una sucursal activa antes de editar este usuario.</p> }
        }
      }
      <div mat-dialog-actions align="end"><button mat-button type="button" mat-dialog-close>Cancelar</button><button mat-flat-button color="primary" [disabled]="!canSave">Guardar</button></div>
    </form>
  `
})
export class EditUserDialogComponent implements OnInit {
  private fb = inject(FormBuilder);
  private ref = inject(MatDialogRef<EditUserDialogComponent>);
  private branchesService = inject(BranchAdminService);
  branches: AdminBranch[] = [];
  branchesLoading = false;
  branchesError = '';
  form = this.fb.group({
    nombres: ['', Validators.required], apellidos: ['', Validators.required],
    correo: ['', [Validators.required, Validators.email]], telefono: [null as string | null],
    id_sucursal: [null as number | null]
  });

  constructor(@Inject(MAT_DIALOG_DATA) public data: UserAdmin) {
    this.form.patchValue({ nombres: data.nombres, apellidos: data.apellidos, correo: data.correo,
      telefono: data.telefono, id_sucursal: data.id_sucursal ?? null });
    if (this.isStoreStaff) this.form.controls.id_sucursal.setValidators(Validators.required);
  }

  get isStoreStaff(): boolean { return BRANCH_ROLES.has(this.data.rol); }
  get canSave(): boolean {
    const branchValid = !this.isStoreStaff || this.branches.some(branch =>
      branch.id_sucursal === this.form.controls.id_sucursal.value && branch.estado === 'ACTIVA');
    return this.form.valid && branchValid && (!this.isStoreStaff || (!this.branchesLoading && !this.branchesError));
  }

  ngOnInit(): void { if (this.isStoreStaff) this.loadBranches(); }

  loadBranches(): void {
    this.branchesLoading = true;
    this.branchesError = '';
    this.branchesService.list().subscribe({
      next: rows => { this.branches = rows.filter(row => row.estado === 'ACTIVA'); this.branchesLoading = false; },
      error: () => { this.branches = []; this.branchesError = 'No se pudieron cargar las sucursales de esta empresa.'; this.branchesLoading = false; }
    });
  }

  save(): void { if (this.canSave) this.ref.close(this.form.getRawValue()); }
}
