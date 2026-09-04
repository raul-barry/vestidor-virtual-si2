import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { Router } from '@angular/router';
import { ProductCardComponent } from './product-card.component';

describe('ProductCardComponent', () => {
  let component: ProductCardComponent;
  let fixture: ComponentFixture<ProductCardComponent>;
  let router: jasmine.SpyObj<Router>;

  beforeEach(async () => {
    router = jasmine.createSpyObj<Router>('Router', ['navigate']);
    await TestBed.configureTestingModule({
      imports: [ProductCardComponent, NoopAnimationsModule],
      providers: [{ provide: Router, useValue: router }]
    }).compileComponents();

    fixture = TestBed.createComponent(ProductCardComponent);
    component = fixture.componentInstance;
    component.producto = {
      id_producto: 1,
      nombre: 'Camisa Oxford',
      descripcion: 'Camisa formal masculina',
      precio_base: '250.00',
      estado: 'ACTIVO',
      categoria: { id_categoria: 1, nombre: 'Camisas' },
      variantes: [{ id_variante: 1, sku: 'CAM-M-BLA', talla: 'M', color: 'Blanco' }]
    };
    fixture.detectChanges();
  });

  it('renders product information', () => {
    expect(fixture.nativeElement.textContent).toContain('Camisa Oxford');
    expect(fixture.nativeElement.textContent).toContain('Camisas');
    expect(fixture.nativeElement.textContent).toContain('1 variantes');
  });

  it('navigates to the product detail', () => {
    component.openProduct();

    expect(router.navigate).toHaveBeenCalledWith(['/catalog/product', 1]);
  });
});
