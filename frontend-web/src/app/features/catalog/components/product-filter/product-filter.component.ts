import { Component, EventEmitter, Input, Output, inject } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { ProductSearchFilters } from '../../services/catalog.service';

@Component({
  selector: 'app-product-filter',
  standalone: true,
  imports: [ReactiveFormsModule, MatButtonModule, MatFormFieldModule, MatInputModule, MatSelectModule],
  templateUrl: './product-filter.component.html',
  styleUrl: './product-filter.component.scss'
})
export class ProductFilterComponent {
  private readonly formBuilder = inject(FormBuilder);

  @Input() categorias: string[] = [];
  @Input() tallas: string[] = [];
  @Input() colores: string[] = [];
  @Output() readonly filtersChange = new EventEmitter<ProductSearchFilters>();

  readonly filterForm = this.formBuilder.group({
    nombre: [''],
    categoria: [''],
    talla: [''],
    color: [''],
    precio_max: [null as number | null, [Validators.min(0.01)]]
  });

  submit(): void {
    if (this.filterForm.invalid) {
      this.filterForm.markAllAsTouched();
      return;
    }

    const values = this.filterForm.getRawValue();
    this.filtersChange.emit({
      nombre: values.nombre?.trim() || undefined,
      categoria: values.categoria || undefined,
      talla: values.talla || undefined,
      color: values.color || undefined,
      precio_max: values.precio_max ?? undefined
    });
  }

  clear(): void {
    this.filterForm.reset({ nombre: '', categoria: '', talla: '', color: '', precio_max: null });
    this.filtersChange.emit({});
  }
}
