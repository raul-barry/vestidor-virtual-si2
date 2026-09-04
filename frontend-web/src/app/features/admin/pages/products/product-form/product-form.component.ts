import { Component, Inject, OnInit, Optional, inject } from '@angular/core';
import { ReactiveFormsModule, NonNullableFormBuilder, Validators } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { AdminProduct, ProductRequest } from '../../../models/product-admin.model';
import { ProductAdminService } from '../../../services/product-admin.service';

@Component({
  selector: 'app-product-form', standalone: true,
  imports: [ReactiveFormsModule, MatButtonModule, MatDialogModule, MatFormFieldModule, MatInputModule, MatSnackBarModule],
  template: `<section class="form-page"><h2>{{ product ? 'Editar producto' : 'Crear producto' }}</h2><form [formGroup]="form" (ngSubmit)="save()"><mat-form-field><mat-label>Nombre</mat-label><input matInput formControlName="nombre"><mat-error>Nombre requerido</mat-error></mat-form-field><mat-form-field><mat-label>Descripción</mat-label><textarea matInput formControlName="descripcion"></textarea></mat-form-field><mat-form-field><mat-label>Precio base</mat-label><input matInput type="number" formControlName="precio_base"><mat-error>Precio mayor a cero</mat-error></mat-form-field><mat-form-field><mat-label>ID categoría</mat-label><input matInput type="number" formControlName="id_categoria"><mat-error>Categoría requerida</mat-error></mat-form-field><div class="actions"><button mat-button type="button" (click)="cancel()">Cancelar</button><button mat-flat-button color="primary" [disabled]="form.invalid || saving">{{saving?'Guardando...':'Guardar'}}</button></div></form></section>`,
  styles: ['.form-page{max-width:38rem;padding:2rem}.form-page form{display:grid;gap:.75rem}.actions{display:flex;justify-content:end;gap:.5rem}']
})
export class ProductFormComponent implements OnInit {
  private fb = inject(NonNullableFormBuilder); private service = inject(ProductAdminService); private route = inject(ActivatedRoute); private router = inject(Router); private snack = inject(MatSnackBar);
  product: AdminProduct | null = null; saving = false;
  form = this.fb.group({ nombre: ['', Validators.required], descripcion: [''], precio_base: [0, [Validators.required, Validators.min(0.01)]], id_categoria: [0, [Validators.required, Validators.min(1)]] });
  constructor(@Optional() @Inject(MAT_DIALOG_DATA) data: AdminProduct | null, @Optional() private ref: MatDialogRef<ProductFormComponent> | null) { if (data) this.setProduct(data); }
  ngOnInit(): void { const id = Number(this.route.snapshot.paramMap.get('id')); if (!this.product && Number.isInteger(id) && id > 0) this.service.getById(id).subscribe({ next: p => this.setProduct(p), error: () => this.snack.open('Producto no encontrado', 'Cerrar', {duration:4000}) }); }
  save(): void { if (this.form.invalid) { this.form.markAllAsTouched(); return; } this.saving = true; const value = this.form.getRawValue() as ProductRequest; const request = this.product ? this.service.update(this.product.id_producto, value) : this.service.create(value); request.subscribe({ next: product => { this.saving=false; this.snack.open('Producto guardado correctamente','Cerrar',{duration:3000}); if(this.ref) this.ref.close(product); else void this.router.navigate(['/admin/products']); }, error: (error:{error?:{message?:string}}) => { this.saving=false; this.snack.open(error.error?.message ?? 'No fue posible guardar el producto','Cerrar',{duration:5000}); } }); }
  cancel(): void { if (this.ref) this.ref.close(); else void this.router.navigate(['/admin/products']); }
  private setProduct(product: AdminProduct): void { this.product = product; this.form.patchValue({ nombre: product.nombre, descripcion: product.descripcion ?? '', precio_base: Number(product.precio_base), id_categoria: product.categoria.id_categoria }); }
}
