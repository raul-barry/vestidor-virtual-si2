import { ComponentFixture, TestBed } from '@angular/core/testing';
import { MatSnackBar } from '@angular/material/snack-bar';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { ActivatedRoute, Router, convertToParamMap } from '@angular/router';
import { of, throwError } from 'rxjs';
import { OrderService } from '../../services/order.service';
import { OrderDetailComponent } from './order-detail.component';

describe('OrderDetailComponent', () => {
  let component: OrderDetailComponent;
  let fixture: ComponentFixture<OrderDetailComponent>;
  let orderService: jasmine.SpyObj<OrderService>;
  let snackBar: jasmine.SpyObj<MatSnackBar>;

  beforeEach(async () => {
    orderService = jasmine.createSpyObj<OrderService>('OrderService', ['getOrderDetail']);
    snackBar = jasmine.createSpyObj<MatSnackBar>('MatSnackBar', ['open']);
    TestBed.configureTestingModule({
      imports: [OrderDetailComponent, NoopAnimationsModule],
      providers: [
        { provide: OrderService, useValue: orderService },
        { provide: MatSnackBar, useValue: snackBar },
        { provide: Router, useValue: jasmine.createSpyObj<Router>('Router', ['navigate']) },
        { provide: ActivatedRoute, useValue: { snapshot: { paramMap: convertToParamMap({ id: '1' }) } } }
      ]
    }).overrideComponent(OrderDetailComponent, {
      set: { providers: [{ provide: MatSnackBar, useValue: snackBar }] }
    });
    await TestBed.compileComponents();
  });

  it('loads order detail', () => {
    orderService.getOrderDetail.and.returnValue(of({
      id_pedido: 1,
      fecha_pedido: '2026-09-02T00:00:00Z',
      estado: 'PENDIENTE',
      total: '500.00',
      detalles: [{ producto: 'Camisa Oxford', talla: 'M', color: 'Blanco', cantidad: 2, precio_unitario: '250.00' }]
    }));
    fixture = TestBed.createComponent(OrderDetailComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();

    expect(component.order?.detalles).toHaveSize(1);
    expect(orderService.getOrderDetail).toHaveBeenCalledWith(1);
  });

  it('handles a detail API error', () => {
    orderService.getOrderDetail.and.returnValue(throwError(() => ({ status: 404 })));
    fixture = TestBed.createComponent(OrderDetailComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();

    expect(component.isNotFound).toBeTrue();
    expect(snackBar.open).toHaveBeenCalled();
  });
});
