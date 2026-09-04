import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { ProductFilterComponent } from './product-filter.component';

describe('ProductFilterComponent', () => {
  let component: ProductFilterComponent;
  let fixture: ComponentFixture<ProductFilterComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ProductFilterComponent, NoopAnimationsModule]
    }).compileComponents();

    fixture = TestBed.createComponent(ProductFilterComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('emits selected filters when searching', () => {
    const emitSpy = spyOn(component.filtersChange, 'emit');
    component.filterForm.setValue({
      nombre: 'camisa',
      categoria: 'Camisas',
      talla: 'M',
      color: 'Blanco',
      precio_max: 300
    });

    component.submit();

    expect(emitSpy).toHaveBeenCalledWith({
      nombre: 'camisa',
      categoria: 'Camisas',
      talla: 'M',
      color: 'Blanco',
      precio_max: 300
    });
  });

  it('emits empty filters when clearing', () => {
    const emitSpy = spyOn(component.filtersChange, 'emit');

    component.clear();

    expect(emitSpy).toHaveBeenCalledWith({});
  });
});
