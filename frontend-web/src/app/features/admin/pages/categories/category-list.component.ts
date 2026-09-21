import { Component, OnInit, ViewChild, inject } from '@angular/core';
import { FormControl } from '@angular/forms';
import { ReactiveFormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatPaginator, MatPaginatorModule } from '@angular/material/paginator';
import { MatSelectModule } from '@angular/material/select';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatTableDataSource, MatTableModule } from '@angular/material/table';
import { ConfirmDialogComponent } from '../../../../shared/components/confirm-dialog/confirm-dialog.component';
import { EmptyStateComponent } from '../../../../shared/components/empty-state/empty-state.component';
import { ErrorMessageComponent } from '../../../../shared/components/error-message/error-message.component';
import { LoadingSpinnerComponent } from '../../../../shared/components/loading-spinner/loading-spinner.component';
import { AdminCategory as Category } from '../../models/category-admin.model';
import { CategoryAdminService } from '../../services/category-admin.service';
import { CategoryDialogComponent } from '../category-dialog/category-dialog.component';

@Component({
  selector: 'app-category-list',
  standalone: true,
  imports: [ReactiveFormsModule, MatButtonModule, MatDialogModule, MatFormFieldModule, MatInputModule, MatPaginatorModule, MatSelectModule, MatSnackBarModule, MatTableModule, LoadingSpinnerComponent, EmptyStateComponent, ErrorMessageComponent],
  template: `<section class="page"><h1>Categorías</h1><div class="toolbar"><mat-form-field><mat-label>Buscar</mat-label><input matInput [formControl]="search" (input)="applyFilters()"></mat-form-field><button mat-flat-button color="primary" (click)="openForm()">Crear categoría</button></div>@if(loading){<app-loading-spinner/>}@else if(error){<app-error-message/>}@else if(!dataSource.data.length){<app-empty-state message="No hay categorías."/>}@else{<div class="table-scroll" role="region" aria-label="Tabla de datos" tabindex="0"><table mat-table [dataSource]="dataSource"><ng-container matColumnDef="nombre"><th mat-header-cell *matHeaderCellDef>Nombre</th><td mat-cell *matCellDef="let c">{{c.nombre}}</td></ng-container><ng-container matColumnDef="descripcion"><th mat-header-cell *matHeaderCellDef>Descripción</th><td mat-cell *matCellDef="let c">{{c.descripcion||'-'}}</td></ng-container><ng-container matColumnDef="estado"><th mat-header-cell *matHeaderCellDef>Estado</th><td mat-cell *matCellDef="let c">{{c.estado}}</td></ng-container><ng-container matColumnDef="acciones"><th mat-header-cell *matHeaderCellDef>Acciones</th><td mat-cell *matCellDef="let c"><button mat-button (click)="openForm(c)">Editar</button><button mat-button color="warn" (click)="remove(c)">Eliminar</button></td></ng-container><tr mat-header-row *matHeaderRowDef="columns"></tr><tr mat-row *matRowDef="let row;columns:columns"></tr></table></div><mat-paginator [pageSize]="5" [pageSizeOptions]="[5,10,25]"/>}</section>`,
  styles: ['.page{padding:2rem}.toolbar{display:flex;gap:1rem;justify-content:space-between;align-items:center;margin-bottom:1rem}table{width:100%}']
})
export class CategoryListComponent implements OnInit {
  private service = inject(CategoryAdminService);
  private dialog = inject(MatDialog);
  private snack = inject(MatSnackBar);
  @ViewChild(MatPaginator) paginator!: MatPaginator;
  dataSource = new MatTableDataSource<Category>([]);
  search = new FormControl('');
  loading = true;
  error = false;
  columns = ['nombre', 'descripcion', 'estado', 'acciones'];

  ngOnInit(): void { this.load(); }

  load(): void {
    this.loading = true;
    this.service.list().subscribe({
      next: (categories) => { this.dataSource.data = categories; this.loading = false; setTimeout(() => this.dataSource.paginator = this.paginator); },
      error: () => { this.error = true; this.loading = false; }
    });
  }

  applyFilters(): void { this.dataSource.filter = (this.search.value ?? '').toLowerCase(); }

  openForm(category?: Category): void {
    this.dialog.open(CategoryDialogComponent, { data: category ?? null, width: '30rem' }).afterClosed().subscribe((result) => {
      if (result) {
        const request = category ? this.service.update(category.id_categoria, result) : this.service.create(result);
        request.subscribe({ next: () => this.load(), error: () => this.snack.open("No se pudo guardar", "Cerrar", { duration: 5000 }) });
      }
    });
  }

  remove(category: Category): void {
    this.dialog.open(ConfirmDialogComponent, { data: { title: 'Eliminar categoría', message: `Eliminar ${category.nombre}?` } }).afterClosed().subscribe((ok) => {
      if (ok) { this.service.delete(category.id_categoria).subscribe({ next: () => { this.load(); this.snack.open('Categoría eliminada', 'Cerrar', { duration: 3000 }); }, error: () => this.snack.open('No fue posible eliminar', 'Cerrar', { duration: 5000 }) }); }
    });
  }

  private updateLocal(category: Category): void {
    const index = this.dataSource.data.findIndex((item) => item.id_categoria === category.id_categoria);
    if (index >= 0) { this.dataSource.data[index] = category; } else { this.dataSource.data = [...this.dataSource.data, category]; }
    this.applyFilters();
  }
}