import { TestBed } from '@angular/core/testing';
import { of, throwError } from 'rxjs';
import { ApiService } from '../../../../core/services/api.service';
import { OutboxSyncService } from '../../../../core/services/outbox-sync.service';
import { ExchangeManagementComponent } from './exchange-management.component';

describe('ExchangeManagementComponent', () => {
  let api: jasmine.SpyObj<ApiService>;
  let outbox: jasmine.SpyObj<OutboxSyncService>;
  let component: ExchangeManagementComponent;

  beforeEach(() => {
    api = jasmine.createSpyObj<ApiService>('ApiService', ['get', 'post', 'put']);
    outbox = jasmine.createSpyObj<OutboxSyncService>('OutboxSyncService', ['cacheExchanges', 'cachedExchanges', 'queuePhysicalExchange']);
    outbox.cachedExchanges.and.resolveTo([]);
    outbox.cacheExchanges.and.resolveTo();
    outbox.queuePhysicalExchange.and.resolveTo({} as any);
    TestBed.configureTestingModule({ imports: [ExchangeManagementComponent], providers: [
      { provide: ApiService, useValue: api }, { provide: OutboxSyncService, useValue: outbox }
    ] });
    component = TestBed.createComponent(ExchangeManagementComponent).componentInstance;
  });

  it('loads tenant changes and inventory incidents from the administration API', async () => {
    api.get.and.returnValues(of([{ id: 3, state: 'SOLICITADO' }]), of([{ id: 9, state: 'INCIDENCIA_CONCILIACION' }]));
    await component.refresh();
    expect(component.rows[0].id).toBe(3);
    expect(component.incidents[0].id).toBe(9);
    expect(outbox.cacheExchanges).toHaveBeenCalledWith(component.rows);
  });

  it('submits inspection and substitution delivery without creating a sale', async () => {
    const changed = { id: 3, state: 'APROBADO', economic_difference: '0.00' };
    api.post.and.returnValue(of(changed));
    component.rows = [{ id: 3, state: 'SOLICITADO', branch_id: 2 }];
    component.good[3] = true;
    component.tag[3] = true;
    await component.inspect(component.rows[0], true);
    expect(api.post).toHaveBeenCalledWith('/api/admin/exchanges/3/inspection', jasmine.objectContaining({ aprobado: true, buen_estado: true, etiqueta_original: true }));
    expect(component.rows[0].state).toBe('APROBADO');
    api.post.and.returnValue(of({ ...changed, state: 'COMPLETADO' }));
    await component.deliver(component.rows[0]);
    expect(api.post).toHaveBeenCalledWith('/api/admin/exchanges/3/deliver', {});
    expect(component.rows[0].state).toBe('COMPLETADO');
  });

  it('keeps physical offline handover in the outbox and exposes incident reconciliation', async () => {
    const row = { id: 4, original_detail_id: 12, branch_id: 2, replacement_variant_id: 18, state: 'SOLICITADO' };
    component.rows = [row];
    component.good[4] = true;
    component.tag[4] = true;
    await component.recordPhysicalOffline(row);
    expect(outbox.queuePhysicalExchange).toHaveBeenCalledWith(row, jasmine.objectContaining({
      id_detalle: 12, id_sucursal: 2, id_variante_sustituta: 18,
      prenda_recibida: true, prenda_entregada: true
    }));
  });

  it('posts an authorized inventory adjustment for a physical shortage incident', async () => {
    api.post.and.returnValue(of({ state: 'CONCILIADA' }));
    component.actualStock[9] = 0;
    component.adjustmentReason[9] = 'Conteo físico confirmado';
    api.get.and.returnValues(of([]), of([]));
    await component.reconcile({ id: 9 });
    expect(api.post).toHaveBeenCalledWith('/api/admin/exchanges/incidents/9/reconcile', {
      stock_real: 0, motivo: 'Conteo físico confirmado'
    });
  });

  it('searches a sale and displays tenant sale details from the API', async () => {
    const sale = { codigo: 'PED-14', elegible: true, detalles: [{ id_detalle: 8, cantidad_disponible_para_cambio: 1 }] };
    api.get.and.returnValue(of(sale));
    component.saleCode = 'PED-14';
    await component.findSale();
    expect(api.get).toHaveBeenCalledWith('/api/admin/exchanges/sales/PED-14');
    expect(component.sale).toEqual(sale);
    expect(component.lookupError).toBe('');
  });

  it('registers the selected change once and keeps its receipt and refreshed sale', async () => {
    const sale = { codigo: 'PED-14', elegible: true, detalles: [] };
    const receipt = { id: 51, original_order_id: 14, state: 'COMPLETADO' };
    api.post.and.returnValue(of(receipt));
    api.get.and.callFake((path: string) => (path.includes('/sales/') ? of(sale) : of([])) as any);
    component.sale = { elegible: true };
    component.saleCode = 'PED-14';
    component.replacement[8] = 21;
    component.exchangeQuantity[8] = 1;
    component.reason[8] = 'Cambio de talla';
    const line = { id_detalle: 8, cantidad_disponible_para_cambio: 1 };

    const first = component.registerChange(line);
    await component.registerChange(line);
    await first;

    expect(api.post).toHaveBeenCalledTimes(1);
    expect(api.post).toHaveBeenCalledWith('/api/admin/exchanges/register', jasmine.objectContaining({
      id_detalle: 8, id_variante_sustituta: 21, cantidad: 1, motivo: 'Cambio de talla'
    }));
    expect(component.receipt).toEqual(receipt);
    expect(component.successMessage).toContain('registrado y guardado');
  });

  it('shows the server rejection without suggesting a successful change', async () => {
    api.post.and.returnValue(throwError(() => ({ error: { detail: 'El plazo de 7 días venció.' } })));
    component.sale = { elegible: true };
    component.saleCode = 'PED-14';
    component.replacement[8] = 21;
    component.reason[8] = 'Cambio de talla';
    await component.registerChange({ id_detalle: 8, cantidad_disponible_para_cambio: 1 });
    expect(component.lookupError).toBe('El plazo de 7 días venció.');
    expect(component.successMessage).toBe('');
    expect(component.receipt).toBeNull();
  });
});
