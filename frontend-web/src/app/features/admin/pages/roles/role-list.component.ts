import { Component, OnInit, inject } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatTableModule } from '@angular/material/table';
import { forkJoin } from 'rxjs';
import { AdminPermission, AdminRole, RoleRequest } from '../../models/role-admin.model';
import { RoleAdminService } from '../../services/role-admin.service';
import { RoleDialogComponent } from './role-dialog.component';

@Component({
  selector: 'app-role-list',
  standalone: true,
  imports: [MatButtonModule, MatDialogModule, MatSnackBarModule, MatTableModule],
  template: `
    <section class="page">
      <div class="header"><h1>Roles y permisos</h1><button mat-flat-button color="primary" (click)="open()">Nuevo rol</button></div>
      @if (loading) { <p role="status">Cargando roles y permisos…</p> }
      @else if (error) { <p role="alert">{{error}} <button mat-button (click)="load()">Reintentar</button></p> }
      @else if (!roles.length) { <p>No hay roles disponibles.</p> }
      @else {
        <table mat-table [dataSource]="roles">
          <ng-container matColumnDef="nombre"><th mat-header-cell *matHeaderCellDef>Nombre</th><td mat-cell *matCellDef="let role">{{role.nombre}} @if(role.protegido){<small>BASE</small>}</td></ng-container>
          <ng-container matColumnDef="descripcion"><th mat-header-cell *matHeaderCellDef>Descripción</th><td mat-cell *matCellDef="let role">{{role.descripcion || '—'}}</td></ng-container>
          <ng-container matColumnDef="permisos"><th mat-header-cell *matHeaderCellDef>Permisos</th><td mat-cell *matCellDef="let role">{{permissionNames(role)}}</td></ng-container>
          <ng-container matColumnDef="estado"><th mat-header-cell *matHeaderCellDef>Estado</th><td mat-cell *matCellDef="let role">{{role.estado}}</td></ng-container>
          <ng-container matColumnDef="acciones"><th mat-header-cell *matHeaderCellDef>Acciones</th><td mat-cell *matCellDef="let role"><button mat-button (click)="open(role)">Editar</button><button mat-button [disabled]="role.protegido" (click)="toggle(role)">{{role.estado === 'ACTIVO' ? 'Desactivar' : 'Restaurar'}}</button></td></ng-container>
          <tr mat-header-row *matHeaderRowDef="columns"></tr><tr mat-row *matRowDef="let row; columns: columns"></tr>
        </table>
      }
    </section>
  `,
  styles: ['.page{padding:2rem}.header{display:flex;justify-content:space-between;align-items:center}table{width:100%}small{padding:3px 6px;background:var(--primary-soft);border-radius:8px}']
})
export class RoleListComponent implements OnInit {
  private service = inject(RoleAdminService);
  private dialog = inject(MatDialog);
  private snack = inject(MatSnackBar);
  roles: AdminRole[] = [];
  permissions: AdminPermission[] = [];
  columns = ['nombre', 'descripcion', 'permisos', 'estado', 'acciones'];
  loading = false;
  error = '';

  ngOnInit(): void { this.load(); }

  load(): void {
    this.loading = true;
    this.error = '';
    forkJoin({ roles: this.service.list(), permissions: this.service.permissions() }).subscribe({
      next: result => { this.roles = result.roles; this.permissions = result.permissions; this.loading = false; },
      error: () => { this.error = 'No fue posible cargar roles y permisos de plataforma.'; this.loading = false; }
    });
  }

  open(role: AdminRole | null = null): void {
    this.dialog.open(RoleDialogComponent, { data: { role, permissions: this.permissions }, width: '38rem' })
      .afterClosed().subscribe((data: RoleRequest | undefined) => {
        if (!data) return;
        const operation = role ? this.service.update(role.id_rol, data) : this.service.create(data);
        operation.subscribe({
          next: () => { this.load(); this.snack.open('Rol guardado', 'Cerrar', { duration: 3000 }); },
          error: error => this.snack.open(error.error?.detail ?? 'No fue posible guardar el rol', 'Cerrar', { duration: 5000 })
        });
      });
  }

  toggle(role: AdminRole): void {
    this.service.toggle(role.id_rol).subscribe({
      next: () => this.load(),
      error: error => this.snack.open(error.error?.detail ?? 'No fue posible cambiar el estado', 'Cerrar', { duration: 5000 })
    });
  }

  permissionNames(role: AdminRole): string { return role.permisos.map(permission => permission.codigo).join(', ') || 'Sin permisos'; }
}
