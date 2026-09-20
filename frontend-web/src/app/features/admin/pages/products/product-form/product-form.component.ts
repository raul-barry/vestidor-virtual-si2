import { Component, Inject, OnDestroy, OnInit, Optional, inject } from '@angular/core';
import { ReactiveFormsModule, NonNullableFormBuilder, Validators } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { Observable, map, of, switchMap } from 'rxjs';
import { API_URL } from '../../../../../core/config/api.config';
import { AdminProduct, ProductRequest } from '../../../models/product-admin.model';
import { AdminCategory } from '../../../models/category-admin.model';
import { CategoryAdminService } from '../../../services/category-admin.service';
import { ProductAdminService } from '../../../services/product-admin.service';

@Component({
  selector: 'app-product-form',
  standalone: true,
  imports: [ReactiveFormsModule, MatButtonModule, MatDialogModule, MatFormFieldModule, MatInputModule, MatSelectModule, MatSnackBarModule],
  template: `
    <section class="form-page">
      <h2>{{ product ? 'Editar producto' : 'Crear producto' }}</h2>
      <form [formGroup]="form" (ngSubmit)="save()">
        <mat-form-field><mat-label>Nombre</mat-label><input matInput formControlName="nombre"><mat-error>Nombre requerido</mat-error></mat-form-field>
        <mat-form-field><mat-label>Descripción</mat-label><textarea matInput formControlName="descripcion"></textarea></mat-form-field>
        <mat-form-field><mat-label>Precio base</mat-label><input matInput type="number" formControlName="precio_base"><mat-error>Precio mayor a cero</mat-error></mat-form-field>
        <mat-form-field>
          <mat-label>Categoría</mat-label>
          <mat-select formControlName="id_categoria">
            <mat-option [value]="0">Seleccionar categoría</mat-option>
            @for (category of categories; track category.id_categoria) { <mat-option [value]="category.id_categoria">{{ category.nombre }}</mat-option> }
          </mat-select>
          <mat-error>Categoría requerida</mat-error>
        </mat-form-field>

        <div class="image-field">
          <label for="product-image">Imagen principal</label>
          <input id="product-image" type="file" accept="image/jpeg,image/png,image/webp" (change)="selectImage($event)">
          <small>JPG, PNG o WebP. Tamaño máximo: 5 MB.</small>
          @if (previewUrl) {
            <div class="preview">
              <img [src]="previewUrl" alt="Vista previa de la imagen del producto">
              <button mat-stroked-button color="warn" type="button" (click)="removeImage()">Eliminar imagen</button>
            </div>
          }
        </div>

        <div class="actions">
          <button mat-button type="button" (click)="cancel()">Cancelar</button>
          <button mat-flat-button color="primary" [disabled]="form.invalid || saving">{{ saving ? 'Guardando...' : 'Guardar' }}</button>
        </div>
      </form>
    </section>
  `,
  styles: [`
    .form-page{max-width:38rem;padding:2rem}.form-page form{display:grid;gap:.75rem}.actions{display:flex;justify-content:end;gap:.5rem}
    .image-field{display:grid;gap:.55rem;padding:1rem;border:1px solid #ddd;border-radius:.75rem}.image-field label{font-weight:600}.image-field small{color:#666}
    .preview{display:flex;align-items:center;gap:1rem;flex-wrap:wrap}.preview img{width:9rem;height:9rem;object-fit:cover;border-radius:.65rem;border:1px solid #ddd}
  `]
})
export class ProductFormComponent implements OnInit, OnDestroy {
  private fb = inject(NonNullableFormBuilder);
  private service = inject(ProductAdminService);
  private categoryService = inject(CategoryAdminService);
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private snack = inject(MatSnackBar);
  product: AdminProduct | null = null;
  saving = false;
  categories: AdminCategory[] = [];
  selectedImage: File | null = null;
  previewUrl: string | null = null;
  private objectUrl: string | null = null;
  private deleteCurrentImage = false;
  form = this.fb.group({ nombre: ['', Validators.required], descripcion: [''], precio_base: [0, [Validators.required, Validators.min(0.01)]], id_categoria: [0, [Validators.required, Validators.min(1)]] });

