import { ComponentFixture, TestBed } from '@angular/core/testing';
import { MatSnackBar } from '@angular/material/snack-bar';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { Router } from '@angular/router';
import { of } from 'rxjs';
import { OrderService } from '../../services/order.service';
import { OrderHistoryComponent } from './order-history.component';

describe('OrderHistoryComponent', () => {
  let component: OrderHistoryComponent;
  let fixture: ComponentFixture<OrderHistoryComponent>;
  let orderService: jasmine.SpyObj<OrderService>;

  beforeEach(async () => {
    orderService = jasmine.createSpyObj<OrderService>('OrderService', ['getOrders']);
    await TestBed.configureTestingModule({
      imports: [OrderHistoryComponent, NoopAnimationsModule],
      providers: [
        { provide: OrderService, useValue: orderService },
        { provide: Router, useValue: jasmine.createSpyObj<Router>('Router', ['navigate']) },
        { provide: MatSnackBar, useValue: jasmine.createSpyObj<MatSnackBar>('MatSnackBar', ['open']) }
      ]
    }).compileComponents();
  });

  it('loads client orders', () => {
    orderService.getOrders.and.returnValue(of([{ id_pedido: 1, estado: 'PENDIENTE', total: '500.00' }]));
    fixture = TestBed.createComponent(OrderHistoryComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();

    expect(component.orders).toHaveSize(1);
  });

  it('handles an empty order list', () => {
    orderService.getOrders.and.returnValue(of([]));
    fixture = TestBed.createComponent(OrderHistoryComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();

    expect(component.orders).toEqual([]);
  });
});
