import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NEVER, of } from 'rxjs';
import { AdminReportService } from '../../services/admin-report.service';
import { AiReportPanelComponent } from './ai-report-panel.component';

describe('AiReportPanelComponent', () => {
  let fixture: ComponentFixture<AiReportPanelComponent>;
  let reports: jasmine.SpyObj<AdminReportService>;

  beforeEach(async () => {
    reports = jasmine.createSpyObj<AdminReportService>('AdminReportService', [
      'getFeatures', 'getBranches', 'generateAiReport', 'exportAiReport',
    ]);
    reports.getFeatures.and.returnValue(of({
      reportes_ia: true,
      reportes_voz: false,
      comparacion_sucursales: false,
      exportacion_pdf_excel: true,
    }));
    reports.getBranches.and.returnValue(of([{ id_sucursal: 7, nombre: 'Central' }]));
    reports.generateAiReport.and.returnValue(of({
      tipo: 'ventas',
      periodo: { desde: '2026-11-01', hasta: '2026-11-05' },
      metricas_calculadas: { ventas_pagadas: '450.00', pedidos_pagados: 3 },
      observaciones_ia: ['Se registraron ventas en el per\u00edodo.'],
      recomendaciones_ia: ['Revisa el comportamiento en el siguiente per\u00edodo.'],
    }));
    reports.exportAiReport.and.returnValue(NEVER);
    await TestBed.configureTestingModule({ imports: [AiReportPanelComponent] })
      .overrideComponent(AiReportPanelComponent, {
        set: { providers: [{ provide: AdminReportService, useValue: reports }] },
      })
      .compileComponents();
    fixture = TestBed.createComponent(AiReportPanelComponent);
  });

  it('renders calculated data separately from AI recommendations and respects plan features', () => {
    fixture.detectChanges();
    fixture.componentInstance.generate();
    fixture.detectChanges();
    const text = fixture.nativeElement.textContent as string;
    expect(text).toContain('M\u00e9tricas calculadas');
    expect(text).toContain('Observaciones de Groq');
    expect(text).toContain('Recomendaciones generadas por IA');
    expect(text).not.toContain('Consultar por voz');
    expect(text).not.toContain('Rendimiento de sucursales');
  });

  it('submits selected filters and renders the period returned by the server', () => {
    fixture.detectChanges();
    const component = fixture.componentInstance;
    component.selectedBranch = '7';
    component.question = 'Resume ventas';
    component.generate('texto');
    fixture.detectChanges();

    expect(reports.generateAiReport).toHaveBeenCalledWith(jasmine.objectContaining({
      tipo: 'ventas',
      id_sucursal: 7,
      consulta: 'Resume ventas',
      canal: 'texto',
    }));
    expect(fixture.nativeElement.textContent).toContain('2026-11-01 \u2014 2026-11-05');
    expect(fixture.nativeElement.textContent).toContain('450.00');
  });

  it('exports the report using the exact filters used to generate it', () => {
    fixture.detectChanges();
    const component = fixture.componentInstance;
    component.selectedType = 'productos';
    component.dateFrom = '2026-11-01';
    component.dateTo = '2026-11-05';
    component.selectedBranch = '7';
    component.generate('texto');
    component.dateFrom = '2026-10-01';
    component.exportReport('pdf');

    expect(reports.exportAiReport).toHaveBeenCalledWith(jasmine.objectContaining({
      tipo: 'productos',
      fecha_inicio: '2026-11-01',
      fecha_fin: '2026-11-05',
      id_sucursal: 7,
    }), 'pdf');
  });

  it('keeps calculated metrics visible when AI analysis is unavailable', () => {
    reports.generateAiReport.and.returnValue(of({
      tipo: 'ventas',
      periodo: { desde: '2026-11-01', hasta: '2026-11-05' },
      metricas_calculadas: { ventas_pagadas: '450.00' },
      observaciones_ia: [],
      recomendaciones_ia: [],
      error_ia: 'La integración de IA de plataforma no está configurada.',
    }));
    fixture.detectChanges();
    fixture.componentInstance.generate();
    fixture.detectChanges();

    expect(fixture.nativeElement.textContent).toContain('450.00');
    expect(fixture.nativeElement.textContent).toContain('no se pudo completar el análisis de IA');
  });
});
