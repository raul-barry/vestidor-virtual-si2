import { Component, Inject, OnInit, inject } from '@angular/core';
import { NonNullableFormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { Supplier, SupplierRequest } from '../../models/commercial-master.model';
import { CommercialMasterAdminService } from '../../services/commercial-master-admin.service';

@Component({
  standalone: true,
  imports: [ReactiveFormsModule, MatDialogModule, MatButtonModule, MatFormFieldModule, MatInputModule, MatSelectModule],
  template: `
    <h2 mat-dialog-title>{{ data ? 'Editar proveedor' : 'Nuevo proveedor' }}</h2>
    <mat-dialog-content>
      <form id="supplier-form" [formGroup]="form" (ngSubmit)="submit()" class="grid">
        <mat-form-field class="wide"><mat-label>Razón social / empresa</mat-label><input matInput formControlName="nombre"><mat-error>Campo requerido</mat-error></mat-form-field>
        <mat-form-field class="wide"><mat-label>Descripción</mat-label><textarea matInput formControlName="descripcion"></textarea></mat-form-field>
        <mat-form-field><mat-label>Persona de contacto</mat-label><input matInput formControlName="persona_contacto"></mat-form-field>
        <mat-form-field><mat-label>Teléfono</mat-label><input matInput formControlName="telefono"></mat-form-field>
        <mat-form-field><mat-label>Correo</mat-label><input matInput type="email" formControlName="correo"><mat-error>Correo no válido</mat-error></mat-form-field>
        <mat-form-field><mat-label>Estado</mat-label><mat-select formControlName="estado"><mat-option value="ACTIVO">Activo</mat-option><mat-option value="INACTIVO">Inactivo</mat-option></mat-select></mat-form-field>
        <mat-form-field class="wide"><mat-label>Dirección (opcional)</mat-label><input matInput formControlName="direccion"></mat-form-field>
        <mat-form-field class="wide"><mat-label>Productos que proporciona</mat-label><mat-select formControlName="id_productos" multiple>@for (product of availableProducts; track product.id_producto) { <mat-option [value]="product.id_producto">{{ product.nombre }}</mat-option> }</mat-select><mat-hint>Selecciona uno o más productos.</mat-hint></mat-form-field>
      </form>
    </mat-dialog-content>
    <mat-dialog-actions align="end"><button mat-button mat-dialog-close>Cancelar</button><button mat-flat-button color="primary" form="supplier-form" [disabled]="form.invalid">Guardar</button></mat-dialog-actions>
  `,
  styles: ['.grid{display:grid;grid-template-columns:1fr 1fr;gap:.5rem;min-width:min(42rem,75vw)}.wide{grid-column:1/-1}@media(max-width:650px){.grid{grid-template-columns:1fr;min-width:0}.wide{grid-column:auto}}']
})
export class SupplierDialogComponent implements OnInit {
  private fb = inject(NonNullableFormBuilder);
  private service = inject(CommercialMasterAdminService);
  availableProducts: Array<{ id_producto: number; nombre: string }> = [];
  form = this.fb.group({
    nombre: [this.data?.nombre ?? '', [Validators.required, Validators.maxLength(150)]],
    descripcion: [this.data?.descripcion ?? '', Validators.maxLength(500)],
    persona_contacto: [this.data?.persona_contacto ?? '', Validators.maxLength(150)],
    telefono: [this.data?.telefono ?? '', Validators.maxLength(30)],
    correo: [this.data?.correo ?? '', [Validators.email, Validators.maxLength(255)]],
    direccion: [this.data?.direccion ?? '', Validators.maxLength(255)],
    estado: [this.data?.estado ?? 'ACTIVO' as const],
    id_productos: [this.data?.productos.map(product => product.id_producto) ?? []]
  });

  constructor(@Inject(MAT_DIALOG_DATA) public data: Supplier | null, private ref: MatDialogRef<SupplierDialogComponent>) {}

  ngOnInit(): void {
    this.service.listProducts().subscribe({
      next: products => {
        const currentSupplier = this.data?.id_proveedor;
        this.availableProducts = products.filter(product => !product.id_proveedor || product.id_proveedor === currentSupplier);
      }
    });
  }

  submit(): void {
    if (this.form.invalid) { this.form.markAllAsTouched(); return; }
    this.ref.close(this.form.getRawValue() as SupplierRequest);
  }
}
