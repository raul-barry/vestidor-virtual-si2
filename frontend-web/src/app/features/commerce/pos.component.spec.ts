import { ComponentFixture, TestBed } from '@angular/core/testing';
import { of } from 'rxjs';
import { ApiService } from '../../core/services/api.service';
import { OutboxSyncService } from '../../core/services/outbox-sync.service';
import { PosComponent } from './pos.component';

describe('PosComponent offline sales', () => {
  let fixture: ComponentFixture<PosComponent>;
  let api: jasmine.SpyObj<ApiService>;
  let outbox: jasmine.SpyObj<OutboxSyncService>;
  let onlineSpy: jasmine.Spy;

  beforeEach(async () => {
    onlineSpy = spyOnProperty(navigator, 'onLine', 'get').and.returnValue(false);
    api = jasmine.createSpyObj<ApiService>('ApiService', ['get', 'post']);
    api.get.and.returnValue(of({ clientes: [], inventario: [] }) as any);
    outbox = jasmine.createSpyObj<OutboxSyncService>('OutboxSyncService', ['cachePosOptions', 'cachedPosOptions', 'queuePosCashSale']);
    outbox.cachedPosOptions.and.resolveTo({
      clientes: [{ id_cliente: 11, nombre: 'Cliente demo' }],
      inventario: [{ id_inventario: 21, id_variante: 31, id_sucursal: 41, sucursal: 'Central',
        producto: 'Camisa', talla: 'M', color: 'Azul', stock: 4, precio: '25.00' }]
    });
    outbox.queuePosCashSale.and.resolveTo({ operation_uuid: '12345678-1234-1234-1234-123456789abc' } as any);
    await TestBed.configureTestingModule({ imports: [PosComponent], providers: [
      { provide: ApiService, useValue: api }, { provide: OutboxSyncService, useValue: outbox }
    ] }).compileComponents();
    fixture = TestBed.createComponent(PosComponent);
  });

  it('queues cash sale locally with branch and variant scope when offline', async () => {
    const component = fixture.componentInstance;
    fixture.detectChanges();
    await fixture.whenStable();
    component.customerType = 'CONSUMIDOR_FINAL';
    component.branchId = 41;
    component.lines = [{ id_inventario: 21, id_variante: 31, id_sucursal: 41, cantidad: 1, precio: '25.00' }];
    component.cashReceived = 30;

    await component.sell();

    expect(outbox.queuePosCashSale).toHaveBeenCalledWith(jasmine.objectContaining({
      id_sucursal: 41, id_cliente: null, importe_recibido: 30,
      lineas: [{ id_variante: 31, cantidad: 1 }]
    }));
    expect(component.lines).toEqual([]);
    expect(component.message).toContain('pendiente');
  });

  it('does not queue QR or card payments while offline', async () => {
    const component = fixture.componentInstance;
    component.customerType = 'CONSUMIDOR_FINAL';
    component.branchId = 41;
    component.paymentMethod = 'QR';
    component.lines = [{ id_inventario: 21, id_variante: 31, id_sucursal: 41, cantidad: 1, precio: '25.00' }];

    await component.sell();

    expect(outbox.queuePosCashSale).not.toHaveBeenCalled();
    expect(component.message).toContain('solo admiten efectivo');
  });
});
