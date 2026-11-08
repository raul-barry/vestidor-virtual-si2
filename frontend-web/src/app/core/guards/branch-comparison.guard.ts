import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { catchError, map, of } from 'rxjs';
import { AdminReportService } from '../../features/admin/services/admin-report.service';

export const branchComparisonGuard: CanActivateFn = () => {
  const reports = inject(AdminReportService);
  const router = inject(Router);
  return reports.getBranchComparisonAccess().pipe(
    map((access) => access.comparacion_sucursales || router.createUrlTree(['/inventory'])),
    catchError(() => of(router.createUrlTree(['/inventory']))),
  );
};
