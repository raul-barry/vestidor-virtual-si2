import { Component, OnInit, inject } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatTableModule } from '@angular/material/table';
import { Collection, CollectionRequest } from '../../models/commercial-master.model';
import { CommercialMasterAdminService } from '../../services/commercial-master-admin.service';
import { CollectionDialogComponent } from './collection-dialog.component';
import { CollectionProductsDialogComponent } from './collection-products-dialog.component';

@Component({
  standalone: true,
  imports: [MatButtonModule, MatDialogModule, MatSnackBarModule, MatTableModule],
  template: `
    <section class="page">
      <header><div><h1>Colecciones</h1><p>Gestión de colección</p></div><button mat-flat-button color="primary" (click)="openDialog()">Nueva colección</button></header>
      @if (loading) { <p>Cargando colecciones...</p> }
      @else {
        <div class="table-scroll" role="region" aria-label="Colecciones" tabindex="0">
          <table mat-table [dataSource]="collections">
            <ng-container matColumnDef="coleccion"><th mat-header-cell *matHeaderCellDef>Colección</th><td mat-cell *matCellDef="let row"><strong>{{ row.nombre }}</strong><br><small>{{ row.descripcion || 'Sin descripción' }}</small></td></ng-container>
            <ng-container matColumnDef="temporada"><th mat-header-cell *matHeaderCellDef>Temporada</th><td mat-cell *matCellDef="let row">{{ row.temporada || '-' }} {{ row.anio || '' }}</td></ng-container>
            <ng-container matColumnDef="vigencia"><th mat-header-cell *matHeaderCellDef>Vigencia</th><td mat-cell *matCellDef="let row">{{ row.fecha_inicio || '-' }} — {{ row.fecha_fin || '-' }}</td></ng-container>
            <ng-container matColumnDef="estado"><th mat-header-cell *matHeaderCellDef>Estado</th><td mat-cell *matCellDef="let row"><span class="state" [class.inactive]="row.estado === 'INACTIVO'">{{ row.estado }}</span></td></ng-container>
            <ng-container matColumnDef="acciones"><th mat-header-cell *matHeaderCellDef>Gestión de colección</th><td mat-cell *matCellDef="let row"><button mat-button (click)="openDialog(row)">Editar</button><button mat-button [color]="row.estado === 'ACTIVO' ? 'warn' : 'primary'" (click)="toggle(row)">{{ row.estado === 'ACTIVO' ? 'Desactivar' : 'Activar' }}</button></td></ng-container>
            <ng-container matColumnDef="productos"><th mat-header-cell *matHeaderCellDef>Productos asociados</th><td mat-cell *matCellDef="let row"><button mat-stroked-button (click)="openProducts(row, 'view')">Ver productos</button><button mat-button color="primary" (click)="openProducts(row, 'associate')">Asociar producto</button></td></ng-container>
            <tr mat-header-row *matHeaderRowDef="columns"></tr><tr mat-row *matRowDef="let row; columns: columns"></tr>
          </table>
        </div>
      }
    </section>
  `,
  styles: ['.page{padding:2rem}header{display:flex;justify-content:space-between;gap:1rem;align-items:center;margin-bottom:1.5rem}h1{margin:0}header p{color:#666;margin:.35rem 0 0}table{width:100%}.state{font-weight:600;color:#24733d}.state.inactive{color:#8b3030}small{color:#666}.table-scroll{overflow:auto}td button+button{margin-left:.25rem}@media(max-width:650px){.page{padding:1rem}header{align-items:flex-start;flex-direction:column}}']
})
export class CollectionListComponent implements OnInit {
  private service = inject(CommercialMasterAdminService);
  private dialog = inject(MatDialog);
  private snack = inject(MatSnackBar);
  collections: Collection[] = [];
  loading = true;
  columns = ['coleccion', 'temporada', 'vigencia', 'estado', 'acciones', 'productos'];

  ngOnInit(): void { this.load(); }
  load(): void { this.loading = true; this.service.listCollections().subscribe({ next: rows => { this.collections = rows; this.loading = false; }, error: () => { this.loading = false; this.notify('No fue posible cargar las colecciones'); } }); }
  openDialog(collection: Collection | null = null): void {
    this.dialog.open(CollectionDialogComponent, { data: collection, width: '46rem', maxWidth: '96vw' }).afterClosed().subscribe((request?: CollectionRequest) => {
      if (!request) return;
      const operation = collection ? this.service.updateCollection(collection.id_coleccion, request) : this.service.createCollection(request);
      operation.subscribe({ next: () => { this.notify('Colección guardada correctamente'); this.load(); }, error: error => this.notify(error.error?.detail ?? 'No fue posible guardar la colección') });
    });
  }
  toggle(collection: Collection): void {
    const estado = collection.estado === 'ACTIVO' ? 'INACTIVO' : 'ACTIVO';
    this.service.setCollectionState(collection.id_coleccion, estado).subscribe({ next: () => { this.notify(estado === 'ACTIVO' ? 'Colección activada' : 'Colección desactivada'); this.load(); }, error: () => this.notify('No fue posible cambiar el estado') });
  }
  openProducts(collection: Collection, mode: 'view' | 'associate'): void { this.dialog.open(CollectionProductsDialogComponent, { data: { collection, mode }, width: '42rem', maxWidth: '96vw' }); }
  private notify(message: string): void { this.snack.open(message, 'Cerrar', { duration: 3500 }); }
}
