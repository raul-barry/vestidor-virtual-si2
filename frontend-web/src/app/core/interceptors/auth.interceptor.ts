import { HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { TokenService } from '../services/token.service';

const PUBLIC_AUTH_PATHS = ['/api/auth/login', '/api/auth/register'];

export const authInterceptor: HttpInterceptorFn = (request, next) => {
  const token = inject(TokenService).getToken();
  const isPublicAuthRequest = PUBLIC_AUTH_PATHS.some((path) => request.url.includes(path));

  if (!token || isPublicAuthRequest) {
    return next(request);
  }

  return next(request.clone({ setHeaders: { Authorization: `Bearer ${token}` } }));
};
