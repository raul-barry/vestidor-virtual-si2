import { Injectable } from '@angular/core';
import { Observable, finalize, tap } from 'rxjs';
import { ApiService } from '../../../core/services/api.service';
import { TokenService } from '../../../core/services/token.service';
import { Usuario } from '../../../shared/models/usuario.model';

export interface RegisterRequest {
  nombres: string;
  apellidos: string;
  correo: string;
  telefono?: string;
  password: string;
}

export interface LoginRequest {
  correo: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  usuario: Pick<Usuario, 'id_usuario' | 'correo'>;
  rol: string;
}

export interface PasswordResetConfirm {
  token: string;
  nueva_password: string;
}

interface MessageResponse {
  message: string;
  token?: string;
}

@Injectable({ providedIn: 'root' })
export class AuthService {
  constructor(
    private readonly api: ApiService,
    private readonly tokenService: TokenService
  ) {}

  register(request: RegisterRequest): Observable<Usuario> {
    return this.api.post<Usuario>('/api/auth/register', request);
  }

  login(request: LoginRequest): Observable<LoginResponse> {
    return this.api.post<LoginResponse>('/api/auth/login', request).pipe(
      tap((response) => {
        this.tokenService.setToken(response.access_token);
        localStorage.setItem('vestidor_virtual_user', JSON.stringify({
          ...response.usuario,
          rol: response.rol
        }));
      })
    );
  }

  getRoleFromToken(token: string): string | null {
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

  hasSession(): boolean {
    return this.tokenService.hasToken();
  }

  clearSession(): void {
    this.tokenService.clearToken();
    localStorage.removeItem('vestidor_virtual_user');
    sessionStorage.removeItem('vestidor_virtual_user');
  }

  logout(): Observable<MessageResponse> {
    return this.api.post<MessageResponse>('/api/auth/logout', {}).pipe(
      finalize(() => this.clearSession())
    );
  }

  requestPasswordReset(correo: string): Observable<MessageResponse> {
    return this.api.post<MessageResponse>('/api/auth/request-password-reset', { correo });
  }

  resetPassword(request: PasswordResetConfirm): Observable<MessageResponse> {
    return this.api.post<MessageResponse>('/api/auth/reset-password', request);
  }

  validatePasswordResetToken(token: string): Observable<MessageResponse> {
    return this.api.post<MessageResponse>('/api/auth/validate-password-reset', { token });
  }
}
