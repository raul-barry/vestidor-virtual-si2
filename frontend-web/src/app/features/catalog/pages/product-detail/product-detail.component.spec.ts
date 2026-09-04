import { ComponentFixture, TestBed } from '@angular/core/testing';
import { MatSnackBar } from '@angular/material/snack-bar';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { ActivatedRoute, convertToParamMap } from '@angular/router';
import { of, throwError } from 'rxjs';
import { CatalogService } from '../../services/catalog.service';
import { CartService } from '../../../cart/services/cart.service';
import { ProductDetailComponent } from './product-detail.component';

describe('ProductDetailComponent', () => {
  let component: ProductDetailComponent;
  let fixture: ComponentFixture<ProductDetailComponent>;
  let catalogService: jasmine.SpyObj<CatalogService>;
  let cartService: jasmine.SpyObj<CartService>;
  let snackBar: jasmine.SpyObj<MatSnackBar>;

  beforeEach(async () => {
    catalogService = jasmine.createSpyObj<CatalogService>('CatalogService', [
      'getProductVariants',
      'getProductAvailability'
    ]);
    cartService = jasmine.createSpyObj<CartService>('CartService', ['addItem']);
    snackBar = jasmine.createSpyObj<MatSnackBar>('MatSnackBar', ['open']);

    TestBed.configureTestingModule({
      imports: [ProductDetailComponent, NoopAnimationsModule],
      providers: [
        { provide: CatalogService, useValue: catalogService },
        { provide: CartService, useValue: cartService },
        { provide: MatSnackBar, useValue: snackBar },
        { provide: ActivatedRoute, useValue: { snapshot: { paramMap: convertToParamMap({ id: '1' }) } } }
      ]
    }).overrideComponent(ProductDetailComponent, {
      set: { providers: [{ provide: MatSnackBar, useValue: snackBar }] }
    });

    await TestBed.compileComponents();
  });

  it('loads variants and availability', () => {
    catalogService.getProductVariants.and.returnValue(of({
      id_producto: 1,
      nombre_producto: 'Camisa Oxford',
      tallas: ['M'],
      colores: ['Blanco'],
      variantes: [{ id_variante: 1, sku: 'OXF-M-BLA', talla: 'M', color: 'Blanco' }]
    }));
    catalogService.getProductAvailability.and.returnValue(of({
      id_producto: 1,
      nombre_producto: 'Camisa Oxford',
      disponibilidad: []
    }));
    fixture = TestBed.createComponent(ProductDetailComponent);
    component = fixture.componentInstance;

    fixture.detectChanges();

    expect(catalogService.getProductVariants).toHaveBeenCalledWith(1);
    expect(catalogService.getProductAvailability).toHaveBeenCalledWith(1);
    expect(component.variants?.nombre_producto).toBe('Camisa Oxford');
  });

  it('shows an error when a detail request fails', () => {
    catalogService.getProductVariants.and.returnValue(throwError(() => new Error('Network error')));
    catalogService.getProductAvailability.and.returnValue(of({
      id_producto: 1,
      nombre_producto: 'Camisa Oxford',
      disponibilidad: []
    }));
    fixture = TestBed.createComponent(ProductDetailComponent);
    component = fixture.componentInstance;

    fixture.detectChanges();

    expect(snackBar.open).toHaveBeenCalledWith('No fue posible cargar el detalle del producto', 'Cerrar', {
      duration: 5000
    });
  });
});
