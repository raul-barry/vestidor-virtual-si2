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
import { InventoryAdmin } from '../../../models/inventory-admin.model';
import { InventoryAdminService } from '../../../services/inventory-admin.service';
import { EmptyStateComponent } from '../../../shared/components/empty-state/empty-state.component';
import { ErrorMessageComponent } from '../../../shared/components/error-message/error-message.component';
import { LoadingSpinnerComponent } from '../../../shared/components/loading-spinner/loading-spinner.component';
import { InventoryFormComponent } from '../inventory-form/inventory-form.component';
import { InventoryHistoryDialogComponent } from '../inventory-history-dialog/inventory-history-dialog.component';
import { StockActionDialogComponent } from '../stock-action-dialog.component';

@Component({
  selector: 'app-inventory-list', standalone: true,
  imports: [ReactiveFormsModule, MatButtonModule, MatDialogModule, MatFormFieldModule, MatInputModule, MatPaginatorModule, MatSelectModule, MatSnackBarModule, MatTableModule, LoadingSpinnerComponent, EmptyStateComponent, ErrorMessageComponent],
  template: `<section class="page">
    <div class="toolbar"><h1>Inventario</h1><button mat-flat-button color="primary" (click)="create()">Crear inventario</button></div>
    <div class="filters"><mat-form-field><mat-label>Buscar producto o SKU</mat-label><input matInput [formControl]="search" (input)="apply()"></mat-form-field><mat-form-field><mat-label>Sucursal</mat-label><input matInput [formControl]="branch" (input)="apply()"></mat-form-field><mat-form-field><mat-label>Stock</mat-label><mat-select [formControl]="stockState" (selectionChange)="apply()"><mat-option value="">Todos</mat-option><mat-option value="LOW">Stock bajo</mat-option><mat-option value="NORMAL">Normal</mat-option></mat-select></mat-form-field></div>
    @if (loading) { <app-loading-spinner /> } @else if (error) { <app-error-message /> } @else if (!source.data.length) { <app-empty-state message="No hay inventario." /> } @else {
      <div class="table-scroll" role="region" aria-label="Tabla de datos" tabindex="0"><table mat-table [dataSource]="source"><ng-container matColumnDef="producto"><th mat-header-cell *matHeaderCellDef>Producto</th><td mat-cell *matCellDef="let i">{{i.producto}}</td></ng-container><ng-container matColumnDef="sku"><th mat-header-cell *matHeaderCellDef>SKU</th><td mat-cell *matCellDef="let i">{{i.sku}}</td></ng-container><ng-container matColumnDef="talla"><th mat-header-cell *matHeaderCellDef>Talla</th><td mat-cell *matCellDef="let i">{{i.talla}}</td></ng-container><ng-container matColumnDef="color"><th mat-header-cell *matHeaderCellDef>Color</th><td mat-cell *matCellDef="let i">{{i.color}}</td></ng-container><ng-container matColumnDef="sucursal"><th mat-header-cell *matHeaderCellDef>Sucursal</th><td mat-cell *matCellDef="let i">{{i.sucursal}}</td></ng-container><ng-container matColumnDef="stock"><th mat-header-cell *matHeaderCellDef>Stock</th><td mat-cell *matCellDef="let i">{{i.stock}}</td></ng-container><ng-container matColumnDef="estado"><th mat-header-cell *matHeaderCellDef>Estado</th><td mat-cell *matCellDef="let i">{{i.stock_bajo?'Stock bajo':'Normal'}}</td></ng-container><ng-container matColumnDef="acciones"><th mat-header-cell *matHeaderCellDef>Acciones</th><td mat-cell *matCellDef="let i"><button mat-button (click)="action(i,'increase')">Agregar</button><button mat-button (click)="action(i,'decrease')">Retirar</button><button mat-button (click)="action(i,'adjust')">Ajustar</button><button mat-button (click)="history(i)">Historial</button></td></ng-container><tr mat-header-row *matHeaderRowDef="cols"></tr><tr mat-row *matRowDef="let row;columns:cols"></tr></table></div><mat-paginator [pageSize]="5" />
    }
  </section>`,
  styles: ['.page{padding:2rem}.toolbar,.filters{display:flex;gap:1rem;align-items:center;justify-content:space-between;margin-bottom:1rem}.filters{justify-content:start;flex-wrap:wrap}.toolbar{flex-wrap:wrap}@media(max-width:600px){.page{padding:1rem}.filters mat-form-field{width:100%}}table{width:100%}']
})
export class InventoryListComponent implements OnInit {
  private service = inject(InventoryAdminService); private dialog = inject(MatDialog); private snack = inject(MatSnackBar);
  @ViewChild(MatPaginator) paginator!: MatPaginator;
  source = new MatTableDataSource<InventoryAdmin>([]); search = new FormControl(''); branch = new FormControl(''); stockState = new FormControl(''); loading = true; error = false;
  cols = ['producto', 'sku', 'talla', 'color', 'sucursal', 'stock', 'estado', 'acciones'];
  ngOnInit(): void { this.load(); }
  load(): void { this.loading = true; this.error = false; this.service.getInventory().subscribe({ next: (items) => { this.source.data = items; this.source.filterPredicate = (item, filter) => { const criteria = JSON.parse(filter); return `${item.producto} ${item.sku}`.toLowerCase().includes(criteria.search) && item.sucursal.toLowerCase().includes(criteria.branch) && (!criteria.stock || (criteria.stock === 'LOW' && item.stock_bajo) || (criteria.stock === 'NORMAL' && !item.stock_bajo)); }; this.apply(); this.loading = false; setTimeout(() => this.source.paginator = this.paginator); }, error: () => { this.error = true; this.loading = false; } }); }
  apply(): void { this.source.paginator?.firstPage(); this.source.filter = JSON.stringify({ search: (this.search.value ?? '').toLowerCase(), branch: (this.branch.value ?? '').toLowerCase(), stock: this.stockState.value ?? '' }); }
  create(): void { this.dialog.open(InventoryFormComponent, { width: '30rem' }).afterClosed().subscribe((result) => { if (result) { this.updateLocal(result); this.snack.open('Inventario creado', 'Cerrar', { duration: 3000 }); } }); }
  action(item: InventoryAdmin, type: 'increase' | 'decrease' | 'adjust'): void { const title = type === 'increase' ? 'Agregar stock' : type === 'decrease' ? 'Retirar stock' : 'Ajustar stock'; this.dialog.open(StockActionDialogComponent, { data: { id: item.id_inventario, type, title, adjust: type === 'adjust' }, width: '28rem' }).afterClosed().subscribe((result) => { if (result) this.updateLocal(result); }); }
  history(item: InventoryAdmin): void { this.dialog.open(InventoryHistoryDialogComponent, { data: { id: item.id_inventario }, width: '56rem' }); }
  private updateLocal(item: InventoryAdmin): void { const index = this.source.data.findIndex((current) => current.id_inventario === item.id_inventario); this.source.data = index < 0 ? [...this.source.data, item] : this.source.data.map((current) => current.id_inventario === item.id_inventario ? item : current); this.apply(); }
}
