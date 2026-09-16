import { Component, OnInit, ViewChild, inject } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatPaginator, MatPaginatorModule } from '@angular/material/paginator';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatTableDataSource, MatTableModule } from '@angular/material/table';
import { ConfirmDialogComponent } from '../../../../shared/components/confirm-dialog/confirm-dialog.component';
import { EmptyStateComponent } from '../../../../shared/components/empty-state/empty-state.component';
import { LoadingSpinnerComponent } from '../../../../shared/components/loading-spinner/loading-spinner.component';
import { AdminBranch as Branch } from '../../models/branch-admin.model';
import { BranchAdminService } from '../../services/branch-admin.service';
import { BranchDialogComponent } from '../branch-dialog/branch-dialog.component';

@Component({
  selector: 'app-branch-list',
  standalone: true,
  imports: [MatButtonModule, MatDialogModule, MatPaginatorModule, MatSnackBarModule, MatTableModule, LoadingSpinnerComponent, EmptyStateComponent, ConfirmDialogComponent],
  template: `<section class="page"><h1>Sucursales</h1><div class="toolbar"><button mat-flat-button color="primary" (click)="openForm()">Crear sucursal</button></div>@if(loading){<app-loading-spinner/>}@else if(!dataSource.data.length){<app-empty-state message="No hay sucursales."/>}@else{<table mat-table [dataSource]="dataSource"><ng-container matColumnDef="nombre"><th mat-header-cell *matHeaderCellDef>Nombre</th><td mat-cell *matCellDef="let b">{{b.nombre}}</td></ng-container><ng-container matColumnDef="direccion"><th mat-header-cell *matHeaderCellDef>Dirección</th><td mat-cell *matCellDef="let b">{{b.direccion}}</td></ng-container><ng-container matColumnDef="ciudad"><th mat-header-cell *matHeaderCellDef>Ciudad</th><td mat-cell *matCellDef="let b">{{b.ciudad}}</td></ng-container><ng-container matColumnDef="estado"><th mat-header-cell *matHeaderCellDef>Estado</th><td mat-cell *matCellDef="let b">{{b.estado}}</td></ng-container><ng-container matColumnDef="acciones"><th mat-header-cell *matHeaderCellDef>Acciones</th><td mat-cell *matCellDef="let b"><button mat-button (click)="openForm(b)">Editar</button><button mat-button (click)="toggle(b)">{{b.estado==='ACTIVA'?'Desactivar':'Activar'}}</button><button mat-button color="warn" (click)="remove(b)">Eliminar</button></td></ng-container><tr mat-header-row *matHeaderRowDef="columns"></tr><tr mat-row *matRowDef="let row;columns:columns"></tr></table><mat-paginator [pageSize]="5" [pageSizeOptions]="[5,10,25]"/>}</section>`,
  styles: ['.page{padding:2rem}.toolbar{display:flex;justify-content:space-between;align-items:center;margin-bottom:1rem}table{width:100%}']
})
export class BranchListComponent implements OnInit {
  private service = inject(BranchAdminService);
  private dialog = inject(MatDialog);
  private snack = inject(MatSnackBar);
  @ViewChild(MatPaginator) paginator!: MatPaginator;
  dataSource = new MatTableDataSource<Branch>([]);
  loading = true;
  columns = ['nombre', 'direccion', 'ciudad', 'estado', 'acciones'];

  ngOnInit(): void { this.load(); }

  load(): void {
    this.loading = true;
    this.service.list().subscribe({
      next: (branches) => { this.dataSource.data = branches; this.loading = false; setTimeout(() => this.dataSource.paginator = this.paginator); },
      error: () => { this.loading = false; }
    });
  }

  openForm(branch?: Branch): void {
    this.dialog.open(BranchDialogComponent, { data: branch ?? null, width: '30rem' }).afterClosed().subscribe((result) => {
      if (result) {
        const request = branch ? this.service.update(branch.id_sucursal, result) : this.service.create(result);
        request.subscribe({ next: () => this.load(), error: () => this.snack.open("No se pudo guardar", "Cerrar", { duration: 5000 }) });
      }
    });
  }

  remove(branch: Branch): void {
    this.dialog.open(ConfirmDialogComponent, { data: { title: 'Eliminar sucursal', message: `Eliminar ${branch.nombre}?` } }).afterClosed().subscribe((ok) => {
      if (ok) { this.service.delete(branch.id_sucursal).subscribe({ next: () => { this.load(); } }); }
    });
  }

  toggle(branch: Branch): void {
    this.service.toggleStatus(branch.id_sucursal).subscribe({
      next: (updated) => { this.dataSource.data = this.dataSource.data.map((item) => item.id_sucursal === updated.id_sucursal ? updated : item); },
      error: () => this.snack.open('No se pudo cambiar el estado', 'Cerrar', { duration: 5000 })
    });
  }

  private updateLocal(branch: Branch): void {
    const index = this.dataSource.data.findIndex((item) => item.id_sucursal === branch.id_sucursal);
    if (index >= 0) { this.dataSource.data[index] = branch; } else { this.dataSource.data = [...this.dataSource.data, branch]; }
  }
}