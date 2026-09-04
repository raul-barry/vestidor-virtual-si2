import { Component, inject } from '@angular/core';
import { NonNullableFormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { InventoryAdminService } from '../../../services/inventory-admin.service';

@Component({selector:'app-inventory-form',standalone:true,imports:[ReactiveFormsModule,MatButtonModule,MatDialogModule,MatFormFieldModule,MatInputModule,MatSnackBarModule],template:`<h2 mat-dialog-title>Crear inventario inicial</h2><form [formGroup]="form" (ngSubmit)="save()" mat-dialog-content><mat-form-field><mat-label>ID variante</mat-label><input matInput type="number" formControlName="id_variante"></mat-form-field><mat-form-field><mat-label>ID sucursal</mat-label><input matInput type="number" formControlName="id_sucursal"></mat-form-field><mat-form-field><mat-label>Stock inicial</mat-label><input matInput type="number" formControlName="stock"></mat-form-field><div mat-dialog-actions align="end"><button mat-button mat-dialog-close type="button">Cancelar</button><button mat-flat-button color="primary" [disabled]="form.invalid">Guardar</button></div></form>`})
export class InventoryFormComponent { private fb=inject(NonNullableFormBuilder);private service=inject(InventoryAdminService);private snack=inject(MatSnackBar);private ref=inject(MatDialogRef<InventoryFormComponent>);form=this.fb.group({id_variante:[0,[Validators.required,Validators.min(1)]],id_sucursal:[0,[Validators.required,Validators.min(1)]],stock:[0,[Validators.required,Validators.min(0)] ]});save(){if(this.form.invalid){this.form.markAllAsTouched();return}this.service.createInventory(this.form.getRawValue()).subscribe({next:i=>this.ref.close(i),error:(e:{error?:{message?:string}})=>this.snack.open(e.error?.message??'No fue posible crear el inventario','Cerrar',{duration:5000})})} }
