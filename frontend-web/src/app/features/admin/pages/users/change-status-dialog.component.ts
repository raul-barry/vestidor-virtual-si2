import { Component, Inject, inject } from '@angular/core';
import { NonNullableFormBuilder, ReactiveFormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';
import { UserAdmin } from '../../models/user-admin.model';
@Component({selector:'app-change-status-dialog',standalone:true,imports:[ReactiveFormsModule,MatButtonModule,MatDialogModule,MatFormFieldModule,MatSelectModule],template:`<h2 mat-dialog-title>Cambiar estado</h2><form [formGroup]="form" (ngSubmit)="save()" mat-dialog-content><mat-form-field><mat-label>Estado</mat-label><mat-select formControlName="estado"><mat-option value="ACTIVO">ACTIVO</mat-option><mat-option value="INACTIVO">INACTIVO</mat-option></mat-select></mat-form-field><div mat-dialog-actions align="end"><button mat-button mat-dialog-close type="button">Cancelar</button><button mat-flat-button color="primary">Guardar</button></div></form>`})
export class ChangeStatusDialogComponent {private fb=inject(NonNullableFormBuilder);private ref=inject(MatDialogRef<ChangeStatusDialogComponent>);form=this.fb.group({estado:['ACTIVO' as 'ACTIVO'|'INACTIVO']});constructor(@Inject(MAT_DIALOG_DATA) data:UserAdmin){this.form.patchValue({estado:data.estado})}save(){this.ref.close(this.form.getRawValue())} }
