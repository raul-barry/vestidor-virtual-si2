import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { VariantSelectorComponent } from './variant-selector.component';

describe('VariantSelectorComponent', () => {
  let component: VariantSelectorComponent;
  let fixture: ComponentFixture<VariantSelectorComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [VariantSelectorComponent, NoopAnimationsModule]
    }).compileComponents();

    fixture = TestBed.createComponent(VariantSelectorComponent);
    component = fixture.componentInstance;
    component.product = {
      id_producto: 1,
      nombre_producto: 'Camisa Oxford',
      tallas: ['M', 'L'],
      colores: ['Blanco', 'Azul'],
      variantes: [{ id_variante: 1, sku: 'OXF-M-BLA', talla: 'M', color: 'Blanco' }]
    };
    fixture.detectChanges();
  });

  it('renders available sizes and colors', () => {
    expect(fixture.nativeElement.textContent).toContain('M');
    expect(fixture.nativeElement.textContent).toContain('L');
    expect(fixture.nativeElement.textContent).toContain('Blanco');
    expect(fixture.nativeElement.textContent).toContain('Azul');
  });
});
