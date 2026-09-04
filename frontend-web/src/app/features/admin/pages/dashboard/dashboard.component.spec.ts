import { ComponentFixture, TestBed } from '@angular/core/testing';
import { MatSnackBar } from '@angular/material/snack-bar';
import { of, throwError } from 'rxjs';
import { AdminReportService } from '../../services/admin-report.service';
import { DashboardComponent } from './dashboard.component';

describe('DashboardComponent', () => {
  let fixture: ComponentFixture<DashboardComponent>;
  let reportService: jasmine.SpyObj<AdminReportService>;
  let snackBar: jasmine.SpyObj<MatSnackBar>;

  beforeEach(async () => {
    reportService = jasmine.createSpyObj<AdminReportService>('AdminReportService', [
      'getDashboard', 'getSales', 'getTopProducts', 'getTopCategories', 'getInventory', 'getCustomers'
    ]);
    snackBar = jasmine.createSpyObj<MatSnackBar>('MatSnackBar', ['open']);
    reportService.getDashboard.and.returnValue(of({ usuarios_totales: 12, clientes_totales: 10, productos_totales: 24, pedidos_totales: 8, ventas_totales: '1500.00', productos_stock_bajo: 2 }));
    reportService.getSales.and.returnValue(of({ ventas_totales: '1500.00', cantidad_pedidos: 8, promedio_compra: '187.50', pedidos_por_estado: { CONFIRMADO: 8 } }));
    reportService.getTopProducts.and.returnValue(of([{ producto: 'Camisa Oxford', cantidad_vendida: 8, ingresos_generados: '1500.00' }]));
    reportService.getTopCategories.and.returnValue(of([{ categoria: 'Camisas', cantidad_vendida: 8, ventas_generadas: '1500.00' }]));
    reportService.getInventory.and.returnValue(of({ stock_total: 80, productos_stock_bajo: 2, productos_sin_stock: 0, movimientos_recientes: [] }));
    reportService.getCustomers.and.returnValue(of({ usuarios_registrados: 12, clientes_activos: 10, clientes_nuevos_mes: 2, clientes_con_compras: 8 }));
    await TestBed.configureTestingModule({
      imports: [DashboardComponent],
      providers: [
        { provide: AdminReportService, useValue: reportService },
        { provide: MatSnackBar, useValue: snackBar }
      ]
    }).overrideComponent(DashboardComponent, {
      set: { providers: [{ provide: MatSnackBar, useValue: snackBar }] }
    }).compileComponents();
    fixture = TestBed.createComponent(DashboardComponent);
  });

  it('loads and renders dashboard metric cards', () => {
    fixture.detectChanges();
    const content = fixture.nativeElement.textContent;
    expect(reportService.getDashboard).toHaveBeenCalled();
    expect(content).toContain('Usuarios totales');
    expect(content).toContain('Clientes');
    expect(content).toContain('Productos');
    expect(content).toContain('Pedidos');
    expect(content).toContain('Ventas');
    expect(content).toContain('Stock bajo');
  });

  it('renders chart components', () => {
    fixture.detectChanges();

    expect(fixture.nativeElement.querySelector('app-sales-chart')).not.toBeNull();
    expect(fixture.nativeElement.querySelector('app-top-products-chart')).not.toBeNull();
    expect(fixture.nativeElement.querySelector('app-category-chart')).not.toBeNull();
  });

  it('handles report API errors', () => {
    reportService.getDashboard.and.returnValue(throwError(() => new Error('Network error')));
    fixture.detectChanges();

    expect(snackBar.open).toHaveBeenCalledWith('No fue posible cargar los reportes', 'Cerrar', { duration: 5000 });
  });
});