  constructor(@Optional() @Inject(MAT_DIALOG_DATA) data: AdminProduct | null, @Optional() private ref: MatDialogRef<ProductFormComponent> | null) {
    if (data) this.setProduct(data);
  }

  ngOnInit(): void {
    this.categoryService.list().subscribe({
      next: categories => this.categories = categories.filter(category => category.estado === 'ACTIVO' || category.id_categoria === this.product?.categoria.id_categoria),
      error: () => this.snack.open('No fue posible cargar las categorías', 'Cerrar', { duration: 4000 })
    });
    const id = Number(this.route.snapshot.paramMap.get('id'));
    if (!this.product && Number.isInteger(id) && id > 0) this.service.getById(id).subscribe({ next: product => this.setProduct(product), error: () => this.snack.open('Producto no encontrado', 'Cerrar', { duration: 4000 }) });
  }

  ngOnDestroy(): void { this.releaseObjectUrl(); }

  selectImage(event: Event): void {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0] ?? null;
    if (!file) return;
    if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type) || file.size > 5 * 1024 * 1024) {
      this.snack.open('Selecciona una imagen JPG, PNG o WebP de hasta 5 MB', 'Cerrar', { duration: 5000 });
      input.value = '';
      return;
    }
    this.releaseObjectUrl();
    this.selectedImage = file;
    this.deleteCurrentImage = false;
    this.objectUrl = URL.createObjectURL(file);
    this.previewUrl = this.objectUrl;
  }

  removeImage(): void {
    this.releaseObjectUrl();
    this.previewUrl = null;
    this.selectedImage = null;
    this.deleteCurrentImage = Boolean(this.product?.imagen_url);
  }

  save(): void {
    if (this.form.invalid) { this.form.markAllAsTouched(); return; }
    this.saving = true;
    const value = this.form.getRawValue() as ProductRequest;
    const request = this.product ? this.service.update(this.product.id_producto, value) : this.service.create(value);
    request.pipe(switchMap(product => this.persistImage(product))).subscribe({
      next: product => {
        this.saving = false;
        this.snack.open('Producto guardado correctamente', 'Cerrar', { duration: 3000 });
        if (this.ref) this.ref.close(product); else void this.router.navigate(['/admin/products']);
      },
      error: (error: { error?: { detail?: string; message?: string } }) => {
        this.saving = false;
        this.snack.open(error.error?.detail ?? error.error?.message ?? 'No fue posible guardar el producto', 'Cerrar', { duration: 5000 });
      }
    });
  }

  cancel(): void { if (this.ref) this.ref.close(); else void this.router.navigate(['/admin/products']); }

  private persistImage(product: AdminProduct): Observable<AdminProduct> {
    if (this.selectedImage) return this.service.uploadImage(product.id_producto, this.selectedImage).pipe(map(result => ({ ...product, imagen_url: result.imagen_url })));
    if (this.deleteCurrentImage) return this.service.deleteImage(product.id_producto).pipe(map(() => ({ ...product, imagen_url: null })));
    return of(product);
  }

  private setProduct(product: AdminProduct): void {
    this.product = product;
    this.form.patchValue({ nombre: product.nombre, descripcion: product.descripcion ?? '', precio_base: Number(product.precio_base), id_categoria: product.categoria.id_categoria });
    this.previewUrl = product.imagen_url ? `${API_URL}${product.imagen_url}` : null;
    this.deleteCurrentImage = false;
  }

  private releaseObjectUrl(): void {
    if (this.objectUrl) URL.revokeObjectURL(this.objectUrl);
    this.objectUrl = null;
  }
}
