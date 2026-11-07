import { TestBed } from '@angular/core/testing';
import { of } from 'rxjs';
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
});
