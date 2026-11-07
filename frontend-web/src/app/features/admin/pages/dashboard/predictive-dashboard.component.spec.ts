import { ComponentFixture, TestBed } from '@angular/core/testing';
import { of } from 'rxjs';
import { AdminReportService } from '../../services/admin-report.service';
import { PredictiveDashboardComponent } from './predictive-dashboard.component';

describe('PredictiveDashboardComponent', () => {
  let fixture: ComponentFixture<PredictiveDashboardComponent>;
  let reports: jasmine.SpyObj<AdminReportService>;

  beforeEach(async () => {
    reports = jasmine.createSpyObj<AdminReportService>('AdminReportService', [
      'getPredictiveFeatures', 'getBranches', 'getPredictiveDashboard',
      'getPredictiveHistory', 'getCustomerSegments',
    ]);
    reports.getPredictiveFeatures.and.returnValue(of({
      machine_learning: true,
      prediccion_demanda: true,
      segmentacion_kmeans: true,
      dashboard_predictivo: true,
    }));
    reports.getBranches.and.returnValue(of([{ id_sucursal: 3, nombre: 'Central' }]));
    reports.getPredictiveDashboard.and.returnValue(of({
      periodo: { desde: '2026-09-01', hasta: '2026-11-05' },
      modelo: { version: 'weekly-v1', actualizado_en: '2026-11-05T10:00:00Z', metodo: 'test', minimo_dias_historicos: 42 },
      evaluacion: { productos_evaluados: 1, mae_unidades: 1.2, wape_porcentaje: 12, metodo: 'backtest' },
      tendencia_historica_semanal: [{ semana_desde: '2026-10-26', unidades_vendidas: 14 }],
      predicciones: [{
        producto_id: 8, producto: 'Camisa', sucursal_id: 3, sucursal: 'Central',
        estado_modelo: 'evaluado', stock_disponible: 3, tendencia: 'creciente',
        riesgo_inventario: 'posible_agotamiento',
        prediccion_7_dias: { demanda_esperada: 7, demanda_diaria: [1, 1, 1, 1, 1, 1, 1], desde: '2026-11-06', hasta: '2026-11-12' },
        evaluacion: { mae: 1, wape_porcentaje: 10 },
      }],
      productos_con_datos_insuficientes: 0,
    }));
    reports.getPredictiveHistory.and.returnValue(of({
      periodo_evaluado: { desde: '2026-09-01', hasta: '2026-11-05' },
      nota: 'backtest reconstruido',
      resultados: [{
        producto_id: 8, producto: 'Camisa', sucursal_id: 3, sucursal: 'Central',
        periodo: { desde: '2026-10-27', hasta: '2026-11-02' },
        demanda_predicha: 6, demanda_real: 7, error_absoluto: 1,
        tipo_resultado: 'backtest_reconstruido',
      }],
    }));
    reports.getCustomerSegments.and.returnValue(of({
      estado: 'calculado', clientes_analizados: 8,
      variables: ['compras_pagadas', 'gasto_pagado', 'dias_desde_ultima_compra'],
      algoritmo: 'K-Means', k: 2, indice_davies_bouldin: 0.42,
      actualizado_en: '2026-11-05T10:00:00Z',
      segmentos: [{
        segmento: 1, clientes: 4, caracteristicas: ['compra reciente'],
        promedios: { compras_pagadas: 2, gasto_pagado: 300, dias_desde_ultima_compra: 5 },
      }],
    }));
    await TestBed.configureTestingModule({ imports: [PredictiveDashboardComponent] })
      .overrideComponent(PredictiveDashboardComponent, {
        set: { providers: [{ provide: AdminReportService, useValue: reports }] },
      })
      .compileComponents();
    fixture = TestBed.createComponent(PredictiveDashboardComponent);
  });

  it('shows forecast, historical comparison, evaluation and tenant segments', () => {
    fixture.detectChanges();
    fixture.detectChanges();
    const text = fixture.nativeElement.textContent as string;
    expect(text).toContain('Dashboard predictivo');
    expect(text).toContain('Demanda (7 días)');
    expect(text).toContain('MAE');
    expect(text).toContain('Backtest histórico');
    expect(text).toContain('Segmentación de clientes (K-Means)');
    expect(text).toContain('posible_agotamiento');
  });

  it('passes selected branch and product filters into recalculation', () => {
    fixture.detectChanges();
    fixture.detectChanges();
    const component = fixture.componentInstance;
    component.selectedBranch = '3';
    component.selectedProduct = '8';
    component.refresh();
    expect(reports.getPredictiveDashboard).toHaveBeenCalledWith(jasmine.objectContaining({
      id_sucursal: 3,
      id_producto: 8,
    }));
  });
});
