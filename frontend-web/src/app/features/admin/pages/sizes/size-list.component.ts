import { Component, OnInit, ViewChild, inject } from '@angular/core';
import { FormControl } from '@angular/forms';
import { ReactiveFormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatPaginator, MatPaginatorModule } from '@angular/material/paginator';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatTableDataSource, MatTableModule } from '@angular/material/table';
import { ConfirmDialogComponent } from '../../../../shared/components/confirm-dialog/confirm-dialog.component';
import { EmptyStateComponent } from '../../../../shared/components/empty-state/empty-state.component';
import { LoadingSpinnerComponent } from '../../../../shared/components/loading-spinner/loading-spinner.component';
import { AdminSize as Size } from '../../models/size-admin.model';
import { SizeAdminService } from '../../services/size-admin.service';
import { SizeDialogComponent } from '../size-dialog/size-dialog.component';
import { Observable } from 'rxjs';

@Component({
  selector: 'app-size-list',
  standalone: true,
  imports: [ReactiveFormsModule, MatButtonModule, MatDialogModule, MatFormFieldModule, MatInputModule, MatPaginatorModule, MatSnackBarModule, MatTableModule, LoadingSpinnerComponent, EmptyStateComponent, ConfirmDialogComponent],
  template: `<section class="page"><h1>Tallas</h1><div class="toolbar"><button mat-flat-button color="primary" (click)="openForm()">Crear talla</button></div>@if(loading){<app-loading-spinner/>}@else if(!dataSource.data.length){<app-empty-state message="No hay tallas."/>}@else{<table mat-table [dataSource]="dataSource"><ng-container matColumnDef="nombre"><th mat-header-cell *matHeaderCellDef>Nombre</th><td mat-cell *matCellDef="let s">{{s.nombre}}</td></ng-container><ng-container matColumnDef="acciones"><th mat-header-cell *matHeaderCellDef>Acciones</th><td mat-cell *matCellDef="let s"><button mat-button (click)="openForm(s)">Editar</button><button mat-button color="warn" (click)="remove(s)">Eliminar</button></td></ng-container><tr mat-header-row *matHeaderRowDef="columns"></tr><tr mat-row *matRowDef="let row;columns:columns"></tr></table><mat-paginator [pageSize]="5" [pageSizeOptions]="[5,10,25]"/>}</section>`,
  styles: ['.page{padding:2rem}.toolbar{display:flex;justify-content:space-between;align-items:center;margin-bottom:1rem}table{width:100%}']
})
export class SizeListComponent implements OnInit {
  private service = inject(SizeAdminService);
  private dialog = inject(MatDialog);
  private snack = inject(MatSnackBar);
  @ViewChild(MatPaginator) paginator!: MatPaginator;
  dataSource = new MatTableDataSource<Size>([]);
  loading = true;
  columns = ['nombre', 'acciones'];

  ngOnInit(): void { this.load(); }

  load(): void {
    this.loading = true;
    const listObservable$: Observable<Size[]> = this.service.list();
    listObservable$.subscribe({
      next: (sizes: Size[]) => { this.dataSource.data = sizes; this.loading = false; setTimeout(() => this.dataSource.paginator = this.paginator); },
      error: () => { this.loading = false; }
    });
  }

  openForm(size?: Size): void {
    this.dialog.open(SizeDialogComponent, { data: size ?? null, width: '25rem' }).afterClosed().subscribe((result) => {
      if (result) {
        const request = size ? this.service.update(size.id_talla, result) : this.service.create(result);
        request.subscribe({ next: () => this.load(), error: () => this.snack.open("No se pudo guardar", "Cerrar", { duration: 5000 }) });
      }
    });
  }

  remove(size: Size): void {
    this.dialog.open(ConfirmDialogComponent, { data: { title: 'Eliminar talla', message: `Eliminar ${size.nombre}?` } }).afterClosed().subscribe((ok) => {
      if (ok) { this.service.delete(size.id_talla).subscribe({ next: () => { this.load(); this.snack.open('Talla eliminada', 'Cerrar', { duration: 3000 }); } }); }
    });
  }

  private updateLocal(size: Size): void {
    const index = this.dataSource.data.findIndex((item) => item.id_talla === size.id_talla);
    if (index >= 0) { this.dataSource.data[index] = size; } else { this.dataSource.data = [...this.dataSource.data, size]; }
  }
}
