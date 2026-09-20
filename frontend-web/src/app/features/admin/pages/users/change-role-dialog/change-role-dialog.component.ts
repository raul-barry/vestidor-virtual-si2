import { Component, Inject, OnInit, inject } from '@angular/core';
import { NonNullableFormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';
import { AdminRole } from '../../../models/role-admin.model';
import { UserAdmin } from '../../../models/user-admin.model';
import { RoleAdminService } from '../../../services/role-admin.service';

@Component({
  selector: 'app-change-role-dialog',
  standalone: true,
  imports: [ReactiveFormsModule, MatButtonModule, MatDialogModule, MatFormFieldModule, MatSelectModule],
  template: `
    <h2 mat-dialog-title>Cambiar rol: {{ data.nombres }}</h2>
    <form [formGroup]="form" (ngSubmit)="save()" mat-dialog-content>
      <mat-form-field><mat-label>Rol</mat-label><mat-select formControlName="id_rol">@for (role of roles; track role.id_rol) { <mat-option [value]="role.id_rol">{{ role.nombre }}</mat-option> }</mat-select></mat-form-field>
      <div mat-dialog-actions align="end"><button mat-button mat-dialog-close type="button">Cancelar</button><button mat-flat-button color="primary" [disabled]="form.invalid">Guardar</button></div>
    </form>
  `
})
export class ChangeRoleDialogComponent implements OnInit {
  private fb = inject(NonNullableFormBuilder);
  private ref = inject(MatDialogRef<ChangeRoleDialogComponent>);
  private roleService = inject(RoleAdminService);
  roles: AdminRole[] = [];
  form = this.fb.group({ id_rol: [0, [Validators.required, Validators.min(1)]] });
  constructor(@Inject(MAT_DIALOG_DATA) public data: UserAdmin) {}
  ngOnInit(): void {
    this.roleService.list().subscribe(roles => {
      this.roles = roles.filter(role => role.estado === 'ACTIVO');
      const current = this.roles.find(role => role.nombre === this.data.rol);
      if (current) this.form.controls.id_rol.setValue(current.id_rol);
    });
  }
  save(): void { if (this.form.valid) this.ref.close(this.form.getRawValue()); }
}
