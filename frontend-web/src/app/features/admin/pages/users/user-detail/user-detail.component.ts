import { Component, OnInit, inject } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { MatCardModule } from '@angular/material/card';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { UserAdmin } from '../../../models/user-admin.model';
import { UserAdminService } from '../../../services/user-admin.service';
import { ErrorMessageComponent } from '../../../shared/components/error-message/error-message.component';
import { LoadingSpinnerComponent } from '../../../shared/components/loading-spinner/loading-spinner.component';
@Component({selector:'app-user-detail',standalone:true,imports:[MatCardModule,MatSnackBarModule,LoadingSpinnerComponent,ErrorMessageComponent],template:`<section class="page">@if(loading){<app-loading-spinner/>}@else if(error){<app-error-message message="Usuario no encontrado."/>}@else if(user){<h1>{{user.nombres}} {{user.apellidos}}</h1><mat-card><mat-card-content><p>Correo: {{user.correo}}</p><p>Teléfono: {{user.telefono || 'No registrado'}}</p><p>Rol: {{user.rol}}</p><p>Estado: {{user.estado}}</p></mat-card-content></mat-card>}</section>`,styles:['.page{padding:2rem}']})
export class UserDetailComponent implements OnInit {private route=inject(ActivatedRoute);private service=inject(UserAdminService);private snack=inject(MatSnackBar);user:UserAdmin|null=null;loading=true;error=false;ngOnInit(){const id=Number(this.route.snapshot.paramMap.get('id'));this.service.getUserDetail(id).subscribe({next:u=>{this.user=u;this.loading=false},error:()=>{this.error=true;this.loading=false;this.snack.open('No fue posible cargar el usuario','Cerrar',{duration:5000})}})} }
