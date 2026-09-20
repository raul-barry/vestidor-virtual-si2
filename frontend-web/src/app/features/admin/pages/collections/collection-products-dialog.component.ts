import { Component, Inject, OnInit, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MAT_DIALOG_DATA, MatDialogModule } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { Collection, CollectionProduct } from '../../models/commercial-master.model';
import { CommercialMasterAdminService } from '../../services/commercial-master-admin.service';

interface CollectionProductsDialogData { collection: Collection; mode: 'view' | 'associate'; }

@Component({
  standalone: true,
  imports: [FormsModule, MatDialogModule, MatButtonModule, MatFormFieldModule, MatSelectModule, MatSnackBarModule],
  template: `
    <h2 mat-dialog-title>Productos · {{ data.collection.nombre }}</h2>
    <mat-dialog-content>
      <section class="associate">
        <h3>Asociar producto</h3>
        <mat-form-field><mat-label>Producto disponible</mat-label><mat-select [(ngModel)]="selectedProductId"><mat-option [value]="0">Seleccionar</mat-option>@for (product of availableProducts; track product.id_producto) { <mat-option [value]="product.id_producto">{{ product.nombre }}</mat-option> }</mat-select></mat-form-field>
        <button mat-flat-button color="primary" [disabled]="!selectedProductId || busy" (click)="associate()">Asociar producto</button>
      </section>
      <h3>Productos asociados</h3>
      @if (loading) { <p>Cargando...</p> }
      @else if (!associated.length) { <p>No hay productos asociados a esta colección.</p> }
      @else {
        <div class="products">@for (product of associated; track product.id_producto) { <div><span>{{ product.nombre }}</span><button mat-button color="warn" [disabled]="busy" (click)="remove(product)">Quitar producto</button></div> }</div>
      }
    </mat-dialog-content>
    <mat-dialog-actions align="end"><button mat-button mat-dialog-close>Cerrar</button></mat-dialog-actions>
  `,
  styles: ['.associate{display:flex;align-items:center;gap:1rem;flex-wrap:wrap;padding:.5rem 0 1rem;border-bottom:1px solid #ddd}.associate h3{width:100%;margin-bottom:0}.products{display:grid;min-width:min(34rem,75vw)}.products div{display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid #eee;padding:.5rem 0}mat-form-field{min-width:18rem}@media(max-width:600px){.products{min-width:0}.associate{display:grid}mat-form-field{min-width:0}}']
})
export class CollectionProductsDialogComponent implements OnInit {
  private service = inject(CommercialMasterAdminService);
  private snack = inject(MatSnackBar);
  allProducts: CollectionProduct[] = [];
  associated: CollectionProduct[] = [];
  selectedProductId = 0;
  loading = true;
  busy = false;

  constructor(@Inject(MAT_DIALOG_DATA) public data: CollectionProductsDialogData) {}
  ngOnInit(): void { this.load(); }
  get availableProducts(): CollectionProduct[] { return this.allProducts.filter(product => product.id_coleccion !== this.data.collection.id_coleccion); }
  load(): void {
    this.loading = true;
    this.service.listProducts().subscribe({ next: products => { this.allProducts = products; this.loadAssociated(); }, error: () => { this.loading = false; this.notify('No fue posible cargar los productos'); } });
  }
  associate(): void {
    if (!this.selectedProductId) return;
    this.busy = true;
    this.service.associateProduct(this.data.collection.id_coleccion, this.selectedProductId).subscribe({ next: () => { this.selectedProductId = 0; this.busy = false; this.notify('Producto asociado'); this.load(); }, error: () => { this.busy = false; this.notify('No fue posible asociar el producto'); } });
  }
  remove(product: CollectionProduct): void {
    this.busy = true;
    this.service.removeProduct(this.data.collection.id_coleccion, product.id_producto).subscribe({ next: () => { this.busy = false; this.notify('Producto quitado de la colección'); this.load(); }, error: () => { this.busy = false; this.notify('No fue posible quitar el producto'); } });
  }
  private loadAssociated(): void { this.service.listCollectionProducts(this.data.collection.id_coleccion).subscribe({ next: products => { this.associated = products; this.loading = false; }, error: () => { this.loading = false; this.notify('No fue posible cargar los productos asociados'); } }); }
  private notify(message: string): void { this.snack.open(message, 'Cerrar', { duration: 3500 }); }
}
