import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { TokenService } from '../services/token.service';

export const authGuard: CanActivateFn = (route) => {
  const tokenService = inject(TokenService);
  const router = inject(Router);

  if (!tokenService.hasToken()) return router.createUrlTree(['/auth']);
  const roles = route.data?.['roles'] as string[] | undefined;
  if (!roles) return true;
  try {
    const payload = tokenService.getToken()!.split('.')[1];
    const base64 = payload.replace(/-/g, '+').replace(/_/g, '/').padEnd(Math.ceil(payload.length / 4) * 4, '=');
    return roles.includes(JSON.parse(atob(base64)).rol) || router.createUrlTree(['/catalog']);
  } catch {
    return router.createUrlTree(['/auth']);
  }
};
