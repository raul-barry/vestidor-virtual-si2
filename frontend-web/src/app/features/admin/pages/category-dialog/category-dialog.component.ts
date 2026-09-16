import { Component, Inject, inject } from '@angular/core';
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';
import { NonNullableFormBuilder, Validators } from '@angular/forms';
import { ReactiveFormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatDialogModule } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';

@Component({
  selector: 'app-category-dialog',
  standalone: true,
  imports: [ReactiveFormsModule, MatButtonModule, MatDialogModule, MatFormFieldModule, MatInputModule],
  template: `<h2 mat-dialog-title>{{data?.id_categoria ? 'Editar' : 'Crear'} categoría</h2><form [formGroup]="form" (ngSubmit)="save()" mat-dialog-content><mat-form-field><mat-label>Nombre</mat-label><input matInput formControlName="nombre"></mat-form-field><mat-form-field><mat-label>Descripción</mat-label><input matInput formControlName="descripcion"></mat-form-field><div mat-dialog-actions align="end"><button mat-button mat-dialog-close type="button">Cancelar</button><button mat-flat-button color="primary" [disabled]="form.invalid">Guardar</button></div></form>`
})
export class CategoryDialogComponent {
  private ref = inject(MatDialogRef<CategoryDialogComponent>);
  form = inject(NonNullableFormBuilder).group({ nombre: ['', [Validators.required, Validators.minLength(1)]], descripcion: [''] });
  constructor(@Inject(MAT_DIALOG_DATA) public data: any) { if (data) this.form.patchValue(data); }
  save(): void { this.ref.close(this.form.getRawValue()); }
}