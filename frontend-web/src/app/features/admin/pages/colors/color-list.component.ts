import { Component, OnInit, ViewChild, inject } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatPaginator, MatPaginatorModule } from '@angular/material/paginator';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatTableDataSource, MatTableModule } from '@angular/material/table';
import { ConfirmDialogComponent } from '../../../../shared/components/confirm-dialog/confirm-dialog.component';
import { EmptyStateComponent } from '../../../../shared/components/empty-state/empty-state.component';
import { LoadingSpinnerComponent } from '../../../../shared/components/loading-spinner/loading-spinner.component';
import { AdminColor as Color } from '../../models/color-admin.model';
import { ColorAdminService } from '../../services/color-admin.service';
import { ColorDialogComponent } from '../color-dialog/color-dialog.component';

@Component({
  selector: 'app-color-list',
  standalone: true,
  imports: [MatButtonModule, MatDialogModule, MatPaginatorModule, MatSnackBarModule, MatTableModule, LoadingSpinnerComponent, EmptyStateComponent, ConfirmDialogComponent],
  template: `<section class="page"><h1>Colores</h1><div class="toolbar"><button mat-flat-button color="primary" (click)="openForm()">Crear color</button></div>@if(loading){<app-loading-spinner/>}@else if(!dataSource.data.length){<app-empty-state message="No hay colores."/>}@else{<div class="table-scroll" role="region" aria-label="Tabla de datos" tabindex="0"><table mat-table [dataSource]="dataSource"><ng-container matColumnDef="nombre"><th mat-header-cell *matHeaderCellDef>Nombre</th><td mat-cell *matCellDef="let c">{{c.nombre}}</td></ng-container><ng-container matColumnDef="acciones"><th mat-header-cell *matHeaderCellDef>Acciones</th><td mat-cell *matCellDef="let c"><button mat-button (click)="openForm(c)">Editar</button><button mat-button color="warn" (click)="remove(c)">Eliminar</button></td></ng-container><tr mat-header-row *matHeaderRowDef="columns"></tr><tr mat-row *matRowDef="let row;columns:columns"></tr></table></div><mat-paginator [pageSize]="5" [pageSizeOptions]="[5,10,25]"/>}</section>`,
  styles: ['.page{padding:2rem}.toolbar{display:flex;justify-content:space-between;align-items:center;margin-bottom:1rem}table{width:100%}']
})
export class ColorListComponent implements OnInit {
  private service = inject(ColorAdminService);
  private dialog = inject(MatDialog);
  private snack = inject(MatSnackBar);
  @ViewChild(MatPaginator) paginator!: MatPaginator;
  dataSource = new MatTableDataSource<Color>([]);
  loading = true;
  columns = ['nombre', 'acciones'];

  ngOnInit(): void { this.load(); }

  load(): void {
    this.loading = true;
    this.service.list().subscribe({
      next: (colors) => { this.dataSource.data = colors; this.loading = false; setTimeout(() => this.dataSource.paginator = this.paginator); },
      error: () => { this.loading = false; }
    });
  }

  openForm(color?: Color): void {
    this.dialog.open(ColorDialogComponent, { data: color ?? null, width: '25rem' }).afterClosed().subscribe((result) => {
      if (result) {
        const request = color ? this.service.update(color.id_color, result) : this.service.create(result);
        request.subscribe({ next: () => this.load(), error: () => this.snack.open("No se pudo guardar", "Cerrar", { duration: 5000 }) });
      }
    });
  }

  remove(color: Color): void {
    this.dialog.open(ConfirmDialogComponent, { data: { title: 'Eliminar color', message: `Eliminar ${color.nombre}?` } }).afterClosed().subscribe((ok) => {
      if (ok) { this.service.delete(color.id_color).subscribe({ next: () => { this.load(); } }); }
    });
  }

  private updateLocal(color: Color): void {
    const index = this.dataSource.data.findIndex((item) => item.id_color === color.id_color);
    if (index >= 0) { this.dataSource.data[index] = color; } else { this.dataSource.data = [...this.dataSource.data, color]; }
  }
}