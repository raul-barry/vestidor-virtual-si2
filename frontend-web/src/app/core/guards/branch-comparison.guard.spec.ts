import { TestBed } from '@angular/core/testing';
import { Router } from '@angular/router';
import { AdminReportService } from '../../features/admin/services/admin-report.service';
import { BranchComparisonAccessCache } from '../services/branch-comparison-access-cache.service';
import { branchComparisonGuard } from './branch-comparison.guard';

describe('branchComparisonGuard offline navigation', () => {
  it('allows navigation offline only when this user and organization had access cached', () => {
    const reports = jasmine.createSpyObj<AdminReportService>('AdminReportService', ['getBranchComparisonAccess']);
    const accessCache = jasmine.createSpyObj<BranchComparisonAccessCache>('BranchComparisonAccessCache', ['read', 'write']);
    const router = jasmine.createSpyObj<Router>('Router', ['createUrlTree']);
    router.createUrlTree.and.returnValue({ denied: true } as any);
    accessCache.read.and.returnValue(true);
    spyOnProperty(navigator, 'onLine', 'get').and.returnValue(false);
    TestBed.configureTestingModule({ providers: [
      { provide: AdminReportService, useValue: reports },
      { provide: BranchComparisonAccessCache, useValue: accessCache },
      { provide: Router, useValue: router }
    ] });

    const result = TestBed.runInInjectionContext(() => branchComparisonGuard({} as any, {} as any));

    expect(result).toBeTrue();
    expect(reports.getBranchComparisonAccess).not.toHaveBeenCalled();
  });

  it('does not grant offline navigation when no positive access decision was cached', () => {
    const reports = jasmine.createSpyObj<AdminReportService>('AdminReportService', ['getBranchComparisonAccess']);
    const accessCache = jasmine.createSpyObj<BranchComparisonAccessCache>('BranchComparisonAccessCache', ['read', 'write']);
    const deniedTree = { denied: true };
    const router = jasmine.createSpyObj<Router>('Router', ['createUrlTree']);
    router.createUrlTree.and.returnValue(deniedTree as any);
    accessCache.read.and.returnValue(null);
    spyOnProperty(navigator, 'onLine', 'get').and.returnValue(false);
    TestBed.configureTestingModule({ providers: [
      { provide: AdminReportService, useValue: reports },
      { provide: BranchComparisonAccessCache, useValue: accessCache },
      { provide: Router, useValue: router }
    ] });

    const result = TestBed.runInInjectionContext(() => branchComparisonGuard({} as any, {} as any));

    expect(result as any).toBe(deniedTree);
    expect(reports.getBranchComparisonAccess).not.toHaveBeenCalled();
  });
});
