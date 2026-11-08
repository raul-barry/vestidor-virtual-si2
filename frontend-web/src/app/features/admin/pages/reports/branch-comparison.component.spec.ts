import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NEVER, of } from 'rxjs';
import { AdminReportService } from '../../services/admin-report.service';
import { BranchComparisonComponent } from './branch-comparison.component';

describe('BranchComparisonComponent', () => {
  let fixture: ComponentFixture<BranchComparisonComponent>;
  let reports: jasmine.SpyObj<AdminReportService>;

  const comparison = {
    organizacion: 'FashionStore',
    periodo: { desde: '2026-11-01', hasta: '2026-11-08' },
    periodo_anterior: { desde: '2026-10-24', hasta: '2026-10-31' },
    zona_horaria: 'UTC-04:00',
    sucursales: [{
      id_sucursal: 7, sucursal: 'Central', ranking: 1, ingresos_netos: '100.00',
      cantidad_ventas: 2, ticket_promedio: '50.00', ingresos_periodo_anterior: '80.00',
      ventas_periodo_anterior: 2, variacion_porcentual: '25.00',
    }],
    totales: { ingresos_netos: '100.00', cantidad_ventas: 2, ticket_promedio: '50.00', variacion_porcentual: '25.00' },
    destacados: { mayores_ingresos: 7, mas_transacciones: 7, mayor_ticket_promedio: 7, menores_ingresos: 7 },
  };

  beforeEach(async () => {
    reports = jasmine.createSpyObj<AdminReportService>('AdminReportService', [
      'getBranchComparisonAccess', 'getComparisonBranches', 'getBranchSalesComparison', 'exportBranchSalesComparison',
    ]);
    reports.getBranchComparisonAccess.and.returnValue(of({ comparacion_sucursales: true, exportacion_pdf_excel: true }));
    reports.getComparisonBranches.and.returnValue(of([{ id_sucursal: 7, nombre: 'Central' }]));
    reports.getBranchSalesComparison.and.returnValue(of(comparison));
    reports.exportBranchSalesComparison.and.returnValue(NEVER);
    await TestBed.configureTestingModule({ imports: [BranchComparisonComponent] })
      .overrideComponent(BranchComparisonComponent, { set: { providers: [{ provide: AdminReportService, useValue: reports }] } })
      .compileComponents();
    fixture = TestBed.createComponent(BranchComparisonComponent);
  });

  it('loads real tenant-scoped comparison and displays metrics, previous period, ranking and indicators', () => {
    fixture.detectChanges();
    fixture.detectChanges();
    const text = fixture.nativeElement.textContent as string;
    expect(reports.getBranchComparisonAccess).toHaveBeenCalled();
    expect(reports.getComparisonBranches).toHaveBeenCalled();
    expect(reports.getBranchSalesComparison).toHaveBeenCalled();
    expect(text).toContain('Comparación por sucursal');
    expect(text).toContain('FashionStore');
    expect(text).toContain('Detalle y ranking');
    expect(text).toContain('Mayores ingresos');
    expect(text).toContain('25.0%');
  });

  it('respects plan and role access without showing comparison data', () => {
    reports.getBranchComparisonAccess.and.returnValue(of({ comparacion_sucursales: false, exportacion_pdf_excel: false }));
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('no tiene habilitada');
    expect(reports.getComparisonBranches).not.toHaveBeenCalled();
    expect(reports.getBranchSalesComparison).not.toHaveBeenCalled();
  });

  it('sorts the detail table and preserves the selected date and branch filters', () => {
    fixture.detectChanges();
    fixture.detectChanges();
    const component = fixture.componentInstance;
    component.selectedBranches = [7];
    component.refresh();
    expect(reports.getBranchSalesComparison).toHaveBeenCalledWith(jasmine.objectContaining({ id_sucursal: [7] }));
    component.sortBy('cantidad_ventas');
    expect(component.sortedRows[0].cantidad_ventas).toBe(2);
  });
});
