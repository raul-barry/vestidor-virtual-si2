import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { catchError, map, of } from 'rxjs';
import { AdminReportService } from '../../features/admin/services/admin-report.service';
import { BranchComparisonAccessCache } from '../services/branch-comparison-access-cache.service';

export const branchComparisonGuard: CanActivateFn = () => {
  const reports = inject(AdminReportService);
  const router = inject(Router);
  const cache = inject(BranchComparisonAccessCache);
  if (!navigator.onLine) return cache.read() === true || router.createUrlTree(['/inventory']);
  return reports.getBranchComparisonAccess().pipe(
    map((access) => { cache.write(access.comparacion_sucursales); return access.comparacion_sucursales || router.createUrlTree(['/inventory']); }),
    catchError(() => of(cache.read() === true || router.createUrlTree(['/inventory']))),
  );
};
