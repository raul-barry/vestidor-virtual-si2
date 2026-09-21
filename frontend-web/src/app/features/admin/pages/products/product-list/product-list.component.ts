import { Component, OnInit, ViewChild, inject } from '@angular/core';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatPaginator, MatPaginatorModule } from '@angular/material/paginator';
import { MatSelectModule } from '@angular/material/select';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatTableDataSource, MatTableModule } from '@angular/material/table';
import { AdminProduct } from '../../../models/product-admin.model';
import { ProductAdminService } from '../../../services/product-admin.service';
import { ConfirmDialogComponent } from '../../../shared/components/confirm-dialog/confirm-dialog.component';
import { EmptyStateComponent } from '../../../shared/components/empty-state/empty-state.component';
import { ErrorMessageComponent } from '../../../shared/components/error-message/error-message.component';
import { LoadingSpinnerComponent } from '../../../shared/components/loading-spinner/loading-spinner.component';
import { ProductFormComponent } from '../product-form/product-form.component';

@Component({
  selector: 'app-product-list', standalone: true,
  imports: [ReactiveFormsModule, MatButtonModule, MatDialogModule, MatFormFieldModule, MatInputModule, MatPaginatorModule, MatSelectModule, MatSnackBarModule, MatTableModule, LoadingSpinnerComponent, EmptyStateComponent, ErrorMessageComponent],
  template: `<section class="page">
    <div class="toolbar"><h1>Productos</h1><button mat-flat-button color="primary" (click)="openForm()">Crear producto</button></div>
    <div class="filters"><mat-form-field><mat-label>Buscar</mat-label><input matInput [formControl]="search" (input)="applyFilters()"></mat-form-field><mat-form-field><mat-label>Estado</mat-label><mat-select [formControl]="status" (selectionChange)="applyFilters()"><mat-option value="">Todos</mat-option><mat-option value="ACTIVO">ACTIVO</mat-option><mat-option value="INACTIVO">INACTIVO</mat-option></mat-select></mat-form-field></div>
    @if (loading) { <app-loading-spinner /> } @else if (error) { <app-error-message /> } @else if (!dataSource.data.length) { <app-empty-state message="No hay productos." /> } @else {
      <div class="table-scroll" role="region" aria-label="Tabla de datos" tabindex="0"><table mat-table [dataSource]="dataSource"><ng-container matColumnDef="nombre"><th mat-header-cell *matHeaderCellDef>Nombre</th><td mat-cell *matCellDef="let p">{{p.nombre}}</td></ng-container><ng-container matColumnDef="categoria"><th mat-header-cell *matHeaderCellDef>Categoría</th><td mat-cell *matCellDef="let p">{{p.categoria.nombre}}</td></ng-container><ng-container matColumnDef="precio"><th mat-header-cell *matHeaderCellDef>Precio</th><td mat-cell *matCellDef="let p">{{p.precio_base}}</td></ng-container><ng-container matColumnDef="estado"><th mat-header-cell *matHeaderCellDef>Estado</th><td mat-cell *matCellDef="let p">{{p.estado}}</td></ng-container><ng-container matColumnDef="acciones"><th mat-header-cell *matHeaderCellDef>Acciones</th><td mat-cell *matCellDef="let p"><button mat-button (click)="openForm(p)">Editar</button><button mat-button color="warn" [disabled]="p.estado==='INACTIVO'" (click)="disable(p)">Desactivar</button></td></ng-container><tr mat-header-row *matHeaderRowDef="columns"></tr><tr mat-row *matRowDef="let row;columns:columns"></tr></table></div><mat-paginator [pageSize]="5" [pageSizeOptions]="[5,10,25]" />
    }
  </section>`,
  styles: ['.page{padding:2rem}.toolbar,.filters{display:flex;gap:1rem;justify-content:space-between;align-items:center;margin-bottom:1rem}.filters{justify-content:start}table{width:100%}']
})
export class ProductListComponent implements OnInit {
  private service = inject(ProductAdminService); private dialog = inject(MatDialog); private snack = inject(MatSnackBar);
  @ViewChild(MatPaginator) paginator!: MatPaginator;
  dataSource = new MatTableDataSource<AdminProduct>([]); search = new FormControl(''); status = new FormControl(''); loading = true; error = false;
  columns = ['nombre', 'categoria', 'precio', 'estado', 'acciones'];
  ngOnInit(): void { this.load(); }
  load(): void { this.loading = true; this.service.list().subscribe({ next: (products) => { this.dataSource.data = products; this.dataSource.filterPredicate = (item, filter) => { const criteria = JSON.parse(filter); return item.nombre.toLowerCase().includes(criteria.name) && (!criteria.state || item.estado === criteria.state); }; this.applyFilters(); this.loading = false; setTimeout(() => this.dataSource.paginator = this.paginator); }, error: () => { this.error = true; this.loading = false; } }); }
  applyFilters(): void { this.dataSource.filter = JSON.stringify({ name: (this.search.value ?? '').toLowerCase(), state: this.status.value ?? '' }); }
  openForm(product?: AdminProduct): void { this.dialog.open(ProductFormComponent, { data: product ?? null, width: '34rem' }).afterClosed().subscribe((result) => { if (result) { this.updateLocal(result); this.snack.open('Producto guardado', 'Cerrar', { duration: 3000 }); } }); }
  disable(product: AdminProduct): void { this.dialog.open(ConfirmDialogComponent, { data: { title: 'Desactivar producto', message: `Desactivar ${product.nombre}?` } }).afterClosed().subscribe((ok) => { if (ok) this.service.disable(product.id_producto).subscribe({ next: (result) => { this.updateLocal(result); this.snack.open('Producto desactivado', 'Cerrar', { duration: 3000 }); }, error: () => this.snack.open('No fue posible desactivar', 'Cerrar', { duration: 5000 }) }); }); }
  private updateLocal(product: AdminProduct): void { const index = this.dataSource.data.findIndex((item) => item.id_producto === product.id_producto); this.dataSource.data = index < 0 ? [...this.dataSource.data, product] : this.dataSource.data.map((item) => item.id_producto === product.id_producto ? product : item); this.applyFilters(); }
}
