import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { CartItemComponent } from './cart-item.component';

describe('CartItemComponent', () => {
  let component: CartItemComponent;
  let fixture: ComponentFixture<CartItemComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [CartItemComponent, NoopAnimationsModule]
    }).compileComponents();
    fixture = TestBed.createComponent(CartItemComponent);
    component = fixture.componentInstance;
    component.item = {
      id_detalle: 1,
      producto: 'Camisa Oxford',
      talla: 'M',
      color: 'Blanco',
      cantidad: 2,
      precio_unitario: '250.00'
    };
    fixture.detectChanges();
  });

  it('renders cart item data', () => {
    expect(fixture.nativeElement.textContent).toContain('Camisa Oxford');
    expect(fixture.nativeElement.textContent).toContain('M · Blanco');
  });

  it('emits the next quantity when increasing', () => {
    const emitSpy = spyOn(component.quantityChange, 'emit');

    component.increase();

    expect(emitSpy).toHaveBeenCalledWith(3);
  });

  it('emits removal from the action', () => {
    const emitSpy = spyOn(component.itemRemoved, 'emit');
    component.itemRemoved.emit();

    expect(emitSpy).toHaveBeenCalled();
  });
});
