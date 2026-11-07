import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { TokenService } from '../services/token.service';

export const platformAdminGuard: CanActivateFn = () => {
  const token = inject(TokenService).getToken();
  const router = inject(Router);
  if (!token) return router.createUrlTree(['/auth/login']);

  try {
    const encoded = token.split('.')[1];
    const payload = JSON.parse(atob(encoded.replace(/-/g, '+').replace(/_/g, '/').padEnd(Math.ceil(encoded.length / 4) * 4, '=')));
    return payload.rol === 'ADMINISTRADOR_PLATAFORMA' ? true : router.createUrlTree(['/catalog']);
  } catch {
    return router.createUrlTree(['/auth/login']);
  }
};
