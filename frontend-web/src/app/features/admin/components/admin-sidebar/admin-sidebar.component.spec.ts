import { ComponentFixture, TestBed } from '@angular/core/testing';
import { RouterTestingModule } from '@angular/router/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { AdminSidebarComponent } from './admin-sidebar.component';
import { AdminReportService } from '../../services/admin-report.service';
import { of } from 'rxjs';

describe('AdminSidebarComponent', () => {
  let fixture: ComponentFixture<AdminSidebarComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AdminSidebarComponent, RouterTestingModule, NoopAnimationsModule],
      providers: [{ provide: AdminReportService, useValue: jasmine.createSpyObj('AdminReportService', ['getBranchComparisonAccess']) }]
    }).compileComponents();
    fixture = TestBed.createComponent(AdminSidebarComponent);
    fixture.detectChanges();
  });

  it('shows administrative navigation options', () => {
    const content = fixture.nativeElement.textContent;
    expect(content).toContain('Dashboard');
    expect(content).toContain('Productos');
    expect(content).toContain('Inventario');
    expect(content).toContain('Reportes');
  });

  it('shows comparison navigation to an assigned manager only after backend authorization', () => {
    const reports = TestBed.inject(AdminReportService) as jasmine.SpyObj<AdminReportService>;
    reports.getBranchComparisonAccess.and.returnValue(of({ comparacion_sucursales: true, exportacion_pdf_excel: true }));
    fixture.componentInstance.role = 'ENCARGADO_SUCURSAL';
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('Comparación por sucursal');
  });

  it('does not show comparison navigation when the backend denies access', () => {
    const reports = TestBed.inject(AdminReportService) as jasmine.SpyObj<AdminReportService>;
    reports.getBranchComparisonAccess.and.returnValue(of({ comparacion_sucursales: false, exportacion_pdf_excel: false }));
    fixture.componentInstance.role = 'ENCARGADO_SUCURSAL';
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).not.toContain('Comparación por sucursal');
  });
});
