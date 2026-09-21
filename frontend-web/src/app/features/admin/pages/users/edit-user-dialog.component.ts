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

@Component({selector:'app-edit-user-dialog',standalone:true,imports:[ReactiveFormsModule,MatButtonModule,MatDialogModule,MatFormFieldModule,MatInputModule,MatSelectModule],template:`<h2 mat-dialog-title>Editar usuario</h2><form [formGroup]="form" (ngSubmit)="save()" mat-dialog-content><mat-form-field><mat-label>Nombres</mat-label><input matInput formControlName="nombres"></mat-form-field><mat-form-field><mat-label>Apellidos</mat-label><input matInput formControlName="apellidos"></mat-form-field><mat-form-field><mat-label>Correo</mat-label><input matInput formControlName="correo"></mat-form-field><mat-form-field><mat-label>Telefono</mat-label><input matInput formControlName="telefono"></mat-form-field>@if(isStoreStaff){<mat-form-field><mat-label>Sucursal</mat-label><mat-select formControlName="id_sucursal"><mat-option [value]="null">Sin asignar</mat-option>@for(branch of branches;track branch.id_sucursal){<mat-option [value]="branch.id_sucursal">{{branch.nombre}}</mat-option>}</mat-select></mat-form-field>}<div mat-dialog-actions align="end"><button mat-button type="button" mat-dialog-close>Cancelar</button><button mat-flat-button color="primary" [disabled]="form.invalid">Guardar</button></div></form>`})
export class EditUserDialogComponent implements OnInit {
  private fb=inject(FormBuilder); private ref=inject(MatDialogRef<EditUserDialogComponent>); private branchesService=inject(BranchAdminService); branches:AdminBranch[]=[];
  form=this.fb.group({nombres:['',Validators.required],apellidos:['',Validators.required],correo:['',[Validators.required,Validators.email]],telefono:[null as string|null],id_sucursal:[null as number|null]});
  constructor(@Inject(MAT_DIALOG_DATA) public data:UserAdmin){this.form.patchValue({nombres:data.nombres,apellidos:data.apellidos,correo:data.correo,telefono:data.telefono,id_sucursal:data.id_sucursal??null})}
  get isStoreStaff(){return this.data.rol==='CAJERO'||this.data.rol==='ENCARGADO_SUCURSAL'}
  ngOnInit(){if(this.isStoreStaff)this.branchesService.list().subscribe(rows=>this.branches=rows.filter(row=>row.estado==='ACTIVA'||row.id_sucursal===this.data.id_sucursal))}
  save(){if(this.form.valid)this.ref.close(this.form.getRawValue())}
}
