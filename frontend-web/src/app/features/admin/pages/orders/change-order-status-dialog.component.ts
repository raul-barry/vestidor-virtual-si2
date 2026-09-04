import { Component, Inject, inject } from '@angular/core';
import { NonNullableFormBuilder, ReactiveFormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';
import { OrderAdmin, OrderStatus } from '../../models/order-admin.model';
@Component({selector:'app-change-order-status-dialog',standalone:true,imports:[ReactiveFormsModule,MatButtonModule,MatDialogModule,MatFormFieldModule,MatSelectModule],template:`<h2 mat-dialog-title>Cambiar estado pedido #{{data.id_pedido}}</h2><form [formGroup]="form" (ngSubmit)="save()" mat-dialog-content><mat-form-field><mat-label>Estado</mat-label><mat-select formControlName="estado">@for(s of states;track s){<mat-option [value]="s">{{s}}</mat-option>}</mat-select></mat-form-field>@if(form.value.estado==='CANCELADO'){<p>Se solicitará confirmación antes de cancelar.</p>}<div mat-dialog-actions align="end"><button mat-button type="button" mat-dialog-close>Cancelar</button><button mat-flat-button color="primary">Guardar</button></div></form>`})
export class ChangeOrderStatusDialogComponent {private fb=inject(NonNullableFormBuilder);private ref=inject(MatDialogRef<ChangeOrderStatusDialogComponent>);states:OrderStatus[]=['PENDIENTE','CONFIRMADO','PREPARANDO','ENVIADO','ENTREGADO','CANCELADO'];form=this.fb.group({estado:['PENDIENTE' as OrderStatus]});constructor(@Inject(MAT_DIALOG_DATA) public data:OrderAdmin){this.form.patchValue({estado:data.estado})}save(){this.ref.close(this.form.controls.estado.value)} }
