import { Component, Inject, OnInit, Optional, inject } from '@angular/core';
import { NonNullableFormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { AdminVariant, VariantRequest } from '../../../models/variant-admin.model';
import { VariantAdminService } from '../../../services/variant-admin.service';
import { ProductAdminService } from '../../../services/product-admin.service';
import { SizeAdminService } from '../../../services/size-admin.service';
import { ColorAdminService } from '../../../services/color-admin.service';
import { forkJoin } from 'rxjs';

export interface VariantFormData { productId?: number; variant?: AdminVariant; }

@Component({ selector:'app-variant-form', standalone:true, imports:[ReactiveFormsModule,MatButtonModule,MatDialogModule,MatFormFieldModule,MatInputModule,MatSelectModule,MatSnackBarModule], template:`<h2 mat-dialog-title>{{data.variant?'Editar variante':'Crear variante'}}</h2><form [formGroup]="form" (ngSubmit)="save()" mat-dialog-content><mat-form-field><mat-label>Producto</mat-label><mat-select formControlName="id_producto" (selectionChange)="suggestSku()">@for(p of products;track p.id_producto){<mat-option [value]="p.id_producto">{{p.nombre}}</mat-option>}</mat-select><mat-error>Producto obligatorio</mat-error></mat-form-field><mat-form-field><mat-label>Talla</mat-label><mat-select formControlName="id_talla" (selectionChange)="suggestSku()">@for(s of sizes;track s.id_talla){<mat-option [value]="s.id_talla">{{s.nombre}}</mat-option>}</mat-select><mat-error>Talla obligatoria</mat-error></mat-form-field><mat-form-field><mat-label>Color</mat-label><mat-select formControlName="id_color" (selectionChange)="suggestSku()">@for(c of colors;track c.id_color){<mat-option [value]="c.id_color">{{c.nombre}}</mat-option>}</mat-select><mat-error>Color obligatorio</mat-error></mat-form-field><mat-form-field><mat-label>Código de variante (SKU)</mat-label><input matInput formControlName="sku"><mat-hint>Código único para esta combinación. Puedes editar la sugerencia.</mat-hint><mat-error>SKU obligatorio</mat-error></mat-form-field><div mat-dialog-actions align="end"><button mat-button type="button" mat-dialog-close>Cancelar</button><button mat-flat-button color="primary" [disabled]="form.invalid || saving">Guardar</button></div></form>`, styles:['form{display:grid;gap:.75rem}mat-form-field{width:100%}'] })
export class VariantFormComponent implements OnInit {
  private fb = inject(NonNullableFormBuilder);
  private service = inject(VariantAdminService);
  private productsService = inject(ProductAdminService);
  private sizesService = inject(SizeAdminService);
  private colorsService = inject(ColorAdminService);
  private snack = inject(MatSnackBar);
  saving = false;
  products: any[]=[]; sizes: any[]=[]; colors: any[]=[];
  form = this.fb.group({
    id_producto: [0, [Validators.required, Validators.min(1)]],
    sku: ['', Validators.required],
    id_talla: [0, [Validators.required, Validators.min(1)]],
    id_color: [0, [Validators.required, Validators.min(1)]]
  });

  constructor(@Inject(MAT_DIALOG_DATA) public data: VariantFormData, @Optional() private ref: MatDialogRef<VariantFormComponent> | null) {
    if (data.variant) this.form.patchValue({ sku: data.variant.sku });
    if (data.productId) this.form.controls.id_producto.setValue(data.productId);
  }

  ngOnInit(): void { forkJoin({products:this.productsService.list(),sizes:this.sizesService.list(),colors:this.colorsService.list()}).subscribe({next: data=>{this.products=data.products.filter(p=>p.estado==='ACTIVO');this.sizes=data.sizes.filter(s=>s.estado==='ACTIVO');this.colors=data.colors.filter(c=>c.estado==='ACTIVO'); if(this.data.variant){const p=this.products.find(x=>x.nombre===this.data.variant?.producto);const s=this.sizes.find(x=>x.nombre===this.data.variant?.talla);const c=this.colors.find(x=>x.nombre===this.data.variant?.color);this.form.patchValue({id_producto:p?.id_producto??0,id_talla:s?.id_talla??0,id_color:c?.id_color??0});}},error:()=>this.snack.open('No fue posible cargar los catálogos','Cerrar',{duration:5000})}); }
  suggestSku(): void { if(this.data.variant || this.form.controls.sku.dirty) return; const p=this.products.find(x=>x.id_producto===this.form.controls.id_producto.value)?.nombre; const s=this.sizes.find(x=>x.id_talla===this.form.controls.id_talla.value)?.nombre; const c=this.colors.find(x=>x.id_color===this.form.controls.id_color.value)?.nombre; if(p&&s&&c)this.form.controls.sku.setValue(`${p}-${s}-${c}`.toUpperCase().replace(/[^A-Z0-9]+/g,'-').replace(/(^-|-$)/g,'')); }

  save(): void {
    if (this.form.invalid) { this.form.markAllAsTouched(); return; }
    this.saving = true;
    const raw = this.form.getRawValue(); const value: VariantRequest = {sku:raw.sku,id_talla:raw.id_talla,id_color:raw.id_color};
    const request = this.data.variant ? this.service.update(this.data.variant.id_variante, value) : this.service.create(raw.id_producto, value);
    request.subscribe({
      next: (variant) => { this.saving = false; this.ref?.close(variant); },
      error: (error: { error?: { message?: string } }) => {
        this.saving = false;
        this.snack.open(error.error?.message ?? 'No fue posible guardar la variante', 'Cerrar', { duration: 5000 });
      }
    });
  }
}
