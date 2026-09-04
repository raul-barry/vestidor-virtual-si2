import { Component, Inject, inject } from '@angular/core';
import { NonNullableFormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { UserAdmin } from '../../../models/user-admin.model';
@Component({selector:'app-change-role-dialog',standalone:true,imports:[ReactiveFormsModule,MatButtonModule,MatDialogModule,MatFormFieldModule,MatInputModule],template:`<h2 mat-dialog-title>Cambiar rol: {{data.nombres}}</h2><form [formGroup]="form" (ngSubmit)="save()" mat-dialog-content><p>Roles: CLIENTE, ADMINISTRADOR, CAJERO, ENCARGADO_SUCURSAL.</p><mat-form-field><mat-label>ID rol</mat-label><input matInput type="number" formControlName="id_rol"></mat-form-field><div mat-dialog-actions align="end"><button mat-button mat-dialog-close type="button">Cancelar</button><button mat-flat-button color="primary" [disabled]="form.invalid">Guardar</button></div></form>`})
export class ChangeRoleDialogComponent {
  private fb = inject(NonNullableFormBuilder);
  private ref = inject(MatDialogRef<ChangeRoleDialogComponent>);
  form = this.fb.group({ id_rol: [0, [Validators.required, Validators.min(1)]] });
  constructor(@Inject(MAT_DIALOG_DATA) public data: UserAdmin) {}
  save(): void { this.ref.close(this.form.getRawValue()); }
}
