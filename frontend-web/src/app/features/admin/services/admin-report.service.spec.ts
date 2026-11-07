import { of } from 'rxjs';
import { ApiService } from '../../../core/services/api.service';
import { AdminReportService } from './admin-report.service';

describe('AdminReportService', () => {
  it('loads report features and branches from tenant-scoped admin endpoints', () => {
    const api = jasmine.createSpyObj<ApiService>('ApiService', ['get', 'post']);
    api.get.and.returnValue(of([]));
    const service = new AdminReportService(api);

    service.getFeatures().subscribe();
    service.getBranches().subscribe();

    expect(api.get).toHaveBeenCalledWith('/api/admin/reports/features');
    expect(api.get).toHaveBeenCalledWith('/api/admin/reports/branches');
  });

  it('sends report filters and identifies voice input explicitly', () => {
    const api = jasmine.createSpyObj<ApiService>('ApiService', ['get', 'post']);
    api.post.and.returnValue(of({}));
    const service = new AdminReportService(api);
    const request = {
      tipo: 'ventas' as const,
      fecha_inicio: '2026-11-01',
      fecha_fin: '2026-11-05',
      id_sucursal: 4,
      consulta: 'Compara las ventas',
      canal: 'voz' as const,
    };

    service.generateAiReport(request).subscribe();

    expect(api.post).toHaveBeenCalledWith('/api/admin/reports/ai', request);
  });

  it('requests downloadable files from the authenticated report export endpoint', () => {
    const api = jasmine.createSpyObj<ApiService>('ApiService', ['get', 'post', 'postBlob']);
    api.postBlob.and.returnValue(of(new Blob(['file'])));
    const service = new AdminReportService(api);
    const request = {
      tipo: 'ventas' as const,
      fecha_inicio: '2026-11-01',
      fecha_fin: '2026-11-05',
      id_sucursal: 4,
      consulta: '',
      canal: 'texto' as const,
    };

    service.exportAiReport(request, 'xlsx').subscribe();

    expect(api.postBlob).toHaveBeenCalledWith('/api/admin/reports/export/xlsx', request);
  });
});
