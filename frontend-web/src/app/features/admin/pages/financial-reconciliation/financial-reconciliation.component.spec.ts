import { ComponentFixture, TestBed } from '@angular/core/testing';
import { of } from 'rxjs';
import { ApiService } from '../../../../core/services/api.service';
import { FinancialReconciliationComponent } from './financial-reconciliation.component';

describe('FinancialReconciliationComponent simulated payments', () => {
  let fixture: ComponentFixture<FinancialReconciliationComponent>;
  let api: jasmine.SpyObj<ApiService>;

  const simulated = {
    id_pago: 17, id_pedido: 29, metodo_pago: 'TARJETA', monto: '120.00',
    currency: 'BOB', estado: 'PENDIENTE', simulated: true,
  };
  const real = { ...simulated, id_pago: 18, simulated: false, proveedor: 'STRIPE' };

  beforeEach(async () => {
    api = jasmine.createSpyObj<ApiService>('ApiService', ['get', 'put']);
    api.get.and.returnValue(of({
      payments: [simulated, real], payment_history: [simulated, real],
      refunds: [], adjustments: [],
    }));
    api.put.and.returnValue(of(simulated));
    await TestBed.configureTestingModule({
      imports: [FinancialReconciliationComponent],
      providers: [{ provide: ApiService, useValue: api }],
    }).compileComponents();
    fixture = TestBed.createComponent(FinancialReconciliationComponent);
    fixture.detectChanges();
  });

  it('shows simulation controls only for a pending simulated payment', () => {
    const text = fixture.nativeElement.textContent as string;
    expect(text).toContain('Aprobar simulación');
    expect(text).toContain('Rechazar simulación');
    expect(fixture.componentInstance.canResolveSimulation(real)).toBeFalse();
    expect(fixture.componentInstance.canResolveSimulation({ ...simulated, estado: 'PAGADO' })).toBeFalse();
  });

  it('sends explicit approval or rejection to the backend after confirmation', () => {
    spyOn(window, 'confirm').and.returnValue(true);

    fixture.componentInstance.resolveSimulation(simulated, true);
    fixture.componentInstance.resolveSimulation(simulated, false);

    expect(api.put).toHaveBeenCalledWith('/api/payments/reconciliation/17/simulate', { approved: true });
    expect(api.put).toHaveBeenCalledWith('/api/payments/reconciliation/17/simulate', { approved: false });
  });

  it('does not send a request when the operator cancels confirmation', () => {
    spyOn(window, 'confirm').and.returnValue(false);

    fixture.componentInstance.resolveSimulation(simulated, true);

    expect(api.put).not.toHaveBeenCalled();
  });
});
