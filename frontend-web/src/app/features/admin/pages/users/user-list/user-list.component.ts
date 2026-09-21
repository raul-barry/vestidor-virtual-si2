import { Component, OnInit, ViewChild, inject } from '@angular/core';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatPaginator, MatPaginatorModule } from '@angular/material/paginator';
import { MatSelectModule } from '@angular/material/select';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatTableDataSource, MatTableModule } from '@angular/material/table';
import { UserAdmin } from '../../../models/user-admin.model';
import { UserAdminService } from '../../../services/user-admin.service';
import { ConfirmDialogComponent } from '../../../shared/components/confirm-dialog/confirm-dialog.component';
import { EmptyStateComponent } from '../../../shared/components/empty-state/empty-state.component';
import { ErrorMessageComponent } from '../../../shared/components/error-message/error-message.component';
import { LoadingSpinnerComponent } from '../../../shared/components/loading-spinner/loading-spinner.component';
import { ChangeRoleDialogComponent } from '../change-role-dialog/change-role-dialog.component';
import { CreateUserDialogComponent } from '../create-user-dialog.component';
import { EditUserDialogComponent } from '../edit-user-dialog.component';

@Component({
  selector:'app-user-list', standalone:true,
  imports:[ReactiveFormsModule,MatButtonModule,MatDialogModule,MatFormFieldModule,MatInputModule,MatPaginatorModule,MatSelectModule,MatSnackBarModule,MatTableModule,LoadingSpinnerComponent,EmptyStateComponent,ErrorMessageComponent],
  template:`<section class="page"><div class="header"><h1>Usuarios</h1><button mat-flat-button color="primary" (click)="create()">Crear usuario</button></div><div class="filters"><mat-form-field><mat-label>Buscar</mat-label><input matInput [formControl]="search" (input)="apply()"></mat-form-field><mat-form-field><mat-label>Rol</mat-label><mat-select [formControl]="role" (selectionChange)="apply()"><mat-option value="">Todos</mat-option>@for(item of roles;track item){<mat-option [value]="item">{{item}}</mat-option>}</mat-select></mat-form-field><mat-form-field><mat-label>Estado</mat-label><mat-select [formControl]="status" (selectionChange)="apply()"><mat-option value="">Todos</mat-option><mat-option value="ACTIVO">ACTIVO</mat-option><mat-option value="INACTIVO">INACTIVO</mat-option><mat-option value="BLOQUEADO">BLOQUEADO</mat-option></mat-select></mat-form-field></div>@if(loading){<app-loading-spinner/>}@else if(error){<app-error-message/>}@else if(!source.data.length){<app-empty-state message="No hay usuarios."/>}@else{<div class="table-scroll"><table mat-table [dataSource]="source"><ng-container matColumnDef="nombre"><th mat-header-cell *matHeaderCellDef>Nombre</th><td mat-cell *matCellDef="let u">{{u.nombres}} {{u.apellidos}}</td></ng-container><ng-container matColumnDef="correo"><th mat-header-cell *matHeaderCellDef>Correo</th><td mat-cell *matCellDef="let u">{{u.correo}}</td></ng-container><ng-container matColumnDef="rol"><th mat-header-cell *matHeaderCellDef>Rol</th><td mat-cell *matCellDef="let u">{{u.rol}}</td></ng-container><ng-container matColumnDef="estado"><th mat-header-cell *matHeaderCellDef>Estado</th><td mat-cell *matCellDef="let u"><span class="status" [class.inactive]="u.estado!=='ACTIVO'">{{u.estado}}</span></td></ng-container><ng-container matColumnDef="acciones"><th mat-header-cell *matHeaderCellDef>Acciones</th><td mat-cell *matCellDef="let u"><button mat-button (click)="detail(u)">Consultar</button><button mat-button (click)="edit(u)">Editar</button><button mat-button (click)="roleDialog(u)">Cambiar rol</button><button mat-button [color]="u.estado==='ACTIVO'?'warn':'primary'" (click)="toggleStatus(u)">{{u.estado==='ACTIVO'?'Desactivar':'Restaurar'}}</button></td></ng-container><tr mat-header-row *matHeaderRowDef="cols"></tr><tr mat-row *matRowDef="let row;columns:cols"></tr></table></div><mat-paginator [pageSize]="5"/>}</section>`,
  styles:['.page{padding:2rem}.header,.filters{display:flex;align-items:center;justify-content:space-between;gap:1rem;flex-wrap:wrap}.filters{justify-content:flex-start}table{width:100%}.status{font-weight:700;color:var(--primary)}.status.inactive{color:var(--danger)}']
})
export class UserListComponent implements OnInit {
  private service=inject(UserAdminService); private dialog=inject(MatDialog); private router=inject(Router); private snack=inject(MatSnackBar);
  @ViewChild(MatPaginator) paginator!:MatPaginator;
  source=new MatTableDataSource<UserAdmin>([]); search=new FormControl(''); role=new FormControl(''); status=new FormControl(''); loading=true; error=false;
  roles=['CLIENTE','ADMINISTRADOR','CAJERO','ENCARGADO_SUCURSAL']; cols=['nombre','correo','rol','estado','acciones'];
  ngOnInit(){this.load()}
  load(){this.loading=true;this.error=false;this.service.getUsers().subscribe({next:users=>{this.source.data=users;this.source.filterPredicate=(u,f)=>{const c=JSON.parse(f);return `${u.nombres} ${u.apellidos} ${u.correo}`.toLowerCase().includes(c.search)&&(!c.role||u.rol===c.role)&&(!c.status||u.estado===c.status)};this.apply();this.loading=false;setTimeout(()=>this.source.paginator=this.paginator)},error:()=>{this.error=true;this.loading=false}})}
  create(){this.dialog.open(CreateUserDialogComponent,{width:'32rem'}).afterClosed().subscribe(data=>{if(data)this.service.createUser(data).subscribe({next:()=>{this.load();this.notice('Usuario creado')},error:e=>this.fail(e,'No fue posible crear el usuario')})})}
  edit(user:UserAdmin){this.dialog.open(EditUserDialogComponent,{data:user,width:'32rem'}).afterClosed().subscribe(data=>{if(data)this.service.updateUser(user.id_usuario,data).subscribe({next:()=>{this.load();this.notice('Usuario actualizado')},error:e=>this.fail(e,'No fue posible editar el usuario')})})}
  toggleStatus(user:UserAdmin){const estado=user.estado==='ACTIVO'?'INACTIVO':'ACTIVO';const action=()=>this.service.updateStatus(user.id_usuario,{estado}).subscribe({next:()=>{this.load();this.notice(estado==='ACTIVO'?'Usuario restaurado':'Usuario desactivado')},error:e=>this.fail(e,'No fue posible cambiar el estado')});if(estado==='INACTIVO')this.dialog.open(ConfirmDialogComponent,{data:{title:'Desactivar usuario',message:`¿Desactivar ${user.correo}?`}}).afterClosed().subscribe(ok=>{if(ok)action()});else action()}
  roleDialog(user:UserAdmin){this.dialog.open(ChangeRoleDialogComponent,{data:user}).afterClosed().subscribe(data=>{if(data)this.service.updateRole(user.id_usuario,data).subscribe({next:()=>{this.load();this.notice('Rol actualizado')},error:e=>this.fail(e,'No fue posible cambiar el rol')})})}
  detail(user:UserAdmin){void this.router.navigate(['/admin/users/detail',user.id_usuario])}
  apply(){this.source.filter=JSON.stringify({search:(this.search.value??'').toLowerCase(),role:this.role.value??'',status:this.status.value??''})}
  private notice(message:string){this.snack.open(message,'Cerrar',{duration:3000})}
  private fail(error:{error?:{message?:string}},fallback:string){this.snack.open(error.error?.message??fallback,'Cerrar',{duration:5000})}
}
