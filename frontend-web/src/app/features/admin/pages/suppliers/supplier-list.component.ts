import { Component, OnInit, inject } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatTableModule } from '@angular/material/table';
import { Supplier, SupplierRequest } from '../../models/commercial-master.model';
import { CommercialMasterAdminService } from '../../services/commercial-master-admin.service';
import { SupplierDialogComponent } from './supplier-dialog.component';

@Component({
  standalone: true,
  imports: [MatButtonModule, MatDialogModule, MatSnackBarModule, MatTableModule],
  template: `
    <section class="page">
      <header><div><h1>Proveedores</h1><p>Empresas y contactos que abastecen el catálogo.</p></div><button mat-flat-button color="primary" (click)="openDialog()">Nuevo proveedor</button></header>
      @if (loading) { <p>Cargando proveedores...</p> }
      @else {
        <div class="table-scroll" role="region" aria-label="Proveedores" tabindex="0">
          <table mat-table [dataSource]="suppliers">
            <ng-container matColumnDef="empresa"><th mat-header-cell *matHeaderCellDef>Empresa</th><td mat-cell *matCellDef="let row"><strong>{{ row.nombre }}</strong><br><small>{{ row.descripcion || 'Sin descripción' }}</small></td></ng-container>
            <ng-container matColumnDef="contacto"><th mat-header-cell *matHeaderCellDef>Contacto</th><td mat-cell *matCellDef="let row">{{ row.persona_contacto || '-' }}<br><small>{{ row.telefono || '-' }} · {{ row.correo || '-' }}</small></td></ng-container>
            <ng-container matColumnDef="direccion"><th mat-header-cell *matHeaderCellDef>Dirección</th><td mat-cell *matCellDef="let row">{{ row.direccion || '-' }}</td></ng-container>
            <ng-container matColumnDef="productos"><th mat-header-cell *matHeaderCellDef>Productos</th><td mat-cell *matCellDef="let row">{{ row.productos?.length ? row.productos.map(productName).join(', ') : '-' }}</td></ng-container>
            <ng-container matColumnDef="estado"><th mat-header-cell *matHeaderCellDef>Estado</th><td mat-cell *matCellDef="let row"><span class="state" [class.inactive]="row.estado === 'INACTIVO'">{{ row.estado }}</span></td></ng-container>
            <ng-container matColumnDef="acciones"><th mat-header-cell *matHeaderCellDef>Acciones</th><td mat-cell *matCellDef="let row"><button mat-button (click)="openDialog(row)">Editar</button><button mat-button [color]="row.estado === 'ACTIVO' ? 'warn' : 'primary'" (click)="toggle(row)">{{ row.estado === 'ACTIVO' ? 'Desactivar' : 'Activar' }}</button></td></ng-container>
            <tr mat-header-row *matHeaderRowDef="columns"></tr><tr mat-row *matRowDef="let row; columns: columns"></tr>
          </table>
        </div>
      }
    </section>
  `,
  styles: ['.page{padding:2rem}header{display:flex;justify-content:space-between;gap:1rem;align-items:center;margin-bottom:1.5rem}h1{margin:0}header p{color:#666;margin:.35rem 0 0}table{width:100%}.state{font-weight:600;color:#24733d}.state.inactive{color:#8b3030}small{color:#666}.table-scroll{overflow:auto}@media(max-width:650px){.page{padding:1rem}header{align-items:flex-start;flex-direction:column}}']
})
export class SupplierListComponent implements OnInit {
  private service = inject(CommercialMasterAdminService);
  private dialog = inject(MatDialog);
  private snack = inject(MatSnackBar);
  suppliers: Supplier[] = [];
  loading = true;
  columns = ['empresa', 'contacto', 'direccion', 'productos', 'estado', 'acciones'];
  productName(product: { nombre: string }): string { return product.nombre; }

  ngOnInit(): void { this.load(); }
  load(): void { this.loading = true; this.service.listSuppliers().subscribe({ next: rows => { this.suppliers = rows; this.loading = false; }, error: () => { this.loading = false; this.notify('No fue posible cargar los proveedores'); } }); }
  openDialog(supplier: Supplier | null = null): void {
    this.dialog.open(SupplierDialogComponent, { data: supplier, width: '46rem', maxWidth: '96vw' }).afterClosed().subscribe((request?: SupplierRequest) => {
      if (!request) return;
      const operation = supplier ? this.service.updateSupplier(supplier.id_proveedor, request) : this.service.createSupplier(request);
      operation.subscribe({ next: () => { this.notify('Proveedor guardado correctamente'); this.load(); }, error: error => this.notify(error.error?.detail ?? 'No fue posible guardar el proveedor') });
    });
  }
  toggle(supplier: Supplier): void {
    const estado = supplier.estado === 'ACTIVO' ? 'INACTIVO' : 'ACTIVO';
    this.service.setSupplierState(supplier.id_proveedor, estado).subscribe({ next: () => { this.notify(estado === 'ACTIVO' ? 'Proveedor activado' : 'Proveedor desactivado'); this.load(); }, error: () => this.notify('No fue posible cambiar el estado') });
  }
  private notify(message: string): void { this.snack.open(message, 'Cerrar', { duration: 3500 }); }
}
