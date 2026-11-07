import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { TokenService } from '../services/token.service';

function getRoleFromToken(token: string): string | null {
  try {
    const payload = token.split('.')[1];
    if (!payload) {
      return null;
    }
    const base64 = payload.replace(/-/g, '+').replace(/_/g, '/').padEnd(Math.ceil(payload.length / 4) * 4, '=');
    return JSON.parse(atob(base64)).rol ?? null;
  } catch {
    return null;
  }
}

export const adminGuard: CanActivateFn = () => {
  const token = inject(TokenService).getToken();
  const router = inject(Router);
  
  const rol = getRoleFromToken(token ?? '')?.trim().toUpperCase() ?? null;
  const resultado = !!token && rol === 'ADMINISTRADOR';


  if (resultado) {
    return true;
  }

  return router.createUrlTree(['/catalog']);
};
