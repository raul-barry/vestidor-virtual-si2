import { Component, Inject, Optional, inject } from '@angular/core';
import { NonNullableFormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { AdminVariant, VariantRequest } from '../../../models/variant-admin.model';
import { VariantAdminService } from '../../../services/variant-admin.service';

export interface VariantFormData { productId: number; variant?: AdminVariant; }

@Component({ selector:'app-variant-form', standalone:true, imports:[ReactiveFormsModule,MatButtonModule,MatDialogModule,MatFormFieldModule,MatInputModule,MatSnackBarModule], template:`<h2 mat-dialog-title>{{data.variant?'Editar variante':'Crear variante'}}</h2><form [formGroup]="form" (ngSubmit)="save()" mat-dialog-content><mat-form-field><mat-label>SKU</mat-label><input matInput formControlName="sku"><mat-error>SKU obligatorio</mat-error></mat-form-field><mat-form-field><mat-label>ID talla</mat-label><input matInput type="number" formControlName="id_talla"><mat-error>Talla obligatoria</mat-error></mat-form-field><mat-form-field><mat-label>ID color</mat-label><input matInput type="number" formControlName="id_color"><mat-error>Color obligatorio</mat-error></mat-form-field><div mat-dialog-actions align="end"><button mat-button type="button" mat-dialog-close>Cancelar</button><button mat-flat-button color="primary" [disabled]="form.invalid || saving">Guardar</button></div></form>`, styles:['form{display:grid;gap:.75rem}'] })
export class VariantFormComponent {
  private fb = inject(NonNullableFormBuilder);
  private service = inject(VariantAdminService);
  private snack = inject(MatSnackBar);
  saving = false;
  form = this.fb.group({
    sku: ['', Validators.required],
    id_talla: [0, [Validators.required, Validators.min(1)]],
    id_color: [0, [Validators.required, Validators.min(1)]]
  });

  constructor(@Inject(MAT_DIALOG_DATA) public data: VariantFormData, @Optional() private ref: MatDialogRef<VariantFormComponent> | null) {
    if (data.variant) this.form.patchValue({ sku: data.variant.sku });
  }

  save(): void {
    if (this.form.invalid) { this.form.markAllAsTouched(); return; }
    this.saving = true;
    const value = this.form.getRawValue() as VariantRequest;
    const request = this.data.variant ? this.service.update(this.data.variant.id_variante, value) : this.service.create(this.data.productId, value);
    request.subscribe({
      next: (variant) => { this.saving = false; this.ref?.close(variant); },
      error: (error: { error?: { message?: string } }) => {
        this.saving = false;
        this.snack.open(error.error?.message ?? 'No fue posible guardar la variante', 'Cerrar', { duration: 5000 });
      }
    });
  }
}
