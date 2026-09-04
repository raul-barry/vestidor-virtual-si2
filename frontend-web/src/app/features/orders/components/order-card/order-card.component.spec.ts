import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { OrderCardComponent } from './order-card.component';

describe('OrderCardComponent', () => {
  let component: OrderCardComponent;
  let fixture: ComponentFixture<OrderCardComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [OrderCardComponent, NoopAnimationsModule]
    }).compileComponents();
    fixture = TestBed.createComponent(OrderCardComponent);
    component = fixture.componentInstance;
    component.order = {
      id_pedido: 1,
      fecha_pedido: '2026-09-02T00:00:00Z',
      estado: 'PENDIENTE',
      total: '500.00'
    };
    fixture.detectChanges();
  });

  it('renders order information', () => {
    expect(fixture.nativeElement.textContent).toContain('PEDIDO #1');
    expect(fixture.nativeElement.textContent).toContain('PENDIENTE');
    expect(fixture.nativeElement.textContent).toContain('500.00');
  });
});
